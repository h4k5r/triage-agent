import ollama
import os

host = os.environ.get("OLLAMA_HOST", "localhost")
print(f"Checking Ollama at {host}:11434")

try:
    models = ollama.list()
    print("Available models:")
    print(models)
    
    target = os.environ.get("OLLAMA_MODEL", "qwen3.5:9b-q8_0")
    print(f"Target model: {target}")
    
    found = any(m['name'] == target for m in models.get('models', []))
    print(f"Model found: {found}")
    
except Exception as e:
    print(f"Error: {e}")
