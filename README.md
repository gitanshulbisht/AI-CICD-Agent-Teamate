# 🤖 AI CI/CD Agent Teammate

> A production-grade AI-powered DevOps agent that monitors GitHub Actions, diagnoses CI/CD failures, and manages ArgoCD deployments — all from your Slack or Telegram channel.

[![CI Test Pipeline](https://github.com/gitanshulbisht/AI-CICD-Agent-Teamate/actions/workflows/test-pipeline.yml/badge.svg)](https://github.com/gitanshulbisht/AI-CICD-Agent-Teamate/actions/workflows/test-pipeline.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![n8n](https://img.shields.io/badge/Powered%20by-n8n-orange)](https://n8n.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://docs.docker.com/compose/)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Agent Capabilities](#agent-capabilities)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Setup Guide](#setup-guide)
  - [Step 1: Clone & Configure Environment](#step-1-clone--configure-environment)
  - [Step 2: Provision Local Kubernetes + ArgoCD](#step-2-provision-local-kubernetes--argocd)
  - [Step 3: Configure External Services](#step-3-configure-external-services)
  - [Step 4: Start the n8n Agent](#step-4-start-the-n8n-agent)
  - [Step 5: Import Workflows into n8n](#step-5-import-workflows-into-n8n)
  - [Step 6: Configure n8n Credentials](#step-6-configure-n8n-credentials)
  - [Step 7: Wire Tool Workflow IDs](#step-7-wire-tool-workflow-ids)
  - [Step 8: Expose via Cloudflare Tunnel (Optional)](#step-8-expose-via-cloudflare-tunnel-optional)
- [Critical Configuration Notes](#critical-configuration-notes)
- [Tool Reference](#tool-reference)
- [Workflow Architecture](#workflow-architecture)
- [Safety Rules](#safety-rules)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)

---

## Overview

This project implements a fully autonomous **AI DevOps Agent** that lives in your chat (Slack or Telegram). You can ask it in plain English to:

- "What failed in the last CI run?"
- "Show me the logs for run 12345."
- "Trigger a rebuild."
- "What's the status of the production app in ArgoCD?"
- "Sync the staging application."

The agent uses an LLM (via OpenRouter) to understand intent, selects the right tool (GitHub CLI or ArgoCD CLI), executes it inside a Docker container, and replies back — all without leaving your chat.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Chat Platforms                           │
│          Slack ──────────────────── Telegram                    │
└──────────────────┬──────────────────────┬───────────────────────┘
                   │  Message In          │  Message In
                   ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     n8n Agent Container                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               AI Agent (LangChain)                       │    │
│  │    LLM: OpenRouter (configurable model)                  │    │
│  │    Memory: Window Buffer (per-user session)              │    │
│  └──────────────────┬──────────────────────────────────────┘    │
│                     │  Tool Selection                            │
│     ┌───────────────┼───────────────┐                           │
│     ▼               ▼               ▼                           │
│  GitHub Tools   ArgoCD Tools   (Extensible)                     │
│  ┌──────────┐  ┌───────────┐                                    │
│  │ gh CLI   │  │argocd CLI │   ← Baked into Docker image        │
│  └──────────┘  └───────────┘                                    │
└─────────────────────────────────────────────────────────────────┘
                   │  API Calls
     ┌─────────────┴─────────────┐
     ▼                           ▼
GitHub Actions API         ArgoCD Server
(gitanshulbisht/...)       (kind cluster)
```

Each "tool" is a **separate n8n sub-workflow** that gets called by the agent. This makes tools independently testable, auditable, and replaceable.

---

## Agent Capabilities

### GitHub Actions Tools

| Tool | Description |
|---|---|
| `github_get_failed_runs` | Lists the last 10 failed GitHub Actions runs with branch, status, and run ID |
| `github_get_run_logs` | Fetches the failure logs for a specific run ID (last 200 lines) |
| `github_trigger_rebuild` | Re-runs a specific failed GitHub Actions run |

### ArgoCD Tools

| Tool | Description |
|---|---|
| `argocd_app_status` | Gets the current health and sync status of an ArgoCD application |
| `argocd_sync_app` | Triggers a sync/deployment of an ArgoCD application |
| `argocd_app_history` | Fetches the deployment history of an ArgoCD application |

---

## Tech Stack

| Component | Technology |
|---|---|
| **Orchestration** | [n8n](https://n8n.io) v1.123.55 |
| **LLM** | [OpenRouter](https://openrouter.ai) (configurable model) |
| **GitHub Automation** | [GitHub CLI (`gh`)](https://cli.github.com) v2.49.0 |
| **CD / GitOps** | [ArgoCD](https://argo-cd.readthedocs.io) (latest) |
| **Local K8s** | [kind](https://kind.sigs.k8s.io) |
| **Helm** | [Helm](https://helm.sh) (for ArgoCD install) |
| **Containerization** | Docker + Docker Compose |
| **Tunnel** | [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) |
| **Chat** | Slack / Telegram |

---

## Prerequisites

Before you begin, ensure you have the following installed on your local machine:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (with Docker Compose v2)
- [Homebrew](https://brew.sh) (macOS)
- [GitHub CLI (`gh`)](https://cli.github.com) — installed locally for authentication setup
- [Cloudflare CLI (`cloudflared`)](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) — for public webhook exposure

You will also need accounts/access for:
- **GitHub** — a Personal Access Token (PAT) with `repo` and `workflow` scopes
- **OpenRouter** — an API key for LLM access
- **Slack** — a Slack App with a Bot Token and Signing Secret
  - *OR* **Telegram** — a bot token from BotFather
- **ArgoCD** — a running instance (set up in Step 2)

---

## Setup Guide

### Step 1: Clone & Configure Environment

```bash
git clone https://github.com/gitanshulbisht/AI-CICD-Agent-Teamate.git
cd AI-CICD-Agent-Teamate

# Copy the example env file
cp .env.example .env
```

Now edit `.env` and fill in all values:

```env
# n8n Admin UI Password
N8N_BASIC_AUTH_PASSWORD=your_secure_password_here

# GitHub — PAT needs: repo, workflow scopes
GITHUB_TOKEN=ghp_your_github_personal_access_token
GH_REPO=your_github_username/your_repository_name

# ArgoCD — see Step 2 for how to get this
ARGOCD_SERVER=host.docker.internal:8080
ARGOCD_AUTH_TOKEN=your_argocd_jwt_token

# Telegram Bot Token (from BotFather) — optional if using Slack
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# OpenRouter API Key — https://openrouter.ai/keys
OPENROUTER_API_KEY=your_openrouter_api_key

# Webhook URL — set after Step 8 (Cloudflare Tunnel)
# e.g. https://your-tunnel-name.trycloudflare.com
WEBHOOK_URL=https://your-cloudflare-tunnel-url
```

---

### Step 2: Provision Local Kubernetes + ArgoCD

This project uses [kind](https://kind.sigs.k8s.io) to run a local Kubernetes cluster and installs ArgoCD via Helm. A setup script automates everything:

```bash
chmod +x setup-local-infra.sh
./setup-local-infra.sh
```

The script will:
1. Check for and install `kind`, `helm`, and `kubectl` if missing (via Homebrew)
2. Create a local Kubernetes cluster named `cicd-agent-cluster`
3. Install ArgoCD into the `argocd` namespace via Helm
4. Wait for all ArgoCD pods to be `Ready`
5. Print the initial admin password

**After the script completes:**

> ⚠️ **Important:** A simple `kubectl port-forward` will frequently disconnect when your machine sleeps or the network changes. It is highly recommended to set up a persistent port-forwarding mechanism. 

For macOS users, you can create a `LaunchAgent` to keep the port-forward running automatically:

```bash
cat << 'EOF' > ~/Library/LaunchAgents/com.cicd-agent.argocd-portforward.plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cicd-agent.argocd-portforward</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/kubectl</string>
        <string>port-forward</string>
        <string>svc/argocd-server</string>
        <string>-n</string>
        <string>argocd</string>
        <string>8080:443</string>
        <string>--context</string>
        <string>kind-cicd-agent-cluster</string>
        <string>--address</string>
        <string>0.0.0.0</string>
    </array>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.cicd-agent.argocd-portforward.plist
```

Then open https://localhost:8080, log in with `admin` + the password printed by the script.

**Generate a permanent ArgoCD JWT token** for the agent:

```bash
# Log in via CLI
argocd login localhost:8080 --username admin --password <password-from-script> --insecure

# Generate a token (never expires — adjust as needed)
argocd account generate-token --account admin
```

Copy this token into your `.env` file as `ARGOCD_AUTH_TOKEN`.

---

### Step 3: Configure External Services

#### GitHub

Authenticate the GitHub CLI locally (this is for initial setup; the container uses `GITHUB_TOKEN`):

```bash
gh auth login
```

Ensure your `GITHUB_TOKEN` in `.env` has:
- `repo` — read/write access to the target repository
- `workflow` — ability to re-run workflow runs

#### Slack (if using Slack integration)

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app.
2. Under **OAuth & Permissions**, add the following **Bot Token Scopes**:
   - `channels:history`, `channels:read`
   - `chat:write`
   - `im:history`, `im:read`, `im:write`
3. Under **Event Subscriptions**, enable events and set the Request URL to your n8n webhook URL (available after Step 8):
   - `https://your-tunnel-url/webhook/slack-cicd-agent`
4. Subscribe to the **Bot Events**: `message.channels`, `message.im`
5. Install the app to your workspace and copy the **Bot User OAuth Token**.
6. Copy the **Signing Secret** from **Basic Information**.
7. Add the bot to the channels you want it to listen in.

You'll enter the Bot Token and Signing Secret into n8n credentials in Step 6.

#### Telegram (if using Telegram integration)

1. Message [@BotFather](https://t.me/BotFather) on Telegram.
2. Use `/newbot` to create a bot and copy the token into `TELEGRAM_BOT_TOKEN` in `.env`.
3. No webhook configuration needed — n8n handles it automatically.

---

### Step 4: Start the n8n Agent

```bash
docker compose up -d --build
```

This builds the custom Docker image (which includes `gh` CLI v2.49.0 and the `argocd` CLI) and starts n8n on port `5679`.

Verify it's running:
```bash
docker ps
# Should show: cicd_agent_n8n ... Up ... 0.0.0.0:5679->5678/tcp

# Check logs
docker logs cicd_agent_n8n --tail 30
```

Access the n8n UI at: **http://localhost:5679**

Login: `admin` / your `N8N_BASIC_AUTH_PASSWORD` from `.env`

---

### Step 5: Import Workflows into n8n

The workflows are stored as JSON files in the `workflows/` directory. Import them in this exact order (tools first, agent last):

**In the n8n UI:**  
Go to **Workflows → Import from File** for each:

#### Import Tool Sub-Workflows (order doesn't matter):
- `workflows/tools/github_get_failed_runs.json`
- `workflows/tools/github_get_run_logs.json`
- `workflows/tools/github_trigger_rebuild.json`
- `workflows/tools/argocd_app_status.json`
- `workflows/tools/argocd_sync_app.json`
- `workflows/tools/argocd_app_history.json`

#### Import Agent Workflows (import ONE based on your chat platform):
- `workflows/slack-agent-workflow.json` — for Slack
- `workflows/agent-workflow.json` — for Telegram

> ⚠️ **After importing**, note the **Workflow ID** of each tool workflow. You'll need them in Step 7.

---

### Step 6: Configure n8n Credentials

Go to **n8n Settings → Credentials** and create the following:

#### OpenRouter (for LLM)
- Type: **OpenAI API** (OpenRouter is API-compatible)
- API Key: your `OPENROUTER_API_KEY`
- Base URL: `https://openrouter.ai/api` (no trailing `/v1`)

In the AI Agent node, set the model to one of:
- `openai/gpt-4o-mini` (recommended for speed/cost)
- `anthropic/claude-3.5-sonnet` (recommended for quality)
- `google/gemini-2.0-flash` (fastest)

#### Slack (if using Slack)
- Type: **Slack OAuth2 API**
- Client ID and Secret from your Slack App's **Basic Information** page
  
*OR use a simpler Bot Token approach:*
- Type: **Slack API**
- Access Token: your Bot User OAuth Token (`xoxb-...`)

#### Telegram (if using Telegram)
- Type: **Telegram API**
- Access Token: your bot token from BotFather

---

### Step 7: Wire Tool Workflow IDs

This is the most critical step. Each tool in the agent workflow must be linked to its corresponding sub-workflow.

1. Open the **Slack CI/CD Agent Workflow** (or Telegram variant) in the n8n editor.
2. Click on each **Tool** node (e.g., `Tool: github_get_failed_runs`).
3. In the **Workflow** field, select the matching sub-workflow from the dropdown.
4. Repeat for all 6 tool nodes.
5. Click **Save**.

Additionally, for the tool workflows — ensure the Code nodes use JavaScript (not the "Execute Command" node) to prevent shell interpolation issues with template expressions. For example, `github_trigger_rebuild` correctly handles the `run_id` variable in JS:

```javascript
const { execSync } = require('child_process');
const data = $input.item.json;
const val = (data.query && data.query.run_id) ? data.query.run_id : data.run_id;
if (!val) { return [{ json: { stdout: '', stderr: 'No run_id provided.' } }]; }
try {
  const stdout = execSync('gh run rerun ' + val, { encoding: 'utf8', timeout: 30000 });
  return [{ json: { stdout: stdout || 'Done.', stderr: '' } }];
} catch(e) {
  return [{ json: { stdout: e.stdout || '', stderr: e.stderr || e.message } }];
}
```

> **Why?** The `Execute Command` node uses shell interpolation which can corrupt n8n template expressions like `{{ $json.run_id }}`. The JavaScript Code node has full control over input parsing.

Also ensure the **Tool: github_trigger_rebuild** node in the agent workflow uses:
- **Schema Type**: `Generate from JSON Example`
- **JSON Example**: `{"run_id": "12345678"}`

---

### Step 8: Expose via Cloudflare Tunnel (Optional but Required for Slack/Telegram webhooks)

Slack and Telegram need to send events to a public URL. Cloudflare Tunnel creates a free, temporary public URL without any port forwarding or firewall configuration:

```bash
# Install cloudflared (macOS)
brew install cloudflared

# Start tunnel (run in a dedicated terminal)
cloudflared tunnel --url http://localhost:5679
```

This will print a URL like:
```
https://random-words.trycloudflare.com
```

Copy this URL and:
1. Add it to your `.env` as `WEBHOOK_URL`
2. Update the **Slack Event Subscriptions** Request URL to `<your-tunnel-url>/webhook/slack-cicd-agent`
3. Restart n8n: `docker compose restart n8n`

> ⚠️ **Note:** The free Cloudflare Tunnel URL changes every time you restart `cloudflared`. For a persistent URL, use a [named tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/) with a custom domain.

---

## Critical Configuration Notes

### ⚠️ `github_trigger_rebuild` — Known Issue & Fix

The `github_trigger_rebuild` tool **must** use the JavaScript Code node, not the Execute Command node. The Execute Command node passes n8n expressions to the shell, which causes:
```
accepts at most 1 arg(s), received 2
/bin/sh: : Permission denied
```

**Root cause:** `gh run rerun {{ $json.run_id }}` is evaluated by the shell as two separate arguments if the expression is empty or unresolved.

**Fix:** Use a JavaScript Code node that explicitly parses the input and constructs the command string safely (see Step 7).

### n8n API Key for MCP Integration

To use the `n8n-mcp` MCP server (for AI assistants to directly manage n8n workflows):

1. In n8n: **Settings → n8n API → Create an API Key**
2. The key is a JWT — copy it and use it in your MCP client configuration

### Memory per User

The agent uses **Window Buffer Memory** with a `sessionKey` of `={{ $('Slack Trigger').item.json.user }}`. This means each Slack user gets their own independent conversation context.

---

## Tool Reference

### `github_get_failed_runs`
**Command:** `gh run list --status failure --limit 10 --json name,headBranch,status,conclusion,databaseId`  
**Returns:** JSON array of last 10 failed runs with names, branches, and IDs.

### `github_get_run_logs`
**Input:** `run_id` (GitHub Actions run ID, e.g., `27850514146`)  
**Command:** `gh run view <run_id> --log-failed | tail -n 200`  
**Returns:** Last 200 lines of failure logs for the specified run.

### `github_trigger_rebuild`
**Input:** `run_id`  
**Command:** `gh run rerun <run_id>` (executed via JavaScript Code node)  
**Returns:** Confirmation message or error.  
**⚠️ WRITE OPERATION** — Requires user confirmation before the agent will execute.

### `argocd_app_status`
**Input:** `app_name` (ArgoCD application name)  
**Command:** `argocd app get <app_name> --output json --server host.docker.internal:8080 --insecure`  
**Returns:** Full application health and sync status as JSON.

### `argocd_sync_app`
**Input:** `app_name`  
**Command:** `argocd app sync <app_name> --server host.docker.internal:8080 --insecure`  
**Returns:** Sync operation output.  
**⚠️ WRITE OPERATION** — Requires user confirmation before the agent will execute.

### `argocd_app_history`
**Input:** `app_name`  
**Command:** `argocd app history <app_name> --server host.docker.internal:8080 --insecure`  
**Returns:** Deployment history table.

---

## Workflow Architecture

```
Chat Message Received
        │
        ▼
   Slack/Telegram Trigger (n8n)
        │
        ▼
   AI Agent (LangChain ReAct)
   ├── LLM: OpenRouter
   ├── Memory: Window Buffer (per-user)
   └── Tools:
       ├── github_get_failed_runs  ──▶ [Sub-Workflow] ──▶ gh CLI
       ├── github_get_run_logs     ──▶ [Sub-Workflow] ──▶ gh CLI
       ├── github_trigger_rebuild  ──▶ [Sub-Workflow] ──▶ gh CLI
       ├── argocd_app_status       ──▶ [Sub-Workflow] ──▶ argocd CLI
       ├── argocd_sync_app         ──▶ [Sub-Workflow] ──▶ argocd CLI
       └── argocd_app_history      ──▶ [Sub-Workflow] ──▶ argocd CLI
        │
        ▼
   Reply sent back to chat channel
```

---

## Safety Rules

The agent's system prompt enforces a critical safety policy:

> **For any WRITE operation** (specifically `github_trigger_rebuild` and `argocd_sync_app`), the agent **MUST**:
> 1. Explain the exact impact of the action to the user.
> 2. Ask for explicit confirmation.
> 3. Only execute the tool after the user says **"Yes"** or **"Proceed"**.

This prevents accidental deployments or rebuilds triggered by ambiguous messages.

---

## Troubleshooting

### n8n UI stuck on loading
```bash
docker restart cicd_agent_n8n
# Wait ~15 seconds, then refresh
```

### `github_trigger_rebuild` fails with "Permission denied"
The `Execute Command` node is being used instead of the Code node. See [Step 7](#step-7-wire-tool-workflow-ids) for the fix.

### ArgoCD CLI authentication fails
The `ARGOCD_AUTH_TOKEN` in your `.env` has expired. Generate a new one:
```bash
argocd login localhost:8080 --username admin --password <password> --insecure
argocd account generate-token --account admin
# Paste the new token in .env, then: docker compose restart n8n
```

### ArgoCD Tools fail with "connection refused" or "TLS certificate mismatch"
1. **Connection Refused:** Ensure your `kubectl port-forward` is running and listening on `0.0.0.0`. If you didn't set up the LaunchAgent in Step 2, run:
   `kubectl port-forward svc/argocd-server -n argocd 8080:443 --context kind-cicd-agent-cluster --address 0.0.0.0`
   If the port-forward keeps dying, check if the `argocd-server` pod is in `CrashLoopBackOff` (often caused by stuck pre-upgrade jobs in Helm). You can fix the pod crash loop by running `kubectl delete pod -l app.kubernetes.io/name=argocd-server -n argocd --force`.
2. **TLS Mismatch:** Ensure your ArgoCD tools (`argocd_app_status`, etc.) include `--server host.docker.internal:8080 --insecure` in the command execution node to bypass strict TLS checks against the local docker network.

### Slack events not arriving
1. Verify Cloudflare Tunnel is running: `cloudflared tunnel --url http://localhost:5679`
2. Verify the Slack Event Subscriptions Request URL matches the tunnel URL exactly.
3. Check n8n webhook URL: should be `https://<tunnel>/webhook/slack-cicd-agent`.

### n8n doesn't see updated workflow (stale cache)
After making changes via the database or API directly, restart n8n:
```bash
docker restart cicd_agent_n8n
```

### LLM using wrong variable format
If the agent sends `{{ $json.run_id }}` as literal text, the tool's JSON Schema type is set to "Define using JSON Schema" instead of "Generate from JSON Example". Change the **Schema Type** to `Generate from JSON Example` and set `{"run_id": "example_id"}` as the example.

---

## Project Structure

```
AI-CICD-Agent-Teamate/
├── .env.example                    # Template for all required environment variables
├── .github/
│   └── workflows/
│       └── test-pipeline.yml       # Demo CI pipeline (intentional failure for testing)
├── Dockerfile.n8n                  # Custom n8n image with gh + argocd CLIs
├── docker-compose.yml              # Runs the n8n agent container
├── setup-local-infra.sh            # Automated kind cluster + ArgoCD setup script
├── workflows/
│   ├── slack-agent-workflow.json   # Main agent workflow (Slack)
│   ├── discord-agent-workflow.json # Main agent workflow (Discord variant)
│   ├── agent-workflow.json         # Main agent workflow (Telegram/generic)
│   └── tools/
│       ├── github_get_failed_runs.json   # Tool: list failed GH Actions runs
│       ├── github_get_run_logs.json      # Tool: get logs for a run
│       ├── github_trigger_rebuild.json   # Tool: re-run a failed CI run
│       ├── argocd_app_status.json        # Tool: get ArgoCD app status
│       ├── argocd_sync_app.json          # Tool: sync/deploy an ArgoCD app
│       └── argocd_app_history.json       # Tool: get ArgoCD deployment history
└── generate_workflows.py           # Script to regenerate tool workflow JSON files
```

---

## Contributing

Pull requests are welcome! When adding new tools:
1. Create a new sub-workflow JSON in `workflows/tools/`.
2. Add the tool to the agent workflow with appropriate description and `fromJson` schema.
3. Update this README's [Tool Reference](#tool-reference) section.
4. Ensure write operations include a confirmation step in the agent's system prompt.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
