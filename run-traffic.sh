#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=========================================================="
echo " Starting K6 Load Generation for AI Triage Agent          "
echo "=========================================================="

echo "[1/2] Installing dependencies and bundling K6 script..."
cd k6
npm install
npm run build

echo "[2/2] Launching K6 Docker Container..."
echo "This container will run on your host network to reach the Minikube port-forward."
echo "(Press Ctrl+C to stop traffic generation)"
echo "----------------------------------------------------------"

# Use Docker Compose to start the K6 runner
# It is configured in k6/docker-compose.yml to run the bundled script
docker compose up k6
