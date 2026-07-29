# Deploy AAP MCP server

Full runbook: [docs/DEPLOY-AND-CONNECT.md](../../../docs/DEPLOY-AND-CONNECT.md)

Official reference: [Deploy the MCP server on Ansible Automation Platform](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server)

## Access required

| Role | Access |
|------|--------|
| Platform admin | OpenShift `oc`/console on AAP cluster **or** containerized installer host |
| AAP admin / service user | Gateway UI/API to create tokens and verify automation |
| Network | Client → MCP HTTPS; MCP → AAP APIs (in-cluster for operator) |

## Architecture

1. Gemini (MCP client) sends tool calls with Bearer token  
2. AAP MCP validates token and proxies to Controller/Gateway  
3. RBAC of the token + server read/write mode gate actions  
4. Results return to Gemini (and may be sent to the LLM provider)

## Toolsets

| Toolset path | Purpose |
|--------------|---------|
| `job_management` | List/launch jobs, templates, logs, relaunch |
| `inventory_management` | Inventories, hosts, groups |
| `system_monitoring` | Health, gateway, audit-style views |
| `user_management` | Users, teams, RBAC |
| `security_compliance` | Credentials metadata, security policies |
| `platform_configuration` | Settings, licenses, EEs |

URL pattern: `{MCP_BASE_URL}/{toolset}/mcp`

**Do not** use the AAP gateway UI hostname unless that host is also the MCP route. Wrong host returns SPA HTML.

## Detect “MCP not deployed yet”

- Gateway `service_types`: only `gateway`, `controller`, `hub`, `eda`
- `oc get route -A | grep mcp` empty
- Guessed `*-mcp.apps…` hosts return router 503 with no backing service

## Containerized install

### Inventory

```ini
[ansiblemcp]
aap.example.com

[all:vars]
mcp_allow_write_operations=false
mcp_ignore_certificate_errors=false
# mcp_tls_cert=/path/to/tls.crt
# mcp_tls_key=/path/to/tls.key
# mcp_extra_settings='[{"setting": "DEFAULT_PAGE_SIZE", "value": "25"}]'
```

### Deploy

1. Merge into containerized installer inventory  
2. Run install/upgrade  
3. `podman ps` → `ansiblemcp`  
4. Base URL: `https://aap.example.com:8448`

## OpenShift / operator install

### Enable MCP

```yaml
spec:
  mcp:
    disabled: false
    allow_write_operations: false
```

```bash
oc -n "$NS" patch ansibleautomationplatform "$NAME" --type merge -p '
spec:
  mcp:
    disabled: false
    allow_write_operations: false
'
oc -n "$NS" get ansiblemcpserver
oc -n "$NS" get deploy,pods,route | grep -i mcp
```

### Find URLs

| Item | Where |
|------|--------|
| AAP UI | Route for gateway / AAP |
| Admin password | Secret e.g. `aap-admin-password` |
| MCP base URL | Route for `*-mcp` → Location |

### Permission change after deploy

Delete `AnsibleMCPServer` (name often ends with `-mcp`) and let the operator recreate after changing `allow_write_operations`.

### Custom CA

```bash
oc create secret generic aap-mcp-ca \
  --from-file=bundle-ca.crt=/path/to/ca.crt \
  -n "$NS"
```

```yaml
# on AnsibleMCPServer
spec:
  bundle_cacert_secret: aap-mcp-ca
```

## Create API token

1. AAP UI → Access Management → Users → Tokens → Create  
2. Scope Read or Write  
3. `export AAP_MCP_TOKEN=...`

Gateway API:

```bash
curl -sk -u "admin:${AAP_PASSWORD}" \
  -H 'Content-Type: application/json' \
  -d '{"description":"gemini-mcp","scope":"write"}' \
  "${AAP_URL%/}/api/gateway/v1/tokens/"
```

## Dual-layer security

| Layer | Effect |
|-------|--------|
| Server `allow_write_operations` | Global read-only vs read-write |
| Token RBAC + scope | What that identity may do |

## Data exposure to LLMs

Masked: credential passwords, secret keys, vault, SSH keys, stored API tokens.  
Not masked: hostnames, IPs, inventory vars, job logs, extra vars, survey answers.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `SELF_SIGNED_CERT_IN_CHAIN` | `bundle_cacert_secret` |
| HTTP 406 on job stdout | Request JSON first |
| HTTP 400 + self-signed | Prefer CA; last resort `IGNORE_CERTIFICATE_ERRORS` |
| Write tools fail | Enable write + recreate MCP CR |
| HTML from “MCP” URL | Wrong host — use MCP route |
| `oc` points at different cluster | `oc login` to AAP’s API server |

## Standalone community server (optional)

[ansible/aap-mcp-server](https://github.com/ansible/aap-mcp-server) for local/dev only. Prefer platform MCP for workshops/production once operator MCP is available.
