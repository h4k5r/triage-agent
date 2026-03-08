#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=========================================================="
echo " Building and Loading Docker Images into Minikube "
echo "=========================================================="

# Ensure minikube is running before trying to load images
if ! minikube status > /dev/null 2>&1; then
    echo "Error: Minikube is not running. Please run 'minikube start' first."
    exit 1
fi

echo "[1/4] Building local Node App image..."
docker build -t triage-agent-app:latest ./dummy-app

echo "[2/4] Building local LGTM stack image..."
docker build -t triage-agent-lgtm:latest ./lgtm

echo "[3/4] Building local AI Agent image..."
docker build -t triage-agent-agent:latest ./agent

echo "[4/4] Building MCP server images..."
docker build -t mcp-github:latest -f mcp/github.Dockerfile mcp/
docker build -t mcp-kubernetes:latest -f mcp/kubernetes.Dockerfile mcp/
docker build -t mcp-grafana:latest -f mcp/grafana.Dockerfile mcp/

echo "[4/4] Sideloading images directly into Minikube cluster..."
# Using minikube image load is often faster/more reliable than eval $(minikube docker-env)
minikube image load triage-agent-app:latest
minikube image load triage-agent-lgtm:latest
minikube image load triage-agent-agent:latest
minikube image load mcp-github:latest
minikube image load mcp-kubernetes:latest
minikube image load mcp-grafana:latest

echo "=========================================================="
echo " Success! Images loaded."
echo ""
echo " You can now apply your manifests:"
echo "   kubectl apply -f dummy-app/kubernetes/"
echo "   kubectl apply -f lgtm/kubernetes/"
echo "   kubectl apply -f agent/kubernetes/"
echo "   kubectl apply -f mcp/kubernetes/"
echo "=========================================================="
