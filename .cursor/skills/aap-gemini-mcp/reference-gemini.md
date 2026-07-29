# Connect Gemini to AAP MCP

**Full guide:** [docs/CONNECT-GEMINI.md](../../../docs/CONNECT-GEMINI.md)  
Also: [docs/DEPLOY-AND-CONNECT.md](../../../docs/DEPLOY-AND-CONNECT.md)

AAP MCP is a **remote Streamable HTTP** MCP server. Gemini must use HTTP (not stdio) and send `Authorization: Bearer <AAP_TOKEN>`.

## Paths

| Path | Doc section |
|------|-------------|
| Gemini CLI | CONNECT-GEMINI → Path A |
| Agent Platform managed agent | CONNECT-GEMINI → Path B |
| Browser chat sandbox (`sandbox/`) | CONNECT-GEMINI → Path C |

## Access required

### Gemini CLI

| Need | Notes |
|------|--------|
| Gemini CLI installed | https://google-gemini.github.io/gemini-cli/ |
| `~/.gemini/settings.json` or `.gemini/settings.json` | Or `gemini mcp add` |
| `AAP_MCP_TOKEN` in environment | Prefer env substitution |
| HTTPS to `MCP_BASE_URL` | Trust public CA; private CA only for local CLI |
| Vertex or API-key auth | e.g. `GOOGLE_GENAI_USE_VERTEXAI=true` |
| Trusted workspace for headless | `--skip-trust` / `GEMINI_CLI_TRUST_WORKSPACE=true` |

### Gemini Enterprise Agent Platform

| Need | Notes |
|------|--------|
| Google Cloud project | Billing + Agent / Vertex access |
| `aiplatform.googleapis.com` (+ Agent Registry as needed) | Enable APIs |
| IAM | Create agents + **`roles/mcp.toolUser`** |
| Publicly trusted MCP HTTPS | Self-signed fails; prefer **:443** |
| `base_environment.network.allowlist: ["*"]` | Sandbox egress is off by default |
| Streamable HTTP | SSE-only not supported |

Docs: [Create and manage agents](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/create-manage)

---

## Gemini CLI (summary)

Template: `configs/gemini-cli-settings.json` — use **`httpUrl`** + headers.

```bash
export AAP_MCP_TOKEN='...'
export MCP_BASE_URL='https://aap.example.com:8448'
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT='your-project'
export GEMINI_CLI_TRUST_WORKSPACE=true

gemini mcp add --transport http aap-job-mgmt \
  "${MCP_BASE_URL}/job_management/mcp" \
  --header "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -s user

gemini --skip-trust -y -p "List Ansible job template names using MCP."
```

Verify prompts: list tools, list job templates, show inventories.

Keep MCP server names ≤ ~20 characters.

---

## Gemini Agent Platform (summary)

1. Smoke-test MCP with a trusted cert (`curl` without `-k`).  
2. Enable APIs + grant `roles/mcp.toolUser`.  
3. Fill `configs/gemini-agent-tools.json` (`MCP_BASE_HOST`, token, network allowlist `*`).  
4. `POST .../agents` (LRO); confirm agent exists.  
5. Register each toolset URL in Agent Registry (`gcloud agent-registry services create …`).  
6. Call Interactions API or use org chat UI if available.  

For a reliable **login + chat** UI against AAP MCP, deploy **`sandbox/`** (Path C) instead of relying only on Interactions.

---

## Chat sandbox (summary)

```bash
cd sandbox
# set MCP_BASE_URL, AAP_MCP_TOKEN, SANDBOX_PASSWORD, GCP project
gcloud run deploy aap-mcp-sandbox --source=. --allow-unauthenticated \
  --service-account=aap-mcp-sandbox@PROJECT.iam.gserviceaccount.com \
  --set-env-vars=...
```

Open the Cloud Run URL → password → ask for job templates.

---

## Cursor comparison

| Cursor | Gemini CLI |
|--------|------------|
| `"type": "http"` | omit (use `httpUrl`) |
| `"url": "..."` | `"httpUrl": "..."` |
| `"headers": { "Authorization": "Bearer ..." }` | same |

---

## Minimal Gemini order

1. `MCP_BASE_URL` + trusted TLS  
2. `AAP_MCP_TOKEN`  
3. Pick CLI **and/or** Agent Platform **and/or** `sandbox/`  
4. Run verification prompts from CONNECT-GEMINI.md  
