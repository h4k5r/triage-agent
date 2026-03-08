#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=========================================================="
echo " Port-Forwarding Kubernetes Services to Host Machine      "
echo "=========================================================="

# Kill any existing kubectl port-forward processes to avoid binding errors
pkill -f "kubectl port-forward svc/lgtm" || true
pkill -f "kubectl port-forward svc/node-typescript-app" || true

echo "Forwarding LGTM Grafana dashboard to port 3001..."
kubectl port-forward svc/lgtm 3001:3001 &

echo "Forwarding LGTM OTLP endpoints to ports 4317 & 4318..."
kubectl port-forward svc/lgtm 4317:4317 &
kubectl port-forward svc/lgtm 4318:4318 &

echo "Forwarding Node.js App to port 3000..."
kubectl port-forward svc/node-typescript-app 3000:3000 &

echo "Forwarding MCP Servers to ports 8080-8082..."
kubectl port-forward svc/mcp-github 8080:8080 &
kubectl port-forward svc/mcp-kubernetes 8081:8080 &
kubectl port-forward svc/mcp-grafana 8082:8080 &

echo "=========================================================="
echo " Success! Traffic is now routing from your host into the cluster."
echo " Press Ctrl+C at any time to stop forwarding."
echo "=========================================================="

# Wait indefinitely to keep the port forwards alive in the foreground
wait
