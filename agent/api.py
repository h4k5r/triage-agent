from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import time
import uuid
import os
import json
from contextlib import asynccontextmanager, AsyncExitStack
from llm import get_llm
from agent import NativeTriageAgent
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

INCIDENTS_STORE_PATH = "/tmp/incidents_store.json"

def _save_incidents():
    try:
        data = {k: v.dict() for k, v in incidents.items()}
        with open(INCIDENTS_STORE_PATH, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[!] Error saving incidents: {e}")

def _load_incidents():
    global incidents
    if os.path.exists(INCIDENTS_STORE_PATH):
        try:
            with open(INCIDENTS_STORE_PATH, "r") as f:
                data = json.load(f)
                for k, v in data.items():
                    incidents[k] = IncidentRecord(**v)
            print(f"[+] Loaded {len(incidents)} incidents from store.")
        except Exception as e:
            print(f"[!] Error loading incidents: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_executor, mcp_tools
    
    print("\n[+] Lifespan startup: Initializing agent and tools...")
    _load_incidents()
    async with AsyncExitStack() as stack:
        print("[+] Gathering MCP Tools...")
        try:
            tools = await asyncio.wait_for(get_mcp_tools(stack), timeout=60.0)
        except Exception as e:
            print(f"[!] Error loading tools: {e}")
            tools = []
        
        client, model_name = get_llm()
        
        print("[+] Building Agent Executor...")
        triage_agent = NativeTriageAgent(client, model_name, tools)
        
        agent_executor = triage_agent
        mcp_tools = tools
        
        print("[+] Agent ready for requests.")
        yield
        
    print("\n[+] Lifespan shutdown: Cleaning up resources...")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Triage Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "agent_initialized": agent_executor is not None}


@app.post("/triage", response_model=TriageResponse)
async def triage_endpoint(request: TriageRequest):
    if agent_executor is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        print(f"\n[+] Processing triage request: {request.query}")
        result = await agent_executor.ainvoke(request.query)

        print(f"[+] Agent finished: {result[:150]}...")
        if result:
            return TriageResponse(response=result)
        else:
            return TriageResponse(response="Agent produced no response", status="error")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def _run_alert_triage(incident_id: str, query: str):
    record = incidents.get(incident_id)
    if not record:
        return

    try:
        print(f"\n[+] [Incident {incident_id}] Starting background triage run...")

        if agent_executor is None:
            raise RuntimeError("Agent executor is not initialized")

        result = await agent_executor.ainvoke(query)

        record.status = "COMPLETED"
        record.response = result or "Agent produced no response."
        record.updated_at = time.time()
        _save_incidents()
        print(f"[+] [Incident {incident_id}] Triage completed successfully.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        record.status = "FAILED"
        record.error = str(e)
        record.updated_at = time.time()
        _save_incidents()
        print(f"[!] [Incident {incident_id}] Triage failed: {e}")


@app.post("/alerts", status_code=202)
async def grafana_alert_webhook(payload: GrafanaWebhookPayload):
    """Webhook endpoint invoked by Grafana Alertmanager when rules fire or resolve."""
    print(f"\n[!] Grafana Alert Webhook received: status={payload.status}, alerts={len(payload.alerts)}")

    if payload.status == "resolved":
        for a in payload.alerts:
            alertname = a.labels.get("alertname", "UnknownAlert")
            service = a.labels.get("service") or a.labels.get("service_name") or a.labels.get("job") or "unknown"
            print(f"[*] Alert resolved: {alertname}-{service}")
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

        # Only ignore rapid network duplicates within 2s for the exact same starts_at timestamp
        dedup_key = f"{alert.fingerprint or ''}-{alertname}-{service}-{starts_at}"
        if dedup_key in recent_alerts and (now - recent_alerts[dedup_key]) < 2:
            print(f"[*] Skipping exact network retransmission for '{dedup_key}' within 2s")
            continue
        recent_alerts[dedup_key] = now

        incident_id = f"inc-{uuid.uuid4().hex[:8]}"

        # Determine alert focus scope (5xx server errors vs 4xx client errors)
        alert_text = f"{alertname} {summary} {description}".lower()
        if "server" in alert_text or "5xx" in alert_text:
            target_metric_filter = '{status_code=~"5.."}'
            scope_desc = "HTTP 5xx server errors (e.g., status 500, 502)"
            scope_constraint = (
                "IMPORTANT: Focus exclusively on HTTP 5xx server errors and the specific failing routes causing them. "
                "Do NOT list, table, or enumerate successful 2xx requests or 4xx client errors in the metrics breakdown or report."
            )
        elif "client" in alert_text or "4xx" in alert_text:
            target_metric_filter = '{status_code=~"4.."}'
            scope_desc = "HTTP 4xx client errors (e.g., status 400, 401, 404)"
            scope_constraint = (
                "IMPORTANT: Focus exclusively on HTTP 4xx client errors and the specific routes causing them. "
                "Do NOT list, table, or enumerate successful 2xx requests or 5xx server errors in the metrics breakdown or report."
            )
        else:
            target_metric_filter = '{status_code!~"2.."}'
            scope_desc = "failing non-2xx error responses"
            scope_constraint = (
                "IMPORTANT: Focus strictly on the failing routes and error status codes relevant to this alert. "
                "Do NOT list or enumerate successful 2xx requests in the report."
            )

        query = (
            f"GRAFANA ALERT TRIGGERED: '{alertname}' for service '{service}'.\n"
            f"Severity: {alert.labels.get('severity', 'critical')}\n"
            f"Started At: {starts_at}\n"
            f"Summary: {summary}\n"
            f"Description: {description}\n\n"
            f"INVESTIGATION INSTRUCTIONS:\n"
            f"1. Query Prometheus metrics specifically filtered for {target_metric_filter} (e.g., `increase(http_server_requests_total{target_metric_filter}[5m])` or `http_server_requests_total{target_metric_filter}`) to quantify the error rate for THIS alert window.\n"
            f"   {scope_constraint}\n"
            f"   NOTE: Focus on the specific error spike for THIS alert window (over the last 5 minutes). Clearly distinguish the new error burst from cumulative historical totals.\n"
            f"2. Query Loki logs for service '{service}' with STRICT constraints:\n"
            f"   - Use `limit=50` to cap the number of log lines returned.\n"
            f"   - Use `start` and `end` parameters to scope to the 5 minutes around {starts_at}.\n"
            f"   - Use LogQL line filters: e.g., `{{service_name=\"{service}\"}} |= \"error\"` or `|= \"500\"` to fetch only error-relevant lines.\n"
            f"   - Logs are automatically deduplicated. Do NOT re-fetch the same query.\n"
            f"3. Inspect Kubernetes pods and events for service '{service}' (e.g. check restarts, crash loops, or resource saturation).\n"
            f"4. Retrieve the source code repository from the deployment/pod annotations (`github.com/repository`) and subpath (`github.com/path`). For compiled TypeScript/Node apps where logs cite `dist/*.js` (e.g. `dist/app.js`), inspect the corresponding TypeScript source file in `src/*.ts` (e.g. `dummy-app/src/app.ts`) using GitHub MCP tools (`get_file_contents`), cite the actual TypeScript code snippet in your report, and diagnose what is causing the error.\n"
            f"5. Provide a clear summary: Root Cause, Affected Endpoints/Pods, Source Code Analysis (citing the TypeScript file path and relevant lines of code from GitHub), and Recommended Fix.\n"
            f"   Ensure your final report contains ONLY information relevant to {scope_desc}; do not include unrelated healthy endpoints or other status code categories."
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
        _save_incidents()
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

