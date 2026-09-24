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
    "query_loki_logs", "query_prometheus", "list_loki_label_values", "list_loki_label_names",
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
        params = dict(self.input_schema)
        if "$schema" in params:
            del params["$schema"]
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description or "",
            parameters=params
        )
        
    async def invoke(self, arguments: dict) -> str:
        try:
            result = await self.session.call_tool(self.name, arguments=arguments)
            if result.isError:
                return f"Error: {result.content}"
            texts = [c.text for c in result.content if hasattr(c, 'text')]
            output = "\n".join(texts)
            if self.name in {"query_loki_logs", "query_loki"}:
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
