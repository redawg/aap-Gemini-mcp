# Deploy AAP MCP server

Official reference: [Deploy the MCP server on Ansible Automation Platform](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server)

## Architecture (short)

1. User prompts Gemini (MCP client / host)
2. Gemini maps intent → MCP tool call
3. AAP MCP authenticates with the user's AAP API token
4. Automation controller executes / returns API data
5. MCP normalizes response → Gemini → user

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

## Containerized install

### Inventory

```ini
[ansiblemcp]
aap.example.com

[all:vars]
mcp_allow_write_operations=false
mcp_ignore_certificate_errors=false
# Optional custom TLS
# mcp_tls_cert=/path/to/tls.crt
# mcp_tls_key=/path/to/tls.key
# Optional list API page size
# mcp_extra_settings='[{"setting": "DEFAULT_PAGE_SIZE", "value": "25"}]'
```

### Deploy

1. Merge variables into the AAP containerized installer inventory
2. Run the installer / upgrade playbook for the environment
3. Confirm pod: `podman ps` → look for `ansiblemcp`
4. Base URL: `https://aap.example.com:8448`

### Write access

- `false` (default): query only — overrides user write even if token has Write scope
- `true`: mutations allowed, still gated by token RBAC

## OpenShift / operator install

### Enable MCP on the AAP custom resource

```yaml
apiVersion: aap.ansible.com/v1alpha1
kind: AnsibleAutomationPlatform
metadata:
  name: aap
spec:
  mcp:
    disabled: false
    allow_write_operations: false
```

Optional self-signed ignore (prefer CA secret instead):

```yaml
spec:
  mcp:
    disabled: false
    allow_write_operations: false
    extra_settings:
      - setting: IGNORE_CERTIFICATE_ERRORS
        value: true
```

### Find URLs

| Item | Where |
|------|--------|
| AAP UI | Networking → Routes → AAP route Location |
| Admin password | Secrets → `aap-admin-password` |
| MCP base URL | Networking → Routes → `*-mcp` Location |

### Permission change after deploy

If `allow_write_operations` changes after the MCP CR exists:

1. Find `AnsibleMCPServer` with `-mcp` suffix
2. Delete the CR
3. Let the operator recreate it

### Custom CA (SELF_SIGNED_CERT_IN_CHAIN)

```bash
oc create secret generic aap-mcp-ca \
  --from-file=bundle-ca.crt=/path/to/ca.crt \
  -n <namespace>
```

On `AnsibleMCPServer`:

```yaml
spec:
  bundle_cacert_secret: aap-mcp-ca
```

Verify init logs mention adding the customer CA bundle; MCP pod logs should have no SSL errors.

## Create API token

1. Log into AAP as the integration user
2. Access Management → Users → select user → Tokens → Create token
3. Application: optional (blank = PAT)
4. Scope: Read or Write
5. Copy token once; export as `AAP_MCP_TOKEN`

Token capabilities = that user's RBAC ∩ server-level read/write mode.

## Dual-layer security

| Layer | Effect |
|-------|--------|
| Server `allow_write_operations` / `mcp_allow_write_operations` | Global read-only vs read-write |
| API token RBAC + scope | What that identity may do |

## Data exposure to LLMs

Always masked by AAP API: credential passwords, secret keys, vault secrets, SSH keys, stored API tokens.

Not masked (may reach Gemini/provider): hostnames, IPs, inventory vars, job logs, extra vars, survey answers.

Recommend: store secrets only in AAP credentials; restrict token org/inventory access.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `SELF_SIGNED_CERT_IN_CHAIN` | Mount CA via `bundle_cacert_secret` |
| HTTP 406 on job stdout | Ask Gemini to request JSON first |
| HTTP 400 with self-signed | Prefer CA trust; last resort `IGNORE_CERTIFICATE_ERRORS` / `mcp_ignore_certificate_errors=true` |
| Write tools fail though token is Write | Confirm server-level write is enabled and MCP CR was recreated after change |
| Gemini cannot reach MCP | Check firewall, route, DNS, TLS trust from the Gemini host |

## Standalone community server (optional)

For local/dev without platform-integrated MCP, see [ansible/aap-mcp-server](https://github.com/ansible/aap-mcp-server). Prefer the platform-deployed MCP for production AAP 2.6+/2.7+.
