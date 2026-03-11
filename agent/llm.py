import os
from langchain_ollama import ChatOllama

def get_llm() -> ChatOllama:
    """
    Initializes and returns the LangChain ChatOllama connection.
    Uses environment variables for configuration with sensible defaults.
    """
    ollama_host = os.environ.get("OLLAMA_HOST", "localhost")
    ollama_url = f"http://{ollama_host}:11434"
    ollama_model = os.environ.get("OLLAMA_MODEL", "qwen3.5:9b-q8_0")
    
    print(f"\n[+] Initializing connection to Ollama at {ollama_url}")
    print(f"[+] Using model: {ollama_model}")
    
    llm = ChatOllama(
        model=ollama_model,
        base_url=ollama_url,
        temperature=0.1, # Low temperature for analytical triage tasks
        num_ctx=262144,    # Increased context for 54+ tools
        timeout=300,      # High timeout for complex multi-tool reasoning
    )
    
    return llm


