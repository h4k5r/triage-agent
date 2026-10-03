import os
import asyncio
from typing import List, Dict, Any, Callable
from mcp import ClientSession
from mcp.client.sse import sse_client
from contextlib import AsyncExitStack
from google.genai import types
from log_dedup import _dedup_log_text

TOOL_WHITELIST = {
    "kubectl_get", "kubectl_describe", "kubectl_logs", "kubectl_rollout", "ping",
    "query_loki_logs", "query_loki", "query_prometheus", "list_loki_label_values", "list_loki_label_names",
    "list_prometheus_metric_names", "list_datasources",
    "get_file_contents", "search_code", "search_repositories", "list_commits", "get_issue", "list_issues"
}

class MCPNativeTool:
    def __init__(self, name: str, description: str, input_schema: dict, session: ClientSession):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.session = session
        
    def to_function_declaration(self) -> types.FunctionDeclaration:
        params = dict(self.input_schema) if self.input_schema else {}
        if "$schema" in params:
            del params["$schema"]
        if not params or params.get("type") != "object":
            params["type"] = "object"
            if "properties" not in params:
                params["properties"] = {}
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description or "",
            parameters=params
        )

    def to_ollama_tool(self) -> dict:
        # Provide clean, specialized schemas for critical tools to optimize local model performance
        if self.name == "query_prometheus":
            params = {
                "type": "object",
                "properties": {
                    "expr": {"type": "string", "description": "PromQL query expression, e.g. increase(http_server_requests_total{status_code=~\"5..\"}[5m])"}
                },
                "required": ["expr"]
            }
        elif self.name in {"query_loki_logs", "query_loki"}:
            params = {
                "type": "object",
                "properties": {
                    "logql": {"type": "string", "description": "LogQL query filter, e.g. {service_name=\"node-typescript-app\"} |= \"error\""},
                    "limit": {"type": "integer", "description": "Max log lines to return (e.g. 50)"}
                },
                "required": ["logql"]
            }
        elif self.name == "kubectl_get":
            params = {
                "type": "object",
                "properties": {
                    "resourceType": {"type": "string", "description": "Type of resource to get (e.g. 'pods', 'deployments', 'events')"},
                    "name": {"type": "string", "description": "Name of specific resource (optional)"},
                    "labelSelector": {"type": "string", "description": "Label selector filter (e.g. 'app=node-typescript-app')"}
                },
                "required": ["resourceType"]
            }
        elif self.name == "kubectl_describe":
            params = {
                "type": "object",
                "properties": {
                    "resourceType": {"type": "string", "description": "Type of resource to describe (e.g. 'pod', 'deployment')"},
                    "name": {"type": "string", "description": "Name of the resource to describe"}
                },
                "required": ["resourceType", "name"]
            }
        elif self.name == "kubectl_logs":
            params = {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the pod to fetch logs from"},
                    "tail": {"type": "integer", "description": "Number of lines to show from end of logs (default: 50)"}
                },
                "required": ["name"]
            }
        elif self.name == "get_file_contents":
            params = {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path in repository, e.g. 'dummy-app/src/app.ts'"}
                },
                "required": ["path"]
            }
        else:
            params = dict(self.input_schema) if self.input_schema else {}
            if "$schema" in params:
                del params["$schema"]
            if not params or params.get("type") != "object":
                params["type"] = "object"
                if "properties" not in params:
                    params["properties"] = {}
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description or "",
                "parameters": params,
            },
        }
        
    async def invoke(self, arguments: dict) -> str:
        try:
            args = dict(arguments) if isinstance(arguments, dict) else {}

            # Parameter normalizations for various tools
            if self.name == "query_prometheus":
                args.setdefault("datasourceUid", "prometheus")
                args.setdefault("queryType", "instant")
                args.setdefault("endTime", "now")
                if "query" in args and "expr" not in args:
                    args["expr"] = args.pop("query")
            elif self.name in {"query_loki_logs", "query_loki"}:
                args.setdefault("datasourceUid", "loki")
                if "query" in args and "logql" not in args:
                    args["logql"] = args.pop("query")
                if "start" in args and "startRfc3339" not in args:
                    args["startRfc3339"] = str(args.pop("start"))
                if "end" in args and "endRfc3339" not in args:
                    args["endRfc3339"] = str(args.pop("end"))
            elif self.name == "kubectl_get":
                if "resource" in args and "resourceType" not in args:
                    parts = str(args.pop("resource")).split()
                    args["resourceType"] = parts[0]
                    if len(parts) > 1 and "name" not in args:
                        args["name"] = parts[1]
                args.setdefault("resourceType", "pods")
                args.setdefault("namespace", "default")
                args.setdefault("output", "json")
            elif self.name == "kubectl_describe":
                if "resource" in args and "name" not in args:
                    parts = str(args.pop("resource")).split()
                    args["resourceType"] = parts[0]
                    if len(parts) > 1:
                        args["name"] = parts[1]
                if "pod" in args:
                    args.setdefault("resourceType", "pod")
                    args["name"] = args.pop("pod")
                args.setdefault("resourceType", "pod")
                args.setdefault("namespace", "default")
            elif self.name == "kubectl_logs":
                if "pod" in args:
                    args["name"] = args.pop("pod")
                args.setdefault("resourceType", "pod")
                args.setdefault("namespace", "default")
            elif self.name == "get_file_contents":
                if "path" in args:
                    p = str(args["path"])
                    if p.startswith("worldender/triage-agent/"):
                        args["owner"] = "worldender"
                        args["repo"] = "triage-agent"
                        args["path"] = p.replace("worldender/triage-agent/", "")
                    else:
                        args.setdefault("owner", "worldender")
                        args.setdefault("repo", "triage-agent")

            result = await self.session.call_tool(self.name, arguments=args)
            if result.isError:
                return f"Error: {result.content}"
            texts = [c.text for c in result.content if hasattr(c, 'text')]
            output = "\n".join(texts)
            if self.name in {"query_loki_logs", "query_loki", "kubectl_logs"}:
                output = _dedup_log_text(output)
            return output
        except Exception as e:
            return f"Error invoking tool: {e}"

async def get_mcp_tools(stack: AsyncExitStack) -> List[MCPNativeTool]:
    tools = []
    endpoints = [
        os.environ.get("GITHUB_MCP_URL", "http://localhost:8080"),
        os.environ.get("GRAFANA_MCP_URL", "http://localhost:8082"), 
        os.environ.get("KUBERNETES_MCP_URL", "http://localhost:8081")
    ]
    
    for url in endpoints:
        if not url: continue
        try:
            sse_url = f"{url}/sse" if not url.endswith("/sse") else url
            streams = await stack.enter_async_context(sse_client(sse_url, timeout=300, sse_read_timeout=3600))
            read_stream, write_stream = streams
            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()
            
            res = await session.list_tools()
            for t in res.tools:
                if t.name in TOOL_WHITELIST:
                    tools.append(MCPNativeTool(
                        name=t.name,
                        description=t.description or "",
                        input_schema=t.inputSchema,
                        session=session
                    ))
        except Exception as e:
            print(f"[!] Failed to connect or load tools from {url}: {e}")
            
    return tools
