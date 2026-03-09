import os
import asyncio
from typing import List
from langchain_core.tools import BaseTool
from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_mcp_adapters.tools import load_mcp_tools

from contextlib import AsyncExitStack

async def get_mcp_tools(stack: AsyncExitStack) -> List[BaseTool]:
    """
    Connects to the remote Kuberenetes MCP servers securely over HTTP SSE
    and converts their native definitions into LangChain compatible BaseTools.
    """
    tools = []
    
    # We define the remote endpoints. For local development, they map to the port-forwards.
    # In production, they are injected via the Kubernetes ConfigMap.
    endpoints = [
        # os.environ.get("MCP_GITHUB_URL", "http://localhost:8081"),
        os.environ.get("MCP_GRAFANA_URL", "http://localhost:8082"), 
        # os.environ.get("MCP_KUBERNETES_URL", "http://localhost:8082")
    ]
    
    # To keep the LLM focused and reduce prompt noise, we whitelist only the most 
    # useful tools for a Triage agent. 54+ tools can confuse smaller local models.
    TOOL_WHITELIST = [
        "query_loki_logs", 
        "query_loki_stats",
        "list_loki_label_values",
        "query_prometheus",
        "list_prometheus_metric_names",
        "list_datasources"
    ]
    
    # Connect via SSE. We must keep the sessions alive as long as the tools are used.
    from contextlib import AsyncExitStack
    
    for url in endpoints:
        print(f"[+] Connecting to MCP Server at {url}")
        try:
            # We connect via the async HTTP side channel (SSE)
            streams = await stack.enter_async_context(sse_client(f"{url}/sse"))
            read_stream, write_stream = streams
            
            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()
            
            # Convert the tools exposed by this specific MCP server into LangChain format
            all_mcp_tools = await load_mcp_tools(session)
            
            # Filter tools based on whitelist (DISABLED FOR TESTING - ALLOWING ALL TOOLS)
            active_tools = all_mcp_tools # [t for t in all_mcp_tools if t.name in TOOL_WHITELIST]
            
            print(f"    -> Loaded {len(active_tools)} tools.")
            # if active_tools:
            #    print(f"    -> Active tools: {', '.join([t.name for t in active_tools])}")
            
            # Inform LangGraph that if a tool throws an error
            for tool in active_tools:
                tool.handle_tool_error = True
                
            tools.extend(active_tools)
        except Exception as e:
            print(f"[!] Failed to connect or load tools from {url}: {e}")
            
    return tools
