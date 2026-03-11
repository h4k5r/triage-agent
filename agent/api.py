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
        MAX_ITERATIONS = 100
        # Seed the conversation with the user's query
        messages = [("user", request.query)]
        last_ai_text = ""

        for iteration in range(MAX_ITERATIONS):
            print(f"  [LOOP] Iteration {iteration + 1}/{MAX_ITERATIONS}")
            result = await agent_executor.ainvoke({"messages": messages})

            all_msgs = result.get("messages", [])
            for i, m in enumerate(all_msgs):
                print(f"    [DEBUG] msg[{i}] type={type(m).__name__} content_len={len(str(m.content))}")

            # Find the last AIMessage with actual text content in this iteration
            iter_ai_text = ""
            for msg in reversed(all_msgs):
                if isinstance(msg, AIMessage):
                    text = _extract_text(msg.content)
                    if text:
                        iter_ai_text = text
                        break

            # Check if the agent called any new tools in this iteration vs previous
            prev_len = len(messages) if isinstance(messages[0], tuple) else len(messages)
            new_tool_calls = sum(
                1 for m in all_msgs[prev_len:]
                if not isinstance(m, AIMessage)
            )
            print(f"    [LOOP] new_tool_calls={new_tool_calls} iter_ai_text_len={len(iter_ai_text)}")

            # Log intermediate output before next pass
            new_msgs = all_msgs[prev_len:]
            tool_names = [
                m.name for m in new_msgs
                if not isinstance(m, AIMessage) and hasattr(m, "name")
            ]
            if tool_names:
                print(f"    [LOOP] Tools called this pass: {tool_names}")
            if iter_ai_text:
                preview = iter_ai_text[:300].replace("\n", " ")
                print(f"    [LOOP] AI output this pass: {preview}{'...' if len(iter_ai_text) > 300 else ''}")
            else:
                print(f"    [LOOP] AI output this pass: (none)")

            # Accumulate: use the full message list for the next iteration
            # Add a continuation prompt so the model knows to keep investigating
            messages = all_msgs
            if iter_ai_text:
                last_ai_text = iter_ai_text

            # If the agent produced text AND made no new tool calls, it's done
            if iter_ai_text and new_tool_calls == 0:
                print(f"  [LOOP] Agent finished at iteration {iteration + 1}")
                break

            # If no new tool calls were made at all, push the agent to continue
            if new_tool_calls == 0 and iteration < MAX_ITERATIONS - 1:
                messages = list(all_msgs) + [
                    ("user", (
                        "Continue the investigation. You have not yet completed all required steps. "
                        "If you have Kubernetes data, now use Prometheus/Grafana tools: "
                        "try list_prometheus_metric_names or query_prometheus to get memory usage, "
                        "or list_datasources to find the correct datasource ID. "
                        "Do NOT stop until you have checked all requested data sources."
                    ))
                ]

        # If still no text response after all iterations, force a summarization
        if not last_ai_text:
            print("  [LOOP] All iterations exhausted with no AI text — forcing summarization")
            summary_msgs = list(result["messages"]) + [
                ("user", "Based on all the tool results above, provide a complete and concise summary of your findings.")
            ]
            llm = get_llm()
            summary = await llm.ainvoke(summary_msgs)
            last_ai_text = _extract_text(summary.content)

        if last_ai_text:
            return TriageResponse(response=last_ai_text)
        else:
            return TriageResponse(response="Agent produced no response", status="error")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
