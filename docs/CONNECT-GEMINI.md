# Connect Gemini AI to AAP MCP

End-to-end steps to use **Gemini** (CLI, Agent Platform, or the repo chat sandbox) with Ansible Automation Platform’s Model Context Protocol (MCP) server.

Prerequisites: MCP is already deployed and you have an AAP API token. If not, complete:

1. [DEPLOY-AAP-CONTAINERIZED.md](DEPLOY-AAP-CONTAINERIZED.md) or [DEPLOY-MCP.md](DEPLOY-MCP.md)
2. [DEPLOY-AND-CONNECT.md](DEPLOY-AND-CONNECT.md) through **Step 5** (user + token + smoke-test)

Official references:

- [Gemini CLI MCP](https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html)
- [Create and manage agents](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/create-manage)
- [Interact with agents](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/interact-with-agents)

---

## Choose a Gemini path

| Path | Best for | What you get |
|------|----------|--------------|
| **A. Gemini CLI** | Developers on a laptop | Terminal agent that calls AAP MCP tools |
| **B. Gemini Agent Platform** | Hosted managed agent in GCP | Agent resource + Interactions API |
| **C. Chat sandbox (this repo)** | Browser login + chat | Cloud Run web UI that uses Gemini + AAP MCP |

You can enable more than one path. **CLI** and the **chat sandbox** are the most reliable for MCP tool calls today.

---

## Shared requirements (all Gemini paths)

### 1. MCP base URL and token

```bash
export MCP_BASE_URL='https://aap.example.com:8448'   # Podman default
# OpenShift example (no :8448):
# export MCP_BASE_URL='https://aap-mcp.apps.example.com'

export AAP_MCP_TOKEN='...'   # gateway token for the dedicated MCP user
```

Tool URL shape:

```text
${MCP_BASE_URL}/job_management/mcp
${MCP_BASE_URL}/inventory_management/mcp
${MCP_BASE_URL}/system_monitoring/mcp
${MCP_BASE_URL}/user_management/mcp
${MCP_BASE_URL}/security_compliance/mcp
${MCP_BASE_URL}/platform_configuration/mcp
```

### 2. Publicly trusted HTTPS (critical for GCP / Agent Platform)

Gemini Agent Platform and many Google runtimes **reject self-signed MCP certificates**.

| Situation | What to do |
|-----------|------------|
| OpenShift with a public ACME / trusted ingress cert | Use the MCP route URL as-is |
| Podman/RHEL with installer self-signed certs | Replace MCP TLS with **Let’s Encrypt** (or your org CA that Google trusts) |
| Prefer standard **:443** (no `:8448`) | Put an HTTPS load balancer or reverse proxy in front of MCP (terminate TLS on 443, backend to MCP `:8086` HTTP or `:8448` HTTPS) |

Example: issue a Let’s Encrypt cert for the AAP FQDN and install it on the MCP nginx cert paths (containerized layout), then restart the MCP service. Verify **without** `-k`:

```bash
curl -sS -o /dev/null -w "%{http_code} ssl=%{ssl_verify_result}\n" \
  "${MCP_BASE_URL%/}/"
# ssl_verify_result=0 means the cert chain is trusted
```

### 3. Streamable HTTP only

AAP MCP speaks **Streamable HTTP** (JSON-RPC over `POST`, often with `Accept: application/json, text/event-stream`).  
Gemini Agent Platform does **not** support deprecated SSE-only MCP.

Smoke-test initialize:

```bash
curl -sS -D - -o /tmp/mcp-init.sse \
  -X POST "${MCP_BASE_URL}/job_management/mcp" \
  -H "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}'
```

Expect HTTP 200, an `Mcp-Session-Id` response header, and SSE/JSON containing `serverInfo`.

### 4. Naming

Keep MCP server names short (about **≤ 20 characters**). Many clients cap `serverName + toolName` at **64** characters.  
Repo templates use names like `aap-job-mgmt`, `aap-inv-mgmt`.

---

## Path A — Gemini CLI

### Prerequisites

- [Gemini CLI](https://google-gemini.github.io/gemini-cli/) installed
- Auth: API key **or** Vertex AI (`GOOGLE_GENAI_USE_VERTEXAI=true` + GCP project + credentials)
- Shell has `AAP_MCP_TOKEN` exported (preferred over committing tokens)

### Configure MCP servers

Template: [`configs/gemini-cli-settings.json`](../configs/gemini-cli-settings.json)

Copy into `~/.gemini/settings.json` and/or project `.gemini/settings.json` (gitignored). Replace `MCP_BASE_HOST` with your MCP host **including port** when using Podman (`aap.example.com:8448`).

```json
{
  "security": {
    "auth": {
      "selectedType": "vertex-ai"
    }
  },
  "mcpServers": {
    "aap-job-mgmt": {
      "httpUrl": "https://MCP_BASE_HOST/job_management/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      },
      "timeout": 30000
    },
    "aap-inv-mgmt": {
      "httpUrl": "https://MCP_BASE_HOST/inventory_management/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      },
      "timeout": 30000
    }
  }
}
```

Notes:

- Gemini CLI uses **`httpUrl`** (not Cursor’s `"type": "http"` + `"url"`).
- Prefer `${AAP_MCP_TOKEN}` in settings; export the real token in the environment.

### Add servers via CLI (optional)

```bash
export AAP_MCP_TOKEN='...'
export MCP_BASE_URL='https://aap.example.com:8448'

gemini mcp add --transport http aap-job-mgmt \
  "${MCP_BASE_URL}/job_management/mcp" \
  --header "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -s user

gemini mcp list
```

### Vertex AI auth example

```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT='your-gcp-project'
export GOOGLE_CLOUD_LOCATION='global'   # or a supported region
export GOOGLE_APPLICATION_CREDENTIALS='/path/to/sa.json'  # or use gcloud ADC
export AAP_MCP_TOKEN='...'
export GEMINI_CLI_TRUST_WORKSPACE=true  # needed for non-interactive / untrusted folders
```

### Run and verify

```bash
cd /path/to/your/project
gemini --skip-trust -y -p "Using AAP MCP tools, list Ansible job template names."
```

Interactive:

```bash
gemini --skip-trust
# then: List my Ansible Automation Platform job templates.
```

Expected: the model calls MCP tools (for example `job_templates_list`) and returns real AAP names.

### CLI troubleshooting

| Symptom | Fix |
|---------|-----|
| MCP servers listed as **Disabled** / untrusted folder | `GEMINI_CLI_TRUST_WORKSPACE=true` and/or `gemini --skip-trust` |
| Auth error | Set Vertex env vars or `GEMINI_API_KEY` / selected auth in settings |
| TLS errors | Use a publicly trusted MCP cert or install your CA in the OS trust store |
| Tools missing | Confirm `gemini mcp list`, token, and `${MCP_BASE_URL}/…/mcp` with curl |

---

## Path B — Gemini Enterprise Agent Platform (managed agent)

### Prerequisites

1. GCP project with billing
2. Enable APIs (names can vary by preview; at minimum Vertex / Agent Platform):

   ```bash
   gcloud services enable aiplatform.googleapis.com agentregistry.googleapis.com \
     --project="${GCP_PROJECT_ID}"
   ```

3. IAM on the project (user and/or runtime service account):

   - Permission to create agents
   - **`roles/mcp.toolUser`** (required to call MCP tools)
   - Typically `roles/aiplatform.user`

4. `gcloud auth login` / application-default credentials (or a CI service account)
5. MCP reachable from Google over **public HTTPS with a trusted certificate** (prefer hostname on **port 443**)

### Sandbox network allowlist (required)

By default, managed-agent sandboxes have **no egress**. You must allow network access when creating/updating the agent:

```json
"base_environment": {
  "type": "remote",
  "network": {
    "allowlist": [{ "domain": "*" }]
  }
}
```

Today only `domain: "*"` is accepted for unrestricted access.

### Create the agent

Template: [`configs/gemini-agent-tools.json`](../configs/gemini-agent-tools.json)

The template includes **built-in Gemini tools** plus AAP MCP:

| Tool type | Purpose |
|-----------|---------|
| `google_search` | Query the public web / grounding |
| `url_context` | Fetch and read specific URLs |
| `code_execution` | Run code in the managed sandbox |
| `filesystem` | Read/write files in the agent environment |
| `mcp_server` (×6) | AAP job, inventory, monitoring, users, security, platform toolsets |

1. Copy the template and replace `MCP_BASE_HOST` / `YOUR_AAP_TOKEN`.
2. Keep `system_instruction` and `base_environment.network` as in the template (instructs when to use MCP vs web vs code).
3. Create (long-running operation):

```bash
export GCP_PROJECT_ID='your-gcp-project'
export LOCATION='global'

curl -X POST \
  "https://aiplatform.googleapis.com/v1beta1/projects/${GCP_PROJECT_ID}/locations/${LOCATION}/agents" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -d @/path/to/filled-gemini-agent-tools.json
```

Poll the returned operation until `done`, then:

```bash
curl -sS \
  "https://aiplatform.googleapis.com/v1beta1/projects/${GCP_PROJECT_ID}/locations/${LOCATION}/agents/aap-ops-agent" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)"
```

### Update tools / network later

```bash
curl -X PATCH \
  "https://aiplatform.googleapis.com/v1beta1/projects/${GCP_PROJECT_ID}/locations/${LOCATION}/agents/aap-ops-agent?update_mask=tools,system_instruction,base_environment" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -d @/path/to/filled-gemini-agent-tools.json
```

### Register MCP servers in Agent Registry

Register each toolset URL so the project can discover/govern MCP endpoints:

```bash
export MCP_BASE_URL='https://mcp.example.com'   # trusted HTTPS, prefer :443

gcloud agent-registry services create aap-job-mgmt \
  --location=global \
  --display-name='AAP Job Management MCP' \
  --mcp-server-spec-type=NO_SPEC \
  --interfaces="url=${MCP_BASE_URL}/job_management/mcp,protocolBinding=JSONRPC"
```

Repeat for other toolsets (`aap-inv-mgmt`, …) with the matching `/…/mcp` paths.

### Interact via the Interactions API

```bash
curl -N -X POST \
  "https://aiplatform.googleapis.com/v1beta1/projects/${GCP_PROJECT_ID}/locations/global/interactions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Api-Revision: 2026-05-20" \
  -d "{
    \"stream\": true,
    \"background\": true,
    \"store\": true,
    \"agent\": \"aap-ops-agent\",
    \"environment\": {
      \"type\": \"remote\",
      \"network\": { \"allowlist\": [{ \"domain\": \"*\" }] }
    },
    \"input\": [{
      \"type\": \"user_input\",
      \"content\": [{ \"type\": \"text\", \"text\": \"List AAP job template names using MCP.\" }]
    }]
  }"
```

Docs: [Interact with agents](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/interact-with-agents).

### Agent Platform tips and limitations

- Prefer MCP URLs on **port 443** with a public CA; custom ports and self-signed certs often fail silently (tools never attach).
- Start with **job_management** + **inventory_management**; expand after verification.
- Rotate tokens by PATCHing `tools[].headers` (do not commit tokens).
- If the agent only uses sandbox tools (`list_dir`, `run_command`) and never hits your MCP access logs, check TLS, allowlist `*`, Agent Registry registration, and `roles/mcp.toolUser`.
- For a guaranteed browser chat experience against AAP MCP, use **Path C** (sandbox) or **Path A** (CLI).

---

## Path C — Browser chat sandbox (this repo)

The `sandbox/` app is a small FastAPI UI: password login → Gemini (Vertex) → AAP MCP tool calling. It is the easiest way to **log in and chat** against live AAP MCP.

### What it does

- Serves a login page + chat UI
- Loads all six AAP MCP toolsets
- Enables **Google Search**, **URL context**, and **code execution** alongside MCP (configurable via env)
- Uses Vertex Gemini (`gemini-2.5-flash` by default) with function calling bridged to MCP `tools/call`

Env toggles (default `true`): `ENABLE_GOOGLE_SEARCH`, `ENABLE_URL_CONTEXT`, `ENABLE_CODE_EXECUTION`.

**Note:** Vertex often rejects combining Google Search / URL context / code execution with custom MCP function declarations in one request. The sandbox picks a tool bundle by intent (web vs AAP) and falls back if a mix is rejected, so both web research and AAP MCP keep working.

If the model rejects mixing Search with function calling, the sandbox automatically falls back to MCP-only tools for that turn.

### Deploy to Cloud Run

```bash
export GCP_PROJECT_ID='your-gcp-project'
export REGION='us-central1'
export MCP_BASE_URL='https://mcp.example.com'          # trusted HTTPS
export AAP_MCP_TOKEN='...'
export SANDBOX_PASSWORD="$(openssl rand -base64 12)"
export SESSION_SECRET="$(openssl rand -hex 32)"

# Runtime SA in the same project (example)
gcloud iam service-accounts create aap-mcp-sandbox \
  --project="${GCP_PROJECT_ID}" \
  --display-name='AAP MCP Sandbox' || true

RUNTIME_SA="aap-mcp-sandbox@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding "${GCP_PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/aiplatform.user"

cd sandbox
gcloud run deploy aap-mcp-sandbox \
  --project="${GCP_PROJECT_ID}" \
  --region="${REGION}" \
  --source=. \
  --allow-unauthenticated \
  --service-account="${RUNTIME_SA}" \
  --memory=1Gi \
  --timeout=300 \
  --set-env-vars="^@^GOOGLE_CLOUD_PROJECT=${GCP_PROJECT_ID}@GOOGLE_CLOUD_LOCATION=global@MCP_BASE_URL=${MCP_BASE_URL}@GEMINI_MODEL=gemini-2.5-flash@AAP_MCP_TOKEN=${AAP_MCP_TOKEN}@SANDBOX_PASSWORD=${SANDBOX_PASSWORD}@SESSION_SECRET=${SESSION_SECRET}"
```

Open the printed **Service URL**, sign in with `SANDBOX_PASSWORD`, and try:

- “List my AAP job templates.”
- “List inventories and host counts.”
- “Show recent jobs and their status.”

### Local run (optional)

```bash
cd sandbox
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GOOGLE_CLOUD_PROJECT=... GOOGLE_CLOUD_LOCATION=global
export GOOGLE_APPLICATION_CREDENTIALS=...
export MCP_BASE_URL=... AAP_MCP_TOKEN=... SANDBOX_PASSWORD=devpass SESSION_SECRET=devsecret
uvicorn app:app --host 127.0.0.1 --port 8080
```

Note: the app sets `Secure` cookies; use HTTPS (Cloud Run) or adjust for local HTTP testing.

---

## Verification prompts (any path)

1. What MCP tools are available for Ansible Automation Platform?
2. List my Ansible Automation Platform job templates.
3. Show inventories and host counts.
4. List projects and their playbooks.
5. Search the web for Ansible Automation Platform MCP and summarize official docs.
6. Open https://docs.redhat.com (or a specific AAP doc URL) and extract the MCP deployment overview.
7. (Write mode only) Launch job template \<name\> and report status.

---

## Security

- Keep MCP **read-only** until you intentionally enable write operations and use a Write-scoped token.
- Use a **dedicated** AAP MCP user/token (not personal admin long-term).
- Never commit tokens, sandbox passwords, or service-account keys.
- AAP masks credential secrets in API/MCP responses; inventory variables and job logs may still reach the LLM provider.
- Prefer short-lived tokens and rotate agent `headers` when credentials change.

---

## Troubleshooting (Gemini-specific)

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Agent Platform create hangs / agent 404 | MCP TLS not publicly trusted | Install LE/public cert; re-create or PATCH agent |
| Agent chats but never calls MCP | No sandbox egress; tools not attached | Set `base_environment.network.allowlist` to `*`; use :443 + trusted cert; register Agent Registry services |
| `SELF_SIGNED_CERT_IN_CHAIN` / curl fails without `-k` | Self-signed MCP | Replace certs; verify `ssl_verify_result=0` |
| Gemini CLI MCP disabled | Untrusted workspace | `--skip-trust` / `GEMINI_CLI_TRUST_WORKSPACE=true` |
| 401/403 from MCP | Bad token / RBAC | Recreate gateway token; check MCP user roles |
| MCP returns HTML SPA | Wrong host (AAP UI gateway) | Use MCP route or `:8448` / LB hostname |
| Cloud Run sandbox 500 on chat | Missing Vertex IAM or MCP env | Grant `roles/aiplatform.user` to runtime SA; check `MCP_BASE_URL` / `AAP_MCP_TOKEN` |

---

## Related files

| Path | Purpose |
|------|---------|
| [`configs/gemini-cli-settings.json`](../configs/gemini-cli-settings.json) | Gemini CLI MCP template |
| [`configs/gemini-agent-tools.json`](../configs/gemini-agent-tools.json) | Managed agent create/PATCH body |
| [`sandbox/`](../sandbox/) | Browser chat app (Dockerfile + FastAPI) |
| [`configs/.env.example`](../configs/.env.example) | Env var names |
| [DEPLOY-AND-CONNECT.md](DEPLOY-AND-CONNECT.md) | MCP user, token, Cursor, overview |
