#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=========================================================="
echo " Starting Minikube with Storage and Ingress Addons "
echo "=========================================================="

echo "Starting Minikube..."
# Consider adding flags like --cpus=4 --memory=8192 if you run out of resources 
# (the JVM running inside the LGTM container is quite heavy)
minikube start

echo "Enabling storage provisioners (for PVCs)..."
minikube addons enable default-storageclass
minikube addons enable storage-provisioner

echo "Enabling Ingress controller..."
minikube addons enable ingress

echo "=========================================================="
echo " Minikube is up and running!"
echo ""
echo " You can now run:"
echo "   ./load-to-minikube.sh "
echo "=========================================================="
