from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import time
import uuid
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

class GrafanaAlertItem(BaseModel):
    status: str = "firing"
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None
    valueString: Optional[str] = None

class GrafanaWebhookPayload(BaseModel):
    receiver: Optional[str] = None
    status: str = "firing"
    alerts: List[GrafanaAlertItem] = Field(default_factory=list)
    groupLabels: Dict[str, str] = Field(default_factory=dict)
    commonLabels: Dict[str, str] = Field(default_factory=dict)
    commonAnnotations: Dict[str, str] = Field(default_factory=dict)
    externalURL: Optional[str] = None

class IncidentRecord(BaseModel):
    id: str
    status: str  # "INVESTIGATING", "COMPLETED", "FAILED", "RESOLVED"
    created_at: float
    updated_at: float
    alertname: str
    service: str
    starts_at: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    query: str
    response: Optional[str] = None
    error: Optional[str] = None

# Global state for the agent, tools, and incidents
agent_executor = None
mcp_tools = None
incidents: Dict[str, IncidentRecord] = {}
recent_alerts: Dict[str, float] = {}

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


async def _run_alert_triage(incident_id: str, query: str):
    """Background task to run LangGraph triage agent autonomously."""
    record = incidents.get(incident_id)
    if not record:
        return

    try:
        print(f"\n[+] [Incident {incident_id}] Starting background triage run...")
        messages = [("user", query)]

        if agent_executor is None:
            raise RuntimeError("Agent executor is not initialized")

        result = await agent_executor.ainvoke({"messages": messages})
        all_msgs = result.get("messages", [])

        last_ai_text = ""
        for msg in reversed(all_msgs):
            if isinstance(msg, AIMessage):
                text = _extract_text(msg.content)
                if text:
                    last_ai_text = text
                    break

        if not last_ai_text:
            print(f"  [+] [Incident {incident_id}] Generating summary from tool outputs...")
            from langchain_core.messages import ToolMessage
            tool_outputs = []
            for msg in all_msgs:
                if isinstance(msg, ToolMessage):
                    tool_name = getattr(msg, "name", "tool")
                    tool_outputs.append(f"[{tool_name}]: {msg.content}")

            context = "\n\n".join(tool_outputs) if tool_outputs else "No diagnostic tool outputs recorded."
            llm = get_llm()
            summary_prompt = [
                ("user", f"Diagnostic investigation context:\n{context}\n\nAlert Prompt:\n{query}\n\nPlease summarize findings, status, root cause, and recommended fixes.")
            ]
            summary = await llm.ainvoke(summary_prompt)
            last_ai_text = _extract_text(summary.content)

        record.status = "COMPLETED"
        record.response = last_ai_text or "Agent produced no response."
        record.updated_at = time.time()
        print(f"[+] [Incident {incident_id}] Triage completed successfully.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        record.status = "FAILED"
        record.error = str(e)
        record.updated_at = time.time()
        print(f"[!] [Incident {incident_id}] Triage failed: {e}")


@app.post("/alerts", status_code=202)
async def grafana_alert_webhook(payload: GrafanaWebhookPayload):
    """Webhook endpoint invoked by Grafana Alertmanager when rules fire or resolve."""
    print(f"\n[!] Grafana Alert Webhook received: status={payload.status}, alerts={len(payload.alerts)}")

    if payload.status == "resolved":
        for a in payload.alerts:
            alertname = a.labels.get("alertname", "UnknownAlert")
            service = a.labels.get("service") or a.labels.get("service_name") or a.labels.get("job") or "unknown"
            cooldown_key = f"{alertname}-{service}"
            recent_alerts.pop(cooldown_key, None)
            print(f"[*] Cleared cooldown for resolved alert: {cooldown_key}")
        return {"status": "acknowledged", "message": "Alert resolution acknowledged."}

    dispatched = []
    now = time.time()

    # If alerts list is empty but payload status is firing (some custom webhooks send group info)
    items = payload.alerts if payload.alerts else [GrafanaAlertItem(
        status="firing",
        labels=payload.commonLabels,
        annotations=payload.commonAnnotations
    )]

    for alert in items:
        if alert.status != "firing":
            continue

        alertname = alert.labels.get("alertname") or payload.commonLabels.get("alertname", "HighHttpErrorRate")
        service = (
            alert.labels.get("service")
            or alert.labels.get("service_name")
            or alert.labels.get("job")
            or payload.commonLabels.get("service")
            or payload.commonLabels.get("service_name")
            or "node-typescript-app"
        )
        summary = (
            alert.annotations.get("summary")
            or alert.annotations.get("description")
            or payload.commonAnnotations.get("summary", "High HTTP error rate detected")
        )
        description = (
            alert.annotations.get("description")
            or payload.commonAnnotations.get("description", "Service exceeded error threshold in 5-minute window")
        )
        starts_at = alert.startsAt or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))

        cooldown_key = f"{alertname}-{service}"
        if cooldown_key in recent_alerts and (now - recent_alerts[cooldown_key]) < 600:
            print(f"[*] Skipping duplicate alert for '{cooldown_key}' (cooldown active: {int(now - recent_alerts[cooldown_key])}s / 600s)")
            continue

        recent_alerts[cooldown_key] = now
        incident_id = f"inc-{uuid.uuid4().hex[:8]}"

        query = (
            f"GRAFANA ALERT TRIGGERED: '{alertname}' for service '{service}'.\n"
            f"Severity: {alert.labels.get('severity', 'critical')}\n"
            f"Started At: {starts_at}\n"
            f"Summary: {summary}\n"
            f"Description: {description}\n\n"
            f"INVESTIGATION INSTRUCTIONS:\n"
            f"1. Query Loki logs and Prometheus metrics for service '{service}' around {starts_at} to inspect the recent errors, non-2xx status codes (such as 4xx client errors or 5xx server errors), failing endpoints/routes, and log messages/stack traces.\n"
            f"2. Inspect Kubernetes pods and events for service '{service}' (e.g. check restarts, crash loops, or resource saturation).\n"
            f"3. Retrieve the source code repository from the deployment/pod annotations (`github.com/repository`), locate the failing endpoint in the code, and diagnose what is causing the error.\n"
            f"4. Provide a clear summary: Root Cause, Affected Endpoints/Pods, and Recommended Fix."
        )

        record = IncidentRecord(
            id=incident_id,
            status="INVESTIGATING",
            created_at=now,
            updated_at=now,
            alertname=alertname,
            service=service,
            starts_at=starts_at,
            summary=summary,
            description=description,
            query=query
        )
        incidents[incident_id] = record
        dispatched.append(incident_id)

        # Launch background investigation task
        asyncio.create_task(_run_alert_triage(incident_id, query))

    return {
        "status": "accepted",
        "incidents_dispatched": dispatched,
        "count": len(dispatched)
    }


@app.get("/alerts")
async def list_alerts():
    """List all tracked alert incidents and their triage status."""
    return sorted(list(incidents.values()), key=lambda x: x.created_at, reverse=True)


@app.get("/alerts/{incident_id}")
async def get_alert(incident_id: str):
    """Retrieve details and diagnostic report for a specific incident."""
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incidents[incident_id]

