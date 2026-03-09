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
    
    # Environment variable names matching the Kubernetes ConfigMap
    # Fallbacks provided for local testing via port-forwards
    endpoints = [
        os.environ.get("GITHUB_MCP_URL", "http://localhost:8081"),
        os.environ.get("GRAFANA_MCP_URL", "http://localhost:8082"), 
        os.environ.get("KUBERNETES_MCP_URL", "http://localhost:8081")
    ]
    
    for url in endpoints:
        # Avoid empty strings if some env vars are not set
        if not url:
            continue
            
        print(f"[+] Connecting to MCP Server at {url}")
        try:
            # We connect via the async HTTP side channel (SSE)
            # Most MCP servers expose the SSE endpoint at /sse
            sse_url = f"{url}/sse" if not url.endswith("/sse") else url
            
            streams = await stack.enter_async_context(sse_client(sse_url))
            read_stream, write_stream = streams
            
            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()
            
            # Convert the tools exposed by this specific MCP server into LangChain format
            all_mcp_tools = await load_mcp_tools(session)
            
            # Filter tools based on whitelist (DISABLED FOR TESTING - ALLOWING ALL TOOLS)
            active_tools = all_mcp_tools 
            
            print(f"    -> Loaded {len(active_tools)} tools.")
            
            # Inform LangGraph that if a tool throws an error
            for tool in active_tools:
                tool.handle_tool_error = True
                
            tools.extend(active_tools)
        except Exception as e:
            print(f"[!] Failed to connect or load tools from {url}: {e}")
            
    return tools
