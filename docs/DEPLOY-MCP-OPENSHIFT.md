# Deploy AAP MCP on OpenShift

Deploy the **Ansible Automation Platform MCP server** with the AAP Operator on OpenShift (`oc`).

| Target | When to use | MCP URL shape |
|--------|-------------|---------------|
| **OpenShift (operator)** | AAP installed via AAP Operator on OCP / ROSA | `https://<mcp-route>/…/mcp` |

Official Red Hat docs: [Deploy the MCP server](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server).

After MCP is up, continue with tokens + Gemini in [DEPLOY-AND-CONNECT.md](DEPLOY-AND-CONNECT.md).

---

## Prerequisites

- `oc` logged into the **same** cluster that hosts AAP  
- Cluster-admin or edit rights in the AAP namespace (often `aap`)  
- AAP Operator installed; AAP instance healthy  

```bash
oc login https://api.<cluster>:6443 --token='…'   # or kubeadmin
oc whoami --show-server
oc get ansibleautomationplatform -A
```

---

## Step A — Enable MCP on the platform CR

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

---

## Step B — Ensure `AnsibleMCPServer` exists

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

---

## Step C — Wait for workload + route

```bash
oc -n "$NS" rollout status deploy/aap-mcp --timeout=180s
oc -n "$NS" get pods,svc,route -l app.kubernetes.io/name=aap-mcp

export MCP_BASE_URL="https://$(oc -n "$NS" get route aap-mcp -o jsonpath='{.spec.host}')"
echo "$MCP_BASE_URL"
```

Typical route pattern: `https://aap-mcp-<instance>.apps.<cluster>`

---

## Step D — Smoke test

```bash
export AAP_MCP_TOKEN='…'   # from AAP UI Tokens or gateway API

curl -sk -X POST "${MCP_BASE_URL}/job_management/mcp" \
  -H "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
```

Expect HTTP 200 and JSON-RPC `serverInfo`. Root page (`GET $MCP_BASE_URL/`) lists toolset paths.

---

## Step E — Write mode (optional)

```bash
oc -n "$NS" patch ansiblemcpserver aap-mcp --type merge -p '
spec:
  allow_write_operations: true
'
# Per Red Hat: delete and recreate AnsibleMCPServer if write mode was changed after first deploy
```

---

## Notes

- MCP is **not** the AAP gateway host. Use the **`aap-mcp`** route.  
- Reconciler: `ansible-lightspeed-operator-controller-manager` (role `mcpserver`).  
- Changing write permissions after deploy: delete `AnsibleMCPServer` and recreate.

### Toolset URL shapes

```text
{BASE}/job_management/mcp
{BASE}/mcp/job_management
{BASE}/mcp
```

---

## Next

1. Create AAP token → `AAP_MCP_TOKEN`  
2. Wire Gemini CLI / Agent → [DEPLOY-AND-CONNECT.md](DEPLOY-AND-CONNECT.md)  
3. Templates: `configs/gemini-cli-settings.json`, `configs/gemini-agent-tools.json`  
