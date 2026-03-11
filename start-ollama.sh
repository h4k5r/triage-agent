#!/bin/bash

# Configuration
export OLLAMA_HOST="0.0.0.0:11434"

echo "=========================================================="
echo " Starting Ollama with Host Binding 0.0.0.0               "
echo " (Required for Minikube/Kubernetes connectivity)          "
echo "=========================================================="

sudo systemctl stop ollama || sudo pkill ollama


OLLAMA_HOST=0.0.0.0 ollama serve
ollama run qwen3.5:9b-q8_0