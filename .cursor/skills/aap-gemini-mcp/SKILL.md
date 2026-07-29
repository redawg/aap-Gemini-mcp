---
name: aap-gemini-mcp
description: >-
  Deploys the Ansible Automation Platform (AAP) MCP server and connects Google
  Gemini (CLI or Agent Platform) to it. Use when the user asks to deploy AAP MCP,
  wire Gemini to Ansible Automation Platform, configure mcpServers for AAP
  toolsets, or connect Gemini Agent to job/inventory/security MCP endpoints.
---

# AAP MCP + Gemini

Follow:

- Deploy on OpenShift: [docs/DEPLOY-MCP-OPENSHIFT.md](../../../docs/DEPLOY-MCP-OPENSHIFT.md)
- Token + Gemini connect: [docs/DEPLOY-AND-CONNECT.md](../../../docs/DEPLOY-AND-CONNECT.md)

Summarized below for the agent.

## Access gate (ask if missing)

Do **not** invent routes or tokens. Confirm the user has:

1. **AAP** gateway URL + admin/service user (AAP 2.6+/2.7+)
2. **OpenShift** `oc`/console on the **same** cluster as AAP
3. **Gemini**: CLI and/or GCP project for Agent Platform (`roles/mcp.toolUser` as required)
4. Network: Gemini → MCP HTTPS

## Workflow checklist

```
Progress:
- [ ] 0. AAP up (controller /api/controller/v2/ping/)
- [ ] 1. OpenShift login to AAP cluster
- [ ] 2. Enable MCP (spec.mcp + AnsibleMCPServer if needed)
- [ ] 3. Record MCP_BASE_URL from *-mcp route (not gateway UI host)
- [ ] 4. Create AAP_MCP_TOKEN
- [ ] 5. Smoke-test MCP POST initialize
- [ ] 6. Gemini CLI and/or Agent Platform tools
- [ ] 7. Verify prompts
```

## Deploy MCP (OpenShift)

```yaml
# on AnsibleAutomationPlatform
spec:
  mcp:
    disabled: false
    allow_write_operations: false
```

If `AnsibleMCPServer` is not created automatically, apply it (Lightspeed reconciles):

```bash
AAP_HOST=$(oc -n aap get route aap -o jsonpath='{.spec.host}')
# create AnsibleMCPServer aap-mcp with public_base_url=https://$AAP_HOST
oc -n aap rollout status deploy/aap-mcp --timeout=180s
export MCP_BASE_URL="https://$(oc -n aap get route aap-mcp -o jsonpath='{.spec.host}')"
```

Toolsets: `{BASE}/job_management/mcp` (also `{BASE}/mcp/job_management`).

After flipping write mode, **delete/recreate** `AnsibleMCPServer`.

## Token

UI: Access Management → Users → Tokens → Create (Read vs Write).  
Or gateway API: `POST /api/gateway/v1/tokens/`.  
`export AAP_MCP_TOKEN=...` — never commit.

## Connect Gemini

Templates: `configs/gemini-cli-settings.json`, `configs/gemini-agent-tools.json`.

**CLI** — `httpUrl` + Bearer:

```bash
gemini mcp add --transport http aap-job-mgmt \
  "${MCP_BASE_URL}/job_management/mcp" \
  --header "Authorization: Bearer ${AAP_MCP_TOKEN}"
```

**Agent Platform** — agent `tools[]`:

```json
{
  "type": "mcp_server",
  "name": "aap-job-mgmt",
  "url": "https://MCP_HOST/job_management/mcp",
  "headers": { "Authorization": "Bearer TOKEN" }
}
```

Requires Streamable HTTP, GCP project, create-agent API, reachability to MCP. Details: [reference-gemini.md](reference-gemini.md).

## Verify

1. `What MCP tools are available for my Ansible Automation Platform?`
2. `List my Ansible Automation Platform job templates.`
3. `Show inventories and host counts.`

## Security

1. Default read-only MCP.
2. Least-privilege token RBAC.
3. No secrets in git.
4. Warn: inventory/job output may reach the LLM; credential secrets are masked by AAP.

## Agent behavior

1. Point users at `docs/DEPLOY-AND-CONNECT.md` for the full checklist.
2. If MCP not enabled and no `oc` to AAP cluster, list exact access still needed — do not start local bridges unless the user asks.
3. Fill configs from real `MCP_BASE_URL` / token after deploy.
4. Keep MCP server names ≤ ~20 characters.

## Additional resources

- [reference-deploy.md](reference-deploy.md)
- [reference-gemini.md](reference-gemini.md)
- [examples.md](examples.md)
- Official AAP MCP docs: https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server
- Gemini CLI MCP: https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html
- Gemini managed agents: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/create-manage
