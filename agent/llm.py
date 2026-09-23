import os
from typing import Optional
from langchain_core.language_models import BaseChatModel

def get_llm() -> BaseChatModel:
    """
    Initializes and returns a LangChain chat model.
    Supports Google Vertex AI, Google AI Studio (Gemini), and local Ollama.
    Configured via environment variables with intelligent auto-detection.
    """
    provider = os.environ.get("LLM_PROVIDER", "").lower().strip()

    # Auto-detect provider if not explicitly specified
    if not provider:
        if any(os.environ.get(k) for k in ["GOOGLE_CLOUD_PROJECT", "GCP_PROJECT", "VERTEX_MODEL", "GOOGLE_APPLICATION_CREDENTIALS"]):
            provider = "vertexai"
        elif any(os.environ.get(k) for k in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]):
            provider = "genai"
        else:
            provider = "ollama"

    print(f"\n[+] Selected LLM Provider: {provider}")

    if provider in ["vertexai", "vertex", "google_vertex"]:
        from langchain_google_vertexai import ChatVertexAI

        model = os.environ.get("VERTEX_MODEL", "gemini-1.5-pro")
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION") or os.environ.get("VERTEX_LOCATION", "us-central1")
        temperature = float(os.environ.get("LLM_TEMPERATURE", "0.1"))

        print(f"[+] Initializing ChatVertexAI: model={model}, project={project or '(default ADC)'}, location={location}")

        kwargs = {
            "model": model,
            "temperature": temperature,
            "location": location,
        }
        if project:
            kwargs["project"] = project

        return ChatVertexAI(**kwargs)

    elif provider in ["genai", "google_genai", "gemini"]:
        from langchain_google_genai import ChatGoogleGenerativeAI

        model = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
        temperature = float(os.environ.get("LLM_TEMPERATURE", "0.1"))
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        print(f"[+] Initializing ChatGoogleGenerativeAI: model={model} (API Key: {'Set' if api_key else 'Not Found'})")
        kwargs = {"model": model, "temperature": temperature}
        if api_key:
            kwargs["google_api_key"] = api_key
        return ChatGoogleGenerativeAI(**kwargs)

    else:
        # Default fallback: Ollama
        from langchain_ollama import ChatOllama

        ollama_host = os.environ.get("OLLAMA_HOST", "localhost")
        ollama_url = f"http://{ollama_host}:11434"
        ollama_model = os.environ.get("OLLAMA_MODEL", "qwen3.5:9b-q8_0")

        print(f"[+] Initializing ChatOllama at {ollama_url} with model {ollama_model}")

        return ChatOllama(
            model=ollama_model,
            base_url=ollama_url,
            temperature=0.1,
            num_ctx=16384,
            timeout=300,
        )


