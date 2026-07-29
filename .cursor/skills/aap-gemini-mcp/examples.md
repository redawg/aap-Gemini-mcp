# Examples

## Example A — OpenShift AAP + Gemini CLI (read-only)

**Access used**

- OpenShift: `oc login` to AAP cluster  
- AAP admin for token  
- Gemini CLI on laptop with route reachability  

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

**Token**

Create AAP token with **Read** scope → `AAP_MCP_TOKEN`.

**Gemini CLI** (`~/.gemini/settings.json`)

```json
{
  "mcpServers": {
    "aap-job-mgmt": {
      "httpUrl": "https://aap-mcp.apps.example.com/job_management/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      }
    },
    "aap-inv-mgmt": {
      "httpUrl": "https://aap-mcp.apps.example.com/inventory_management/mcp",
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
3. `Summarize hosts in the production inventory.`  

---

## Example B — Gemini Agent Platform (read-write jobs)

**Access used**

- GCP project + Agent Platform API + `roles/mcp.toolUser`  
- MCP write enabled + Write-scoped AAP token  
- Public MCP HTTPS route  

**AAP CR**

```yaml
spec:
  mcp:
    disabled: false
    allow_write_operations: true
```

**Agent tool**

```json
{
  "type": "mcp_server",
  "name": "aap-job-mgmt",
  "url": "https://aap-mcp.apps.example.com/job_management/mcp",
  "headers": {
    "Authorization": "Bearer YOUR_AAP_TOKEN"
  }
}
```

Create agent via Managed Agents API (see `docs/DEPLOY-AND-CONNECT.md` Step 6b).

**Verify**

1. `List job templates I can launch.`  
2. `Launch job template X and report status.`  

---

## Example C — Add one toolset via Gemini CLI

```bash
export AAP_MCP_TOKEN='...'
export MCP_BASE_URL='https://aap-mcp.apps.example.com'

gemini mcp add --transport http aap-job-mgmt \
  "${MCP_BASE_URL}/job_management/mcp" \
  --header "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -s user

gemini mcp list
```

---
