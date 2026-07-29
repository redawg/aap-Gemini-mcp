# Deploy AAP MCP

Deploy the **Ansible Automation Platform MCP server** using either:

| Option | When to use | MCP URL shape |
|--------|-------------|---------------|
| **1. OpenShift (operator)** | AAP via AAP Operator on OCP / ROSA | `https://<mcp-route>/…/mcp` |
| **2. Podman on RHEL (containerized)** | AAP via Red Hat containerized installer on RHEL 9/10 | `https://<host>:8448/…/mcp` |

Official Red Hat docs: [Deploy the MCP server](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server).

After MCP is up, continue with tokens in [DEPLOY-AND-CONNECT.md](DEPLOY-AND-CONNECT.md), then Gemini AI in **[CONNECT-GEMINI.md](CONNECT-GEMINI.md)**.

---

## Option 1 — OpenShift (`oc`)

### Prerequisites

- `oc` logged into the **same** cluster that hosts AAP  
- Cluster-admin or edit rights in the AAP namespace (often `aap`)  
- AAP Operator installed; AAP instance healthy  

```bash
oc login https://api.<cluster>:6443 --token='…'   # or kubeadmin
oc whoami --show-server
oc get ansibleautomationplatform -A
```

### Step A — Enable MCP on the platform CR

```bash
NS=aap
NAME=aap   # CR name from: oc -n aap get ansibleautomationplatform

oc -n "$NS" patch ansibleautomationplatform "$NAME" --type merge -p '
spec:
  mcp:
    disabled: false
    allow_write_operations: false
'
```

Console alternative: **Operators → Ansible Automation Platform →** instance → **YAML** → add the same `spec.mcp` block.

### Step B — Ensure `AnsibleMCPServer` exists

```bash
oc -n "$NS" get ansiblemcpserver
```

If nothing appears within a few minutes, create it (Lightspeed / MCP operator reconciles this CR):

```bash
AAP_HOST=$(oc -n "$NS" get route aap -o jsonpath='{.spec.host}')

cat <<EOF | oc apply -f -
apiVersion: mcpserver.ansible.com/v1alpha1
kind: AnsibleMCPServer
metadata:
  name: aap-mcp
  namespace: ${NS}
spec:
  public_base_url: "https://${AAP_HOST}"
  allow_write_operations: false
EOF
```

Optional if MCP cannot trust AAP TLS:

```yaml
spec:
  extra_settings:
    - setting: IGNORE_CERTIFICATE_ERRORS
      value: true
```

Prefer a CA bundle secret (`bundle_cacert_secret`) over ignoring certs in production.

### Step C — Wait for workload + route

```bash
oc -n "$NS" rollout status deploy/aap-mcp --timeout=180s
oc -n "$NS" get pods,svc,route -l app.kubernetes.io/name=aap-mcp

export MCP_BASE_URL="https://$(oc -n "$NS" get route aap-mcp -o jsonpath='{.spec.host}')"
echo "$MCP_BASE_URL"
```

Typical route pattern: `https://aap-mcp-<instance>.apps.<cluster>`

### Step D — Smoke test

```bash
export AAP_MCP_TOKEN='…'   # from AAP UI Tokens or gateway API

curl -sk -X POST "${MCP_BASE_URL}/job_management/mcp" \
  -H "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
```

Expect HTTP 200 and JSON-RPC `serverInfo`. Root page (`GET $MCP_BASE_URL/`) lists toolset paths.

### Step E — Write mode (optional)

```bash
oc -n "$NS" patch ansiblemcpserver aap-mcp --type merge -p '
spec:
  allow_write_operations: true
'
# Per Red Hat: delete and recreate AnsibleMCPServer if write mode was changed after first deploy
```

### OpenShift notes

- MCP is **not** the AAP gateway host. Use the **`aap-mcp`** route.  
- Reconciler: `ansible-lightspeed-operator-controller-manager` (role `mcpserver`).  
- Changing write permissions after deploy: delete `AnsibleMCPServer` and recreate.

---

## Option 2 — Podman on RHEL (containerized installer)

Use this when AAP runs as **containers on RHEL 9/10** via the Red Hat **containerized installer** (Podman). The MCP server is an `ansiblemcp` container on **HTTPS port 8448**.

**Greenfield (install AAP + MCP from scratch):** follow the full runbook  
→ **[DEPLOY-AAP-CONTAINERIZED.md](DEPLOY-AAP-CONTAINERIZED.md)**

**Brownfield (AAP already installed):** add MCP to inventory and re-run the installer as below.

### Prerequisites

| Need | Notes |
|------|--------|
| Existing containerized AAP on RHEL 9/10 | Installer directory + inventory available |
| Non-root install user | Do not install as root |
| Firewall | **8448/tcp** (and **443** for UI) from MCP clients |
| TLS for MCP | `mcp_tls_cert` / `mcp_tls_key` |

### Step A — Inventory: add MCP host + vars

```ini
[ansiblemcp]
aap.example.com

[all:vars]
mcp_allow_write_operations=false
mcp_ignore_certificate_errors=false
mcp_tls_cert=/path/to/tls.crt
mcp_tls_key=/path/to/tls.key
```

For the lab sandbox agent (create/launch), set `mcp_allow_write_operations=true`.

Use the same FQDN as your other AAP groups. Keep `ansible_connection=local` for single-node installs.

### Step B — Re-run the containerized installer

From the extracted **containerized setup** directory (AAP 2.5+):

```bash
export ANSIBLE_COLLECTIONS_PATH="$PWD/collections:${ANSIBLE_COLLECTIONS_PATH:-}"
ansible-playbook -i inventory-growth ansible.containerized_installer.install
```

(Older docs mention `./setup.sh`; prefer the playbook shipped with your tarball.)

### Step C — Verify

```bash
podman ps | grep -i mcp
export MCP_BASE_URL='https://aap.example.com:8448'
```

### Step D — Smoke test

Same initialize `curl` as OpenShift, against `${MCP_BASE_URL}/job_management/mcp`.

### Step E — Write mode (optional)

Set `mcp_allow_write_operations=true` and re-run the installer.

On an already-running Podman MCP container, write mode is controlled by
`ALLOW_WRITE_OPERATIONS=true` in the container environment (recreate/restart the
`ansiblemcp` container after changing it). Confirm in MCP logs:

`Write operations: ENABLED`

With write mode on, toolsets expose create/launch tools (for example
`groups_create`, `job_templates_launch_create`). Create tools typically require
fields under a `requestBody` argument.

### Podman / RHEL pitfalls

| Issue | Fix |
|-------|-----|
| Preflight: non-root user | Never put `ansible_become=true` in `[all:vars]` |
| Preflight: `[automationmetrics]` required | `automationmetrics_skip_install=true` or deploy metrics |
| Hub + `localhost` hostname | Use an FQDN (`aap.example.com`) |
| MCP URL returns UI HTML | Wrong host — use `:8448`, not the gateway-only URL |

---

## Toolset URL shapes (both options)

```text
{BASE}/job_management/mcp
{BASE}/mcp/job_management
{BASE}/mcp
```

| Deploy | Example `{BASE}` |
|--------|------------------|
| OpenShift | `https://aap-mcp-<instance>.apps.<cluster>` |
| Podman on RHEL | `https://aap.example.com:8448` |

---

## Next

1. Create AAP token → `AAP_MCP_TOKEN`  
2. Wire Gemini CLI / Agent → [DEPLOY-AND-CONNECT.md](DEPLOY-AND-CONNECT.md)  
3. Templates: `configs/gemini-cli-settings.json`, `configs/gemini-agent-tools.json`  
