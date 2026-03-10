import os
import sys
import asyncio
from contextlib import AsyncExitStack

from llm import get_llm
from agent import create_triage_agent
from mcp_client import get_mcp_tools
from cli import run_cli
from api import app, set_agent
import uvicorn

async def main():
    print("==================================================")
    print(" Starting AI Triage Agent  ")
    print("==================================================")
    
    # Debug: Print relevant environment variables
    print("\n[DEBUG] Environment Variables:")
    for key, value in os.environ.items():
        if any(x in key for x in ["MCP", "GRAFANA", "KUBERNETES", "OLLAMA"]):
            print(f"  {key}={value}")
    
    # Start interactive CLI loop or run FastAPI server
    if sys.stdin.isatty():
        try:
            async with AsyncExitStack() as stack:
                # Load the LangChain MCP bindings
                print("\n[+] Gathering MCP Tools...")
                try:
                    tools = await asyncio.wait_for(get_mcp_tools(stack), timeout=30.0)
                except asyncio.TimeoutError:
                    print("[!] Timeout loading tools from MCP servers.")
                    tools = []
                except Exception as e:
                    print(f"[!] Error loading tools: {e}")
                    tools = []
                
                # Connect to Ollama
                llm = get_llm()
                
                # Initialize the LangGraph ReAct Agent
                print("\n[+] Building Agent Executor...")
                triage_agent = create_triage_agent(llm, tools=tools)
                
                # Set the agent in the API module (just in case)
                set_agent(triage_agent, tools)
                
                await run_cli(triage_agent, tools=tools)
        except Exception as e:
            import traceback
            print(f"\n[!] CLI failed to connect or initialize.")
            traceback.print_exc()
    else:
        print("\n[+] Non-interactive environment detected. Starting FastAPI server on port 8000...")
        # In non-interactive mode, FastAPI's lifespan will handle agent and tools initialization
        # Run FastAPI with uvicorn
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
# Force build change
# Lifespan fix
# Lifespan fix v2
