#!/bin/bash

# Configuration
export OLLAMA_HOST="0.0.0.0:11434"

echo "=========================================================="
echo " Starting Ollama with Host Binding 0.0.0.0               "
echo " (Required for Minikube/Kubernetes connectivity)          "
echo "=========================================================="

# Stop existing instances
echo "Stopping existing Ollama instances..."
pkill -f "ollama serve" || true
pkill -f "ollama" || true

# Check if Ollama is still running on the port (likely as a background service)
if lsof -Pi :11434 -sTCP:LISTEN -t >/dev/null ; then
    echo "[!] Port 11434 is still in use. Attempting to stop ollama service..."
    sudo systemctl stop ollama 2>/dev/null || true
    sleep 1
fi

# Final check if port is cleared
if lsof -Pi :11434 -sTCP:LISTEN -t >/dev/null ; then
    echo "Error: Port 11434 is still in use by another process."
    echo "Please stop it manually before running this script."
    exit 1
fi

echo "Starting Ollama serve..."
ollama serve
