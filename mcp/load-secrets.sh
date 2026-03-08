#!/bin/bash

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ENV_FILE="$DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found."
    exit 1
fi

echo "=================================================="
echo " Loading MCP Secrets to Kubernetes                "
echo "=================================================="

# Use kubectl create secret --dry-run and pipe to kubectl apply for an idempotent "upsert"
kubectl create secret generic mcp-github-env --from-env-file="$ENV_FILE" --dry-run=client -o yaml | kubectl apply -f -

echo "=================================================="
echo " Success! Secret 'mcp-github-env' is updated.    "
echo "=================================================="
