# 🔐 Kubernetes Secrets Guide

This guide covers all Kubernetes secrets required to run the **AI Triage Agent** stack, along with copy-paste commands using placeholders.

---

## 📋 Required Secrets Overview

| Secret Name | Target Pod | Required Keys | Description |
|-------------|------------|---------------|-------------|
| `mcp-github-env` | `mcp-github` | `GITHUB_PERSONAL_ACCESS_TOKEN` | Allows the agent to inspect source code and commit history on GitHub. |
| `gcp-adc` *(Recommended)* | `triage-agent` | `application_default_credentials.json` | ADC credentials for Vertex AI. Created from your local `gcloud auth application-default login`. |
| `gemini-secret` *(Optional)* | `triage-agent` | `GEMINI_API_KEY` | Needed if using Google Gemini via API key. |
| `gcp-sa-key` *(Optional)* | `triage-agent` | `key.json` | Needed if using Google Cloud Vertex AI via service account key file. |

---

## 1. GitHub MCP Secret (`mcp-github-env`)

The `mcp-github` pod fails to start with `CreateContainerConfigError` if this secret is missing.

### Option A: Create via `.env` file (Recommended)

1. Copy the example file:
   ```bash
   cp mcp/.env.example mcp/.env
   ```

2. Open `mcp/.env` and replace the placeholder with your GitHub Personal Access Token:
   ```env
   GITHUB_PERSONAL_ACCESS_TOKEN=ghp_yourActualGitHubTokenHere123456
   ```
   *(A placeholder like `GITHUB_PERSONAL_ACCESS_TOKEN=placeholder_token` is sufficient for testing if you do not need live GitHub queries).*

3. Load the secret into Kubernetes:
   ```bash
   ./mcp/load-secrets.sh
   ```

### Option B: Create directly via `kubectl`

Run this single command in your terminal:

```bash
kubectl create secret generic mcp-github-env \
  --from-literal=GITHUB_PERSONAL_ACCESS_TOKEN="ghp_yourPlaceholderToken123456" \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## 2. LLM Secrets for AI Triage Agent (`triage-agent`)

Depending on which LLM provider you use:

### Option A: Google Gemini API Key (`gemini-secret`)

If using Google Gemini with an API key:

1. Create the secret:
   ```bash
   kubectl create secret generic gemini-secret \
     --from-literal=GEMINI_API_KEY="AIzaSyYourPlaceholderGeminiApiKey123456" \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

2. Update the deployment to use the key:
   ```bash
   kubectl set env deployment/triage-agent \
     LLM_PROVIDER="genai" \
     GEMINI_API_KEY_FROM_SECRET=true \
     --from=secret/gemini-secret
   ```

### Option B: Google Cloud Vertex AI with Application Default Credentials (`gcp-adc`) *(Recommended)*

If using Vertex AI with your local `gcloud` login credentials (no service account key file needed):

1. Authenticate with `gcloud` on your host machine:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

2. Create the Kubernetes secret from your local ADC file:
   ```bash
   kubectl create secret generic gcp-adc \
     --from-file=application_default_credentials.json=$HOME/.config/gcloud/application_default_credentials.json \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

3. The `agent/kubernetes/deployment.yaml` already mounts this secret. Ensure it contains:
   ```yaml
   env:
   - name: GOOGLE_APPLICATION_CREDENTIALS
     value: "/var/secrets/google/application_default_credentials.json"
   volumeMounts:
   - name: gcp-adc-volume
     mountPath: /var/secrets/google
     readOnly: true
   volumes:
   - name: gcp-adc-volume
     secret:
       secretName: gcp-adc
       optional: true
   ```

4. Set the provider and project in the ConfigMap (`agent/kubernetes/configmap.yaml`):
   ```yaml
   LLM_PROVIDER: "vertexai"
   VERTEX_MODEL: "gemini-3.7-flash"
   GOOGLE_CLOUD_LOCATION: "global"
   GOOGLE_CLOUD_PROJECT: "your-gcp-project-id"
   ```

5. Apply and restart:
   ```bash
   kubectl apply -f agent/kubernetes/configmap.yaml
   kubectl rollout restart deployment/triage-agent
   ```

### Option C: Google Cloud Vertex AI with Service Account Key (`gcp-sa-key`)

If using Vertex AI with a service account JSON file:

1. Create the secret from your key file:
   ```bash
   kubectl create secret generic gcp-sa-key \
     --from-file=key.json=/path/to/your/service-account-key.json \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

2. Mount the key in `agent/kubernetes/deployment.yaml`:
   ```yaml
   env:
   - name: GOOGLE_APPLICATION_CREDENTIALS
     value: /var/secrets/google/key.json
   - name: GOOGLE_CLOUD_PROJECT
     value: "your-gcp-project-id"
   volumeMounts:
   - name: gcp-key-volume
     mountPath: /var/secrets/google
     readOnly: true
   volumes:
   - name: gcp-key-volume
     secret:
       secretName: gcp-sa-key
   ```

### Option D: Local Ollama (No Secrets Required)

If running Ollama locally on your host machine:
```bash
kubectl set env deployment/triage-agent LLM_PROVIDER="ollama"
```

---

## 3. Quick Fix Script (All Placeholders)

To quickly create placeholder secrets so all pods start without error:

```bash
# 1. Create GitHub MCP secret
kubectl create secret generic mcp-github-env \
  --from-literal=GITHUB_PERSONAL_ACCESS_TOKEN="placeholder_token" \
  --dry-run=client -o yaml | kubectl apply -f -

# 2. Restart failing pods
kubectl rollout restart deployment/mcp-github
kubectl rollout restart deployment/triage-agent
```

---

## 4. Verification

Verify that your secrets are created:
```bash
kubectl get secrets
```

Check that all pods are now running:
```bash
kubectl get pods
```
