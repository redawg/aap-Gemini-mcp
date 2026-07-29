# Examples

All examples use placeholders (`aap.example.com`). Replace with your environment.

## Example A — OpenShift AAP + Gemini CLI (read-only)

**Access**

- `oc login` to the AAP cluster  
- AAP admin for token  
- Gemini CLI with reachability to the MCP route  

**Enable MCP**

```yaml
spec:
  mcp:
    disabled: false
    allow_write_operations: false
```

**Record route**

```bash
oc -n aap get route | grep mcp
export MCP_BASE_URL='https://aap-mcp.apps.example.com'
```

**Token** — Read-scoped AAP token → `AAP_MCP_TOKEN`.

**Gemini CLI** (`~/.gemini/settings.json`)

```json
{
  "mcpServers": {
    "aap-job-mgmt": {
      "httpUrl": "https://aap-mcp.apps.example.com/job_management/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      }
    }
  }
}
```

**Verify**

1. `What MCP tools are available for my Ansible Automation Platform?`  
2. `List my recent Ansible Automation Platform jobs.`  

---

## Example B — RHEL containerized AAP + MCP + Cursor

**Access**

- RHEL 9/10 host, non-root install user with sudo  
- Containerized setup tarball + registry credentials  
- Cursor on a workstation that can reach `:8448`  

**Install** — follow [docs/DEPLOY-AAP-CONTAINERIZED.md](../../../docs/DEPLOY-AAP-CONTAINERIZED.md).

Key inventory fragments:

```ini
[ansiblemcp]
aap.example.com ansible_connection=local

[all:vars]
ansible_connection=local
automationmetrics_skip_install=true
mcp_allow_write_operations=false
mcp_tls_cert=/home/aap/certs/tls.crt
mcp_tls_key=/home/aap/certs/tls.key
registry_username=<rh-registry-user>
registry_password=<rh-registry-token>
```

```bash
ansible-playbook -i inventory-growth ansible.containerized_installer.install
export MCP_BASE_URL='https://aap.example.com:8448'
```

**User + token** — dedicated `mcp-service` superuser + write token (see [DEPLOY-AND-CONNECT.md](../../../docs/DEPLOY-AND-CONNECT.md) Step 4).

**Cursor** — merge into `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "aap-job-mgmt": {
      "url": "https://aap.example.com:8448/job_management/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_AAP_MCP_TOKEN"
      }
    },
    "aap-inv-mgmt": {
      "url": "https://aap.example.com:8448/inventory_management/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_AAP_MCP_TOKEN"
      }
    }
  }
}
```

Reload MCP in Cursor, then list job templates / projects.

---

## Example C — Gemini Agent Platform (trusted TLS + network allowlist)

Full steps: [docs/CONNECT-GEMINI.md](../../../docs/CONNECT-GEMINI.md) Path B.

**Access**

- GCP project + Agent Platform / Vertex APIs + `roles/mcp.toolUser`  
- MCP URL with a **publicly trusted** certificate (prefer hostname on **:443**)  
- AAP token for `Authorization: Bearer …`  

**Agent body** — start from `configs/gemini-agent-tools.json` (includes):

```json
{
  "base_environment": {
    "type": "remote",
    "network": { "allowlist": [{ "domain": "*" }] }
  },
  "tools": [
    {
      "type": "mcp_server",
      "name": "aap-job-mgmt",
      "url": "https://mcp.example.com/job_management/mcp",
      "headers": { "Authorization": "Bearer YOUR_AAP_TOKEN" }
    }
  ]
}
```

Register the MCP URL in Agent Registry, then interact via the Interactions API (see CONNECT-GEMINI).

**Verify**

1. `List job templates I can launch.`  
2. (Write mode only) `Launch job template X and report status.`  

---

## Example D — Add one toolset via Gemini CLI

```bash
export AAP_MCP_TOKEN='...'
export MCP_BASE_URL='https://aap.example.com:8448'
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT='your-gcp-project'
export GEMINI_CLI_TRUST_WORKSPACE=true

gemini mcp add --transport http aap-job-mgmt \
  "${MCP_BASE_URL}/job_management/mcp" \
  --header "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -s user

gemini mcp list
gemini --skip-trust -y -p "List Ansible job template names using MCP."
```

---

## Example E — Browser chat sandbox (Cloud Run)

Full steps: [docs/CONNECT-GEMINI.md](../../../docs/CONNECT-GEMINI.md) Path C.

```bash
export MCP_BASE_URL='https://mcp.example.com'
export AAP_MCP_TOKEN='...'
export SANDBOX_PASSWORD='choose-a-password'
export SESSION_SECRET="$(openssl rand -hex 32)"

cd sandbox
gcloud run deploy aap-mcp-sandbox --source=. --allow-unauthenticated \
  --service-account=aap-mcp-sandbox@PROJECT.iam.gserviceaccount.com \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=PROJECT,GOOGLE_CLOUD_LOCATION=global,MCP_BASE_URL=${MCP_BASE_URL},AAP_MCP_TOKEN=${AAP_MCP_TOKEN},SANDBOX_PASSWORD=${SANDBOX_PASSWORD},SESSION_SECRET=${SESSION_SECRET},GEMINI_MODEL=gemini-2.5-flash"
```

Open the Service URL → sign in with `SANDBOX_PASSWORD` → ask “List my AAP job templates.”
