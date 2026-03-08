#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=========================================================="
echo " Checking System Requirements for AI Triage Agent         "
echo "=========================================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for a command and optionally offer to install it (Linux/apt focus for now, easily extendable)
check_command() {
    local cmd=$1
    local name=$2
    local install_msg=$3

    if command -v "$cmd" >/dev/null 2>&1; then
        printf "[${GREEN}✓${NC}] %s is installed.\n" "$name"
    else
        printf "[${RED}X${NC}] %s is NOT installed.\n" "$name"
        if [ ! -z "$install_msg" ]; then
            printf "${YELLOW}---> To install %s:${NC}\n" "$name"
            printf "     %s\n" "$install_msg"
        fi
        echo ""
        REQUIREMENTS_MET=false
    fi
}

REQUIREMENTS_MET=true

echo "--- Infrastructure ---"
check_command "docker" "Docker" "Instructions: https://docs.docker.com/engine/install/"
check_command "minikube" "Minikube" "curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 && sudo install minikube-linux-amd64 /usr/local/bin/minikube"
check_command "kubectl" "kubectl" "curl -LO \"https://dl.k8s.io/release/\$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl\" && sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl"

echo "--- AI & Agents ---"
check_command "ollama" "Ollama" "curl -fsSL https://ollama.com/install.sh | sh"
check_command "uv" "uv (Python Package Manager)" "curl -LsSf https://astral.sh/uv/install.sh | sh"

echo "--- Application (Node.js) ---"
check_command "node" "Node.js" "Instructions: https://nodejs.org/en/download/package-manager"
check_command "npm" "npm" "Usually installed with Node.js."

echo "=========================================================="
if [ "$REQUIREMENTS_MET" = true ]; then
    printf "${GREEN}All system requirements are cleanly met! You are ready to go.${NC}\n"
    echo "Run ./run-minikube.sh to start the ecosystem."
else
    printf "${RED}Some requirements are missing.${NC}\n"
    echo "Please use the provided commands/links to install the missing software, then re-run this script."
    exit 1
fi
