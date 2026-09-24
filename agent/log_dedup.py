"""
Log Deduplication Wrapper for MCP Loki Tools.

Intercepts query_loki_logs / query_loki tool responses and collapses
identical log lines into counted summaries before the LLM sees them.

Before:  847 identical "GET /error 500" lines → 847 × tokens consumed
After:   "[×847] GET /error 500 Internal Server Error" → 1 line
"""

import re
import json
from collections import Counter
from typing import Optional
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun

# Regex to strip common log timestamp prefixes
# Matches ISO 8601 timestamps, Unix timestamps, and common log date formats
_TIMESTAMP_RE = re.compile(
    r"^\s*"
    r"(?:"
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"  # ISO 8601
    r"|ts=\d+(?:\.\d+)?"                                                            # ts=epoch
    r"|\d{10,13}"                                                                    # Unix epoch
    r")"
    r"\s*",
)

# Max distinct lines to keep in the deduped output
MAX_DISTINCT_LINES = 50


def _dedup_log_text(raw: str) -> str:
    """
    Takes raw log output (multi-line string), deduplicates lines by content
    (ignoring timestamps), and returns a compact summary with counts.
    """
    if not raw or not raw.strip():
        return raw

    lines = raw.strip().splitlines()

    # If it looks like a JSON response, try to parse and extract log lines
    stripped = raw.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            data = json.loads(stripped)
            lines = _extract_lines_from_json(data)
        except (json.JSONDecodeError, TypeError):
            pass

    if not lines:
        return raw

    # Strip timestamps and normalize whitespace for dedup key
    normalized = []
    for line in lines:
        clean = _TIMESTAMP_RE.sub("", line).strip()
        # Also strip leading log level markers for grouping
        clean = re.sub(r"^(INFO|WARN|ERROR|DEBUG|TRACE|FATAL)\s*:?\s*", "", clean, flags=re.IGNORECASE)
        if clean:
            normalized.append((clean, line))

    if not normalized:
        return raw

    # Count occurrences of each distinct message
    counter = Counter(msg for msg, _ in normalized)

    # Preserve one representative raw line per distinct message
    seen = {}
    for clean, original in normalized:
        if clean not in seen:
            seen[clean] = original

    # Sort by frequency (most common first)
    sorted_msgs = counter.most_common(MAX_DISTINCT_LINES)

    # Build output
    output_lines = []
    total_lines = len(normalized)
    distinct_count = len(counter)
    output_lines.append(f"[Log Summary: {total_lines} total lines → {distinct_count} distinct messages]")
    output_lines.append("")

    for msg, count in sorted_msgs:
        if count > 1:
            output_lines.append(f"[×{count}] {msg}")
        else:
            output_lines.append(f"       {msg}")

    if distinct_count > MAX_DISTINCT_LINES:
        output_lines.append(f"... and {distinct_count - MAX_DISTINCT_LINES} more distinct messages (truncated)")

    return "\n".join(output_lines)


def _extract_lines_from_json(data) -> list:
    """Extract log line strings from Grafana/Loki JSON response structures."""
    lines = []

    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                lines.append(item)
            elif isinstance(item, dict):
                # Loki stream format: {"stream": {...}, "values": [["ts", "line"], ...]}
                if "values" in item:
                    for val in item["values"]:
                        if isinstance(val, (list, tuple)) and len(val) >= 2:
                            lines.append(str(val[1]))
                # Simple {"line": "..."} or {"message": "..."} format
                elif "line" in item:
                    lines.append(str(item["line"]))
                elif "message" in item:
                    lines.append(str(item["message"]))
    elif isinstance(data, dict):
        # Loki query_range result format
        if "data" in data and "result" in data.get("data", {}):
            for stream in data["data"]["result"]:
                if "values" in stream:
                    for val in stream["values"]:
                        if isinstance(val, (list, tuple)) and len(val) >= 2:
                            lines.append(str(val[1]))
        # Direct result array
        elif "result" in data:
            return _extract_lines_from_json(data["result"])

    return lines


class DedupLokiTool(BaseTool):
    """
    Wraps an existing Loki MCP tool and deduplicates its output
    before the LLM agent consumes it.
    """
    _wrapped_tool: BaseTool

    name: str = ""
    description: str = ""

    class Config:
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True

    def __init__(self, wrapped_tool: BaseTool, **kwargs):
        # Pull name/description from the wrapped tool
        super().__init__(
            name=wrapped_tool.name,
            description=wrapped_tool.description,
            **kwargs,
        )
        self._wrapped_tool = wrapped_tool
        # Preserve the original tool's schema
        self.args_schema = wrapped_tool.args_schema

    def _run(self, *args, run_manager: Optional[CallbackManagerForToolRun] = None, **kwargs) -> str:
        raw = self._wrapped_tool._run(*args, **kwargs)
        return _dedup_log_text(str(raw))

    async def _arun(self, *args, run_manager: Optional[AsyncCallbackManagerForToolRun] = None, **kwargs) -> str:
        raw = await self._wrapped_tool._arun(*args, **kwargs)
        return _dedup_log_text(str(raw))


def wrap_loki_tools(tools: list) -> list:
    """
    Takes a list of LangChain tools and wraps any Loki log query tools
    with deduplication. Returns a new list with wrapped tools.
    """
    loki_tool_names = {"query_loki_logs", "query_loki"}

    wrapped = []
    for tool in tools:
        if tool.name in loki_tool_names:
            print(f"[+] Wrapping tool '{tool.name}' with log deduplication")
            wrapped.append(DedupLokiTool(wrapped_tool=tool))
        else:
            wrapped.append(tool)

    return wrapped
