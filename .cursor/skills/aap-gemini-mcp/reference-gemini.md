# Connect Gemini to AAP MCP

Full runbook: [docs/DEPLOY-AND-CONNECT.md](../../../docs/DEPLOY-AND-CONNECT.md)

AAP MCP is a **remote Streamable HTTP** MCP server. Gemini must use HTTP (not stdio) and send `Authorization: Bearer <AAP_TOKEN>`.

## Access required for Gemini

### Gemini CLI

| Need | Notes |
|------|--------|
| Gemini CLI installed | https://google-gemini.github.io/gemini-cli/ |
| Edit `~/.gemini/settings.json` or `.gemini/settings.json` | Or use `gemini mcp add` |
| `AAP_MCP_TOKEN` in environment | Prefer env substitution over pasting into files committed to git |
| HTTPS reachability to `MCP_BASE_URL` | Install private CA in OS trust store if needed |

### Gemini Enterprise Agent Platform

| Need | Notes |
|------|--------|
| Google Cloud project | Billing + Agent Platform / Vertex access |
| Agent Platform API enabled | Per Google Cloud docs |
| IAM to create/update agents | Managed Agents API |
| `roles/mcp.toolUser` | Grant to user and agent SA when required for MCP tools |
| `gcloud` auth | User or service account |
| Network Agent Platform → AAP MCP | Public OpenShift route or approved private path |
| Streamable HTTP MCP | SSE-only / stdio not supported for managed agent MCP tools |

Docs: [Create and manage agents](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/create-manage)

---

## Gemini CLI

### settings.json

Use `httpUrl` + `headers` (not Cursor’s `type`/`url`):

```json
{
  "mcpServers": {
    "aap-job-mgmt": {
      "httpUrl": "https://MCP_BASE/job_management/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      },
      "timeout": 30000
    },
    "aap-inv-mgmt": {
      "httpUrl": "https://MCP_BASE/inventory_management/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      }
    }
  }
}
```

Repo template: `configs/gemini-cli-settings.json`.

### CLI commands

```bash
export AAP_MCP_TOKEN='...'
export MCP_BASE_URL='https://YOUR-MCP-ROUTE'

gemini mcp add --transport http aap-job-mgmt \
  "${MCP_BASE_URL}/job_management/mcp" \
  --header "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -s user

gemini mcp list
```

### Verify prompts

- `What MCP tools are available for my Ansible Automation Platform?`
- `List my Ansible Automation Platform job templates.`
- `Show hosts in inventory <name>.`

### Naming

Keep MCP server names ≤ ~20 characters (combined server+tool often capped at 64).

---

## Gemini Agent Platform (managed agent)

### Setup sequence

1. Confirm MCP is up and smoke-tested with the AAP token.  
2. Ensure GCP project + Agent Platform API + IAM (`mcp.toolUser` as needed).  
3. Confirm Agent Platform can resolve/reach `MCP_BASE_URL`.  
4. Create agent with `tools` entries of `type: mcp_server`.  
5. Deploy/enable agent runtime if required by your org.  
6. Chat-test with the same verification prompts.

### Agent tools JSON

Template: `configs/gemini-agent-tools.json`.

```json
{
  "id": "aap-ops-agent",
  "base_agent": "antigravity-preview-05-2026",
  "description": "Operates Ansible Automation Platform via remote MCP toolsets",
  "tools": [
    {
      "type": "mcp_server",
      "name": "aap-job-mgmt",
      "url": "https://MCP_BASE/job_management/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_AAP_TOKEN"
      }
    }
  ]
}
```

### Create via REST

```bash
curl -X POST \
  "https://aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/global/agents" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -d @configs/gemini-agent-tools.json
```

(Replace placeholders in the JSON first.)

### Connectivity patterns

| Situation | Approach |
|-----------|----------|
| MCP on public OpenShift route + valid TLS | Point agent `url` at toolset `/mcp` paths |
| Private AAP only | Expose approved HTTPS ingress reachable from Agent Platform |
| Token rotation | PATCH agent tools headers / secret injection; avoid git |

### Agent Platform constraints

- Streamable HTTP only (`tools/list` / `tools/call` over HTTP POST).  
- Deprecated SSE transport not supported.  
- Start with job + inventory toolsets; expand later.

---

## Cursor / Claude mcp.json (comparison)

| Cursor / AAP docs | Gemini CLI |
|-------------------|------------|
| `"type": "http"` | omit (use `httpUrl`) |
| `"url": "..."` | `"httpUrl": "..."` |
| `"headers": { "Authorization": "Bearer ..." }` | same |

Template: `configs/cursor-mcp.json`.

---

## Minimal connect order

1. `MCP_BASE_URL` from admin / `oc get route`  
2. `AAP_MCP_TOKEN` from AAP Tokens  
3. Enable needed toolsets only  
4. Configure Gemini CLI **and/or** Agent Platform  
5. Run verification prompts  
