# Deploy AAP MCP server

| Guide | Path |
|-------|------|
| **Blank GCP → full stack** | [docs/DEPLOY-GCP-FROM-SCRATCH.md](../../../docs/DEPLOY-GCP-FROM-SCRATCH.md) |
| Greenfield RHEL + Podman + MCP | [docs/DEPLOY-AAP-CONTAINERIZED.md](../../../docs/DEPLOY-AAP-CONTAINERIZED.md) |
| OpenShift / brownfield MCP | [docs/DEPLOY-MCP.md](../../../docs/DEPLOY-MCP.md) |
| User, token, Cursor, Gemini | [docs/DEPLOY-AND-CONNECT.md](../../../docs/DEPLOY-AND-CONNECT.md) |
| Gemini paths + chat questions | [docs/CONNECT-GEMINI.md](../../../docs/CONNECT-GEMINI.md) |

Official: [Deploy the MCP server](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server)

## Choose a path

| Option | When | MCP base URL |
|--------|------|----------------|
| **Blank GCP** | New project, no AAP yet | Follow DEPLOY-GCP-FROM-SCRATCH (ask about RHEL 9+10 targets) |
| **OpenShift** | AAP Operator on OCP / ROSA | `https://<aap-mcp-route>` |
| **Podman on RHEL** | Containerized installer on RHEL 9/10 | `https://<fqdn>:8448` (or LB `:443`) |

Prefer clients on the aggregate endpoint: `{MCP_BASE_URL}/mcp` (all tools).

## Access required

| Role | Access |
|------|--------|
| Platform admin | OpenShift `oc` **or** RHEL host + installer + registry credentials |
| AAP admin / service user | Gateway UI/API for tokens |
| Network | Client → MCP HTTPS |

## Architecture

1. Client (Cursor / Gemini) sends tool calls with Bearer token  
2. AAP MCP validates token and proxies to Controller/Gateway  
3. Token RBAC + server read/write mode gate actions  
4. Results return to the client (and may go to an LLM provider)

## Toolsets

| Path | Purpose |
|------|---------|
| `job_management` | Jobs, templates, logs, relaunch |
| `inventory_management` | Inventories, hosts, groups |
| `system_monitoring` | Health, activity, instances |
| `user_management` | Users, teams, RBAC |
| `security_compliance` | Credentials metadata |
| `platform_configuration` | Settings, EEs, notifications |

URL: `{MCP_BASE_URL}/{toolset}/mcp` (also `{MCP_BASE_URL}/mcp/{toolset}`)

Wrong host (gateway UI) returns SPA HTML — use MCP route or `:8448`.

## OpenShift (summary)

```yaml
spec:
  mcp:
    disabled: false
    allow_write_operations: false
```

Apply `AnsibleMCPServer` if missing. Recreate CR after changing write mode.

## Podman / RHEL (summary)

Inventory must include `[ansiblemcp]` and MCP TLS vars. See full greenfield guide for:

- Non-root installer user (no global `ansible_become=true`)
- FQDN hostnames when Hub is present
- `automationmetrics_skip_install=true` on minimal AAP 2.7 labs
- `ansible-playbook -i inventory-growth ansible.containerized_installer.install`

## Token + clients

Dedicated MCP user → gateway token → Cursor `mcp.json` / Gemini templates under `configs/`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Non-root preflight fail | Remove inventory `ansible_become=true`; run as non-root |
| `[automationmetrics]` required | Skip install flag or deploy metrics group |
| HTML from MCP URL | Wrong host |
| Self-signed TLS client errors | Trust CA or use real certs |
| Write tools fail | Enable write + recreate MCP (OCP) or reinstall (Podman) |
