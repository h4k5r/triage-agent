import json
from google.genai import types

TOOL_ALIASES = {
    "prometheus_query": "query_prometheus",
    "monitoring_query": "query_prometheus",
    "query_metric": "query_prometheus",
    "google_monitoring": "query_prometheus",
    "loki_query": "query_loki_logs",
    "query_loki": "query_loki_logs",
    "loki_logs": "query_loki_logs",
    "get_pods": "kubectl_get",
    "k8s_get": "kubectl_get",
    "k8s_describe": "kubectl_describe",
    "k8s_logs": "kubectl_logs",
    "read_file": "get_file_contents",
}

SRE_SYSTEM_PROMPT = """You are an autonomous SRE Diagnostic Agent.
When investigating an alert, your mission is to investigate cluster telemetry, find root cause, and synthesize a comprehensive Markdown diagnostic report.

AVAILABLE TOOLS & SIGNATURES:
- `query_prometheus(expr=...)`: Run PromQL queries for metrics (e.g. increase of 5xx errors).
- `query_loki_logs(logql=..., limit=50)`: Retrieve application logs matching LogQL filters.
- `kubectl_get(resourceType='pods')`: Inspect Kubernetes pods, services, and deployments.
- `kubectl_describe(resourceType='pod', name=...)`: Describe specific Kubernetes resources for events and annotations.
- `kubectl_logs(name=..., tail=50)`: Fetch pod stdout/stderr logs.
- `get_file_contents(path=...)`: Inspect source code from the repository (e.g., `dummy-app/src/app.ts`).

INVESTIGATION WORKFLOW:
1. Use `query_prometheus` to quantify error rate and affected routes.
2. Use `query_loki_logs` to get error log traces.
3. Use `kubectl_get` and `kubectl_describe` to inspect pod state and deployment annotations.
4. Use `get_file_contents` to inspect the failing source code lines.
5. After gathering the necessary evidence, produce a complete SRE Diagnostic Report with:
   - Root Cause Analysis
   - Telemetry Analysis (metrics & logs)
   - Kubernetes Cluster State
   - Source Code Analysis (citing repository, file path, and code lines)
   - Recommended Fix & Remediation Plan
"""

CORE_TOOLS = {
    "query_prometheus", "query_loki_logs", "kubectl_get", "kubectl_describe",
    "kubectl_logs", "get_file_contents"
}

class NativeTriageAgent:
    def __init__(self, client, model_name, tools, provider: str = "genai"):
        self.client = client
        self.model_name = model_name
        self.tools = tools
        self.provider = provider
        self.tool_map = {t.name: t for t in tools}
        if provider == "ollama":
            self.ollama_tools = [t.to_ollama_tool() for t in tools if t.name in CORE_TOOLS]
        else:
            self.tool_declarations = [t.to_function_declaration() for t in tools]

    async def ainvoke(self, query: str) -> str:
        if self.provider == "ollama":
            return await self._ainvoke_ollama(query)
        else:
            return await self._ainvoke_genai(query)

    async def _ainvoke_ollama(self, query: str) -> str:
        messages = [
            {"role": "system", "content": SRE_SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ]

        asked_for_synthesis = False
        for step in range(15):
            response = await self.client.chat(
                model=self.model_name,
                messages=messages,
                tools=self.ollama_tools if self.ollama_tools else None,
                options={"temperature": 0.1}
            )
            msg = response["message"]
            messages.append(msg)

            tool_calls = msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)
            c_text = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            th_text = msg.get("thinking", "") if isinstance(msg, dict) else (getattr(msg, "thinking", "") or "")
            print(f"  [*] [Ollama] Step {step}: tool_calls={len(tool_calls) if tool_calls else 0}, content_len={len(c_text or '')}, thinking_len={len(th_text or '')}")
            if c_text:
                print(f"      [Content preview]: {repr(c_text[:120])}")
            if th_text and not c_text and not tool_calls:
                print(f"      [Thinking preview]: {repr(th_text[:120])}")
            if not tool_calls:
                content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
                content = content.strip() if content else ""

                # If the model produced no text, short text, or raw tool markup instead of a full report
                if (not content or "<tool_code>" in content or len(content) < 500) and not asked_for_synthesis:
                    asked_for_synthesis = True
                    print("  [*] [Ollama] Synthesizing final SRE Diagnostic Report...")
                    messages.append({
                        "role": "user",
                        "content": (
                            "Investigation complete. Synthesize the final comprehensive SRE Diagnostic Report in Markdown now. "
                            "Include: 1. Root Cause Analysis, 2. Telemetry Analysis (metrics & logs), 3. Kubernetes Cluster State, "
                            "4. Source Code Analysis (pointing out failing code and files), and 5. Recommended Fix & Remediation Plan."
                        )
                    })
                    continue

                if not content:
                    thinking = msg.get("thinking") if isinstance(msg, dict) else getattr(msg, "thinking", "")
                    if thinking:
                        content = thinking

                return content or "Agent completed investigation but produced no textual report."

            for tc in tool_calls:
                fn = tc.get("function") if isinstance(tc, dict) else getattr(tc, "function", None)
                fn_name = fn.get("name") if isinstance(fn, dict) else getattr(fn, "name", "")
                fn_args = fn.get("arguments") if isinstance(fn, dict) else getattr(fn, "arguments", {})

                # Resolve tool aliases
                fn_name = TOOL_ALIASES.get(fn_name, fn_name)

                print(f"  [>] [Ollama] Calling tool: {fn_name}")
                tool_instance = self.tool_map.get(fn_name)
                if not tool_instance:
                    result = f"Error: Tool '{fn_name}' not found. Available tools: {list(self.tool_map.keys())}"
                else:
                    if isinstance(fn_args, str):
                        try:
                            fn_args = json.loads(fn_args)
                        except Exception:
                            pass
                    result = await tool_instance.invoke(fn_args if isinstance(fn_args, dict) else {})

                messages.append({
                    "role": "tool",
                    "content": str(result),
                    "tool_name": fn_name
                })

        return "Agent stopped after reaching maximum steps."

    async def _ainvoke_genai(self, query: str) -> str:
        messages = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=query)]
            )
        ]
        
        # Max steps to prevent infinite loop
        for _ in range(15):
            config = types.GenerateContentConfig(
                temperature=0.1,
                system_instruction=SRE_SYSTEM_PROMPT,
                tools=[types.Tool(function_declarations=self.tool_declarations)] if self.tool_declarations else None,
            )
            
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=messages,
                config=config
            )
            
            if response.candidates:
                candidate = response.candidates[0]
                messages.append(candidate.content)
                
                # Check for function calls
                function_calls = []
                for part in candidate.content.parts:
                    if getattr(part, 'function_call', None):
                        function_calls.append(part.function_call)
                        
                if not function_calls:
                    # No more tool calls, we have our final text answer
                    text_parts = [p.text for p in candidate.content.parts if getattr(p, "text", None)]
                    return "".join(text_parts) if text_parts else (response.text or "")
                    
                # Execute tools
                function_responses = []
                for call in function_calls:
                    print(f"  [>] Calling tool: {call.name}")
                    tool_instance = self.tool_map.get(call.name)
                    if not tool_instance:
                        result = f"Error: Tool {call.name} not found"
                    else:
                        args = dict(call.args) if call.args else {}
                        result = await tool_instance.invoke(args)
                        
                    function_responses.append(
                        types.Part.from_function_response(
                            name=call.name,
                            response={"result": result}
                        )
                    )
                
                # Append tool responses to messages
                messages.append(
                    types.Content(
                        role="user", # The genai SDK specifies function responses come from 'user' or 'function' role depending on API versions, but usually 'user'
                        parts=function_responses
                    )
                )
            else:
                return "Error: No response generated by model."
                
        return "Agent stopped after reaching maximum steps."
