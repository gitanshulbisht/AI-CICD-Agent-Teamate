#!/bin/bash

set -e

echo "🚀 Starting Local Infrastructure Setup for CI/CD Agent..."

# 1. Prerequisite Checks
command -v docker >/dev/null 2>&1 || { echo >&2 "❌ Docker is required but it's not installed. Please install Docker Desktop."; exit 1; }

if ! command -v kind >/dev/null 2>&1; then
    echo "⚙️  kind not found. Attempting to install via Homebrew..."
    brew install kind
fi

if ! command -v helm >/dev/null 2>&1; then
    echo "⚙️  helm not found. Attempting to install via Homebrew..."
    brew install helm
fi

if ! command -v kubectl >/dev/null 2>&1; then
    echo "⚙️  kubectl not found. Attempting to install via Homebrew..."
    brew install kubectl
fi

# 2. Cluster Creation
echo "📦 Creating local Kubernetes cluster (cicd-agent-cluster) via kind..."
if kind get clusters | grep -q "cicd-agent-cluster"; then
    echo "✅ Cluster 'cicd-agent-cluster' already exists."
else
    kind create cluster --name cicd-agent-cluster
fi

# 3. ArgoCD Installation via Helm
echo "⚓ Installing ArgoCD via Helm..."
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

# Install or upgrade ArgoCD
helm upgrade --install argocd argo/argo-cd --namespace argocd --wait

echo "⏳ Waiting for ArgoCD pods to be ready (this may take a minute)..."
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s

# 4. Credential Extraction
echo "🔑 Extracting ArgoCD initial admin password..."
# Sometimes the secret takes a moment to be available
sleep 5
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

echo ""
echo "========================================================="
echo "🎉 Local Infrastructure Provisioned Successfully!"
echo "========================================================="
echo ""
echo "ArgoCD UI URL : https://localhost:8080"
echo "Username      : admin"
echo "Password      : $ARGOCD_PASSWORD"
echo ""
echo "💡 NEXT STEPS:"
echo "1. Run the following command in a new terminal tab to expose the ArgoCD UI:"
echo "   kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo ""
echo "2. Copy the password above into your .env file as ARGOCD_AUTH_TOKEN (after generating a permanent token) or use basic auth if configured."
echo "   (Note: For the n8n agent to use ARGOCD_AUTH_TOKEN, you should generate a JWT token via the ArgoCD CLI or UI)."
echo ""
echo "3. Run 'docker compose up -d' to start the CI/CD Agent."
echo "========================================================="
