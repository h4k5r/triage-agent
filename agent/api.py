from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from contextlib import asynccontextmanager, AsyncExitStack
from langchain_core.messages import AIMessage
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

def _extract_text(content) -> str:
    """Extract plain text from a message content that may be str or list of blocks."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(p for p in parts if p).strip()
    return str(content).strip()


@app.post("/triage", response_model=TriageResponse)
async def triage_endpoint(request: TriageRequest):
    if agent_executor is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        print(f"\n[+] Processing triage request: {request.query}")
        messages = [("user", request.query)]

        # LangGraph ReAct agent autonomously executes the tool reasoning loop
        result = await agent_executor.ainvoke({"messages": messages})

        all_msgs = result.get("messages", [])

        # Find the last AIMessage with actual text content
        last_ai_text = ""
        for msg in reversed(all_msgs):
            if isinstance(msg, AIMessage):
                text = _extract_text(msg.content)
                if text:
                    last_ai_text = text
                    break

        # If model ended without a text summary, invoke LLM once to summarize findings
        if not last_ai_text:
            print("  [+] Generating final summary from tool outputs...")
            from langchain_core.messages import ToolMessage
            tool_outputs = []
            for msg in all_msgs:
                if isinstance(msg, ToolMessage):
                    tool_name = getattr(msg, "name", "tool")
                    tool_outputs.append(f"[{tool_name}]: {msg.content}")
            
            context = "\n\n".join(tool_outputs) if tool_outputs else "No diagnostic tool outputs recorded."
            llm = get_llm()
            summary_prompt = [
                ("user", f"Diagnostic investigation context:\n{context}\n\nUser Question: {request.query}\n\nPlease summarize the findings, status of the system, and any identified root causes.")
            ]
            summary = await llm.ainvoke(summary_prompt)
            last_ai_text = _extract_text(summary.content)

        print(f"[+] Agent finished: {last_ai_text[:150]}...")
        if last_ai_text:
            return TriageResponse(response=last_ai_text)
        else:
            return TriageResponse(response="Agent produced no response", status="error")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
