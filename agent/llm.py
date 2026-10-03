import os
import ollama
from google import genai

def get_llm():
    """
    Initializes and returns an LLM client, the model name, and the provider name.
    Supports Ollama, Google Vertex AI, and Google AI Studio (GenAI).
    """
    provider = os.environ.get("LLM_PROVIDER", "").lower().strip()

    # Auto-detect provider if not explicitly specified
    if not provider:
        if any(os.environ.get(k) for k in ["OLLAMA_MODEL", "OLLAMA_HOST"]):
            provider = "ollama"
        elif any(os.environ.get(k) for k in ["GOOGLE_CLOUD_PROJECT", "GCP_PROJECT", "VERTEX_MODEL", "GOOGLE_APPLICATION_CREDENTIALS"]):
            provider = "vertexai"
        elif any(os.environ.get(k) for k in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]):
            provider = "genai"
        else:
            provider = "ollama"

    print(f"\n[+] Selected LLM Provider: {provider}")

    if provider in ["ollama", "local"]:
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        if not host.startswith("http://") and not host.startswith("https://"):
            host = f"http://{host}:11434" if ":" not in host else f"http://{host}"
        model = os.environ.get("OLLAMA_MODEL", "gemma4:e4b")
        print(f"[+] Initializing Ollama (AsyncClient): model={model}, host={host}")
        client = ollama.AsyncClient(host=host)
        return client, model, "ollama"

    elif provider in ["vertexai", "vertex", "google_vertex"]:
        model = os.environ.get("VERTEX_MODEL", "gemini-2.5-flash")
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION") or os.environ.get("VERTEX_LOCATION", "us-central1")

        print(f"[+] Initializing Google GenAI (Vertex): model={model}, project={project}, location={location}")

        client = genai.Client(
            vertexai=True,
            project=project,
            location=location
        )
        return client, model, "vertexai"

    else:
        # Default fallback: Standard GenAI (AI Studio)
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        print(f"[+] Initializing Google GenAI (AI Studio): model={model}")
        
        client = genai.Client(api_key=api_key)
        return client, model, "genai"
