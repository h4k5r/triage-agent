# AI Triage Agent Backend 🧠

FastAPI + LangGraph agent for Kubernetes triage and diagnostic investigations via Model Context Protocol (MCP).

## Supported LLM Providers

The agent supports **Google Cloud Vertex AI** (Gemini) as well as **Local Ollama**.

### 1. Google Cloud Vertex AI (Recommended for Cloud)

Set the following environment variables (or copy from `.env.example`):

```bash
export LLM_PROVIDER="vertexai"
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"   # Default
export VERTEX_MODEL="gemini-1.5-pro"        # or gemini-2.0-flash
```

**Authentication:**
- For local development:
  ```bash
  gcloud auth application-default login
  ```
- Or supply a service account key path:
  ```bash
  export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
  ```

### 2. Google AI Studio (Gemini API Key)

```bash
export LLM_PROVIDER="genai"
export GEMINI_API_KEY="your-api-key"
export GEMINI_MODEL="gemini-1.5-pro"
```

### 3. Local Ollama

```bash
export LLM_PROVIDER="ollama"
export OLLAMA_HOST="localhost"
export OLLAMA_MODEL="qwen3.5:9b-q8_0"
```

---

## Local Setup with `uv`

```bash
# Sync dependencies
uv sync

# Run the agent API server
uv run python main.py
```
