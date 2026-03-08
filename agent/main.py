import os
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

def main():
    print("==================================================")
    print(" Starting AI Triage Agent  ")
    print("==================================================")

    # Initialize the Ollama model connection
    ollama_host = os.environ.get("OLLAMA_HOST", "localhost")
    ollama_url = f"http://{ollama_host}:11434"
    
    print(f"\n[+] Initializing connection to Ollama at {ollama_url}...")
    try:
        llm = ChatOllama(
            model="gpt-oss:latest",
            base_url=ollama_url,
            temperature=0.1, # Low temperature for analytical triage tasks
        )
        
        # Test the connection with a simple prompt
        print("[+] Testing LLM connection...")
        response = llm.invoke([
            HumanMessage(content="Hello! Please reply with exactly 'Ollama connection successful.'")
        ])
        
        print("\n[LLM Response]:")
        print(f"  {response.content}")
        
    except Exception as e:
        print(f"\n[!] Failed to connect to Ollama. Is it running on port 11434?")
        print(f"Error details: {e}")

if __name__ == "__main__":
    main()
