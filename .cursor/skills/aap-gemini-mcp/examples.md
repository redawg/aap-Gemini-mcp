# Examples

## Example A — Containerized AAP + Gemini CLI (read-only)

**Given**

- Host: `aap.corp.example.com`
- MCP: `https://aap.corp.example.com:8448`
- Goal: list jobs and inventory; no launches

**Inventory**

```ini
[ansiblemcp]
aap.corp.example.com

[all:vars]
mcp_allow_write_operations=false
mcp_ignore_certificate_errors=false
```

**Token**

Create AAP token with **Read** scope for a limited operator user.

**Gemini CLI** (`~/.gemini/settings.json`)

```json
{
  "mcpServers": {
    "aap-job-mgmt": {
      "httpUrl": "https://aap.corp.example.com:8448/job_management/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      }
    },
    "aap-inv-mgmt": {
      "httpUrl": "https://aap.corp.example.com:8448/inventory_management/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      }
    }
  }
}
```

**Verify prompts**

1. `What MCP tools are available for my Ansible Automation Platform?`
2. `List my recent Ansible Automation Platform jobs.`
3. `Summarize hosts in the production inventory.`

---

## Example B — OpenShift AAP + Gemini Agent (read-write jobs)

**Given**

- MCP route: `https://aap-mcp-apps.apps.cluster.example.com`
- Goal: Gemini Agent can launch job templates the token allows

**AAP CR**

```yaml
spec:
  mcp:
    disabled: false
    allow_write_operations: true
```

**Token**

Write-scoped token for a service account limited to specific job templates/orgs.

**Agent tools**

```json
{
  "type": "mcp_server",
  "name": "aap-job-mgmt",
  "url": "https://aap-mcp-apps.apps.cluster.example.com/job_management/mcp",
  "headers": {
    "Authorization": "Bearer YOUR_AAP_TOKEN"
  }
}
```

**Verify prompts**

1. `List job templates I can launch.`
2. `Launch job template X with extra vars {...} and report status.`

---

## Example C — Add one toolset via Gemini CLI

```bash
export AAP_MCP_TOKEN='...'
export MCP_BASE='https://aap.corp.example.com:8448'

gemini mcp add --transport http aap-job-mgmt \
  "${MCP_BASE}/job_management/mcp" \
  --header "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -s user

gemini mcp list
```
