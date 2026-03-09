import os
import sys
import asyncio
from contextlib import AsyncExitStack

from llm import get_llm
from agent import create_triage_agent
from mcp_client import get_mcp_tools
from cli import run_cli

async def main():
    print("==================================================")
    print(" Starting AI Triage Agent  ")
    print("==================================================")
    
    # Debug: Print relevant environment variables
    print("\n[DEBUG] Environment Variables:")
    for key, value in os.environ.items():
        if any(x in key for x in ["MCP", "GRAFANA", "KUBERNETES", "OLLAMA"]):
            print(f"  {key}={value}")
    
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
            
            # Start interactive CLI loop or wait if non-interactive
            if sys.stdin.isatty():
                await run_cli(triage_agent, tools=tools)
            else:
                print("\n[+] Non-interactive environment detected. Agent is ready and waiting.")
                # Keep the process alive in Kubernetes
                while True:
                    await asyncio.sleep(3600)
            
    except Exception as e:
        import traceback
        print(f"\n[!] Failed to connect or initialize.")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
