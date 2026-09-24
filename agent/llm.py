import os
from google import genai

def get_llm():
    """
    Initializes and returns a Google GenAI Client and the model name.
    """
    provider = os.environ.get("LLM_PROVIDER", "").lower().strip()

    # Auto-detect provider if not explicitly specified
    if not provider:
        if any(os.environ.get(k) for k in ["GOOGLE_CLOUD_PROJECT", "GCP_PROJECT", "VERTEX_MODEL", "GOOGLE_APPLICATION_CREDENTIALS"]):
            provider = "vertexai"
        elif any(os.environ.get(k) for k in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]):
            provider = "genai"

    print(f"\n[+] Selected LLM Provider: {provider}")

    if provider in ["vertexai", "vertex", "google_vertex"]:
        model = os.environ.get("VERTEX_MODEL", "gemini-3.7-flash")
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION") or os.environ.get("VERTEX_LOCATION", "us-central1")

        print(f"[+] Initializing Google GenAI (Vertex): model={model}, project={project}, location={location}")

        client = genai.Client(
            vertexai=True,
            project=project,
            location=location
        )
        return client, model

    else:
        # Default fallback: Standard GenAI (AI Studio)
        model = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        print(f"[+] Initializing Google GenAI (AI Studio): model={model}")
        
        client = genai.Client(api_key=api_key)
        return client, model
