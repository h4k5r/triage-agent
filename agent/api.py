from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from contextlib import asynccontextmanager, AsyncExitStack
from llm import get_llm
from agent import create_triage_agent
from mcp_client import get_mcp_tools

class TriageRequest(BaseModel):
    query: str

class TriageResponse(BaseModel):
    response: str
    status: str = "success"

# Global state for the agent and tools
agent_executor = None
mcp_tools = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_executor, mcp_tools
    
    print("\n[+] Lifespan startup: Initializing agent and tools...")
    async with AsyncExitStack() as stack:
        # Load the LangChain MCP bindings
        print("[+] Gathering MCP Tools...")
        try:
            tools = await asyncio.wait_for(get_mcp_tools(stack), timeout=60.0)
        except Exception as e:
            print(f"[!] Error loading tools: {e}")
            tools = []
        
        # Connect to Ollama
        llm = get_llm()
        
        # Initialize the LangGraph ReAct Agent
        print("[+] Building Agent Executor...")
        triage_agent = create_triage_agent(llm, tools=tools)
        
        # Set global state
        agent_executor = triage_agent
        mcp_tools = tools
        
        print("[+] Agent ready for requests.")
        yield
        
    print("\n[+] Lifespan shutdown: Cleaning up resources...")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Triage Agent API", lifespan=lifespan)

# Allow all origins for the browser UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def set_agent(executor, tools):
    """Fallback for interactive mode or testing"""
    global agent_executor, mcp_tools
    agent_executor = executor
    mcp_tools = tools

@app.get("/health")
async def health_check():
    return {"status": "ok", "agent_initialized": agent_executor is not None}

@app.post("/triage", response_model=TriageResponse)
async def triage_endpoint(request: TriageRequest):
    if agent_executor is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Invoke the LangGraph agent
        # We use a thread-safe way or just await it if it's already async
        result = await agent_executor.ainvoke({"messages": [("user", request.query)]})
        
        # Extract the last message from the agent
        if "messages" in result and len(result["messages"]) > 0:
            last_message = result["messages"][-1].content
            return TriageResponse(response=last_message)
        else:
            return TriageResponse(response="Agent produced no response", status="error")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
