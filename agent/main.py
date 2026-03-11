import os
import asyncio

from api import app
import uvicorn

async def main():
    print("==================================================")
    print(" Starting AI Triage Agent  ")
    print("==================================================")

    print("\n[DEBUG] Environment Variables:")
    for key, value in os.environ.items():
        if any(x in key for x in ["MCP", "GRAFANA", "KUBERNETES", "OLLAMA"]):
            print(f"  {key}={value}")

    print("\n[+] Starting FastAPI server on port 8000...")
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
