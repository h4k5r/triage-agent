#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=========================================================="
echo " Building, Loading, and Deploying to Minikube             "
echo "=========================================================="

echo "Running Pre-flight Requirements Check..."
./check-requirements.sh

# Ensure minikube is running
if ! minikube status > /dev/null 2>&1; then
    echo "Starting Minikube..."
    ./minikube/start-minikube.sh
fi

echo "Ensuring local Docker Compose stack is stopped to free up ports..."
docker compose down || true

echo "[1/6] Building and sideloading Docker images natively..."
./minikube/load-to-minikube.sh

echo "[2/6] Deploying LGTM Stack..."
kubectl apply -f lgtm/kubernetes/

echo "[3/6] Deploying MCP Tool Servers..."
# Ensure secrets are loaded if exists
if [ -f "mcp/load-secrets.sh" ] && [ -f "mcp/.env" ]; then
    ./mcp/load-secrets.sh
fi
kubectl apply -f mcp/kubernetes/

echo "[4/6] Deploying Node Application..."
kubectl apply -f dummy-app/kubernetes/

echo "[5/6] Deploying AI Triage Agent..."
kubectl apply -f agent/kubernetes/

echo "[6/6] Waiting for deployments to become ready (this may take a minute)..."
kubectl rollout status deployment/lgtm
kubectl rollout status deployment/node-typescript-app
kubectl rollout status deployment/mcp-kubernetes
kubectl rollout status deployment/mcp-github
kubectl rollout status deployment/mcp-grafana
kubectl rollout status deployment/triage-agent

echo "=========================================================="
echo " All done! The Kubernetes stack is fully live."
echo ""
echo " Initializing port-forwarding so you can access the stack..."
echo "=========================================================="

./minikube/port-forward.sh
