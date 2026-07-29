# Deploy AAP MCP and connect Gemini

End-to-end runbook: enable the Ansible Automation Platform (AAP) MCP server, authenticate, then connect a Gemini agent (CLI or Agent Platform).

Official AAP reference: [Deploy the MCP server on Ansible Automation Platform](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server)

**Platform deploy how-tos (OpenShift `oc` vs AWS containers/ECS):** [DEPLOY-MCP-OPENSHIFT-AND-AWS.md](DEPLOY-MCP-OPENSHIFT-AND-AWS.md)

---

## What you need access to

Collect these **before** starting. Without each item, a later step will block.

### A. Ansible Automation Platform

| Need | Why |
|------|-----|
| AAP **2.6+** (prefer **2.7+**) already installed | MCP is a platform component |
| AAP **admin** (or org admin) UI/API login | Create tokens; verify jobs/inventories |
| AAP console URL (gateway) | e.g. `https://aap-aap.apps.<cluster>/` |
| Network reachability to AAP from your laptop | Token create + API checks |

### B. OpenShift (operator-based AAP — typical for workshops / AWS)

| Need | Why |
|------|-----|
| OpenShift console **or** `oc` login to the **same** cluster that hosts AAP | Edit `AnsibleAutomationPlatform` CR / view routes |
| Permission to edit the AAP operator CR in the AAP namespace | Set `spec.mcp` |
| Ability to list Routes / Deployments in that namespace | Copy MCP URL; confirm pods healthy |

Containerized AAP on RHEL instead of OpenShift? You need SSH/inventory access to re-run the containerized installer instead of `oc`.

### C. Gemini (pick one or both)

| Path | Need |
|------|------|
| **Gemini CLI** | [Gemini CLI](https://google-gemini.github.io/gemini-cli/) installed; ability to edit `~/.gemini/settings.json` or project `.gemini/settings.json`; outbound HTTPS to the MCP URL |
| **Gemini Enterprise Agent Platform** | Google Cloud project; Gemini Enterprise Agent Platform / Vertex AI access; `gcloud` auth; IAM to create agents; **`roles/mcp.toolUser`** on the project for MCP tool use; network path from Agent Platform → AAP MCP (public HTTPS or approved private connectivity) |

### D. Secrets (never commit)

| Secret | Use |
|--------|-----|
| AAP OAuth/API token (`AAP_MCP_TOKEN`) | `Authorization: Bearer …` on every MCP call |
| Optional: OpenShift kubeadmin / token | Deploy MCP via operator |
| Optional: Google Cloud credentials | Create/manage Gemini agents |

Store locally in `.env` (gitignored). Templates: `configs/.env.example`.

---

## Architecture

```
You → Gemini (CLI or Agent Platform)
        → HTTPS MCP tool call + Bearer token
          → AAP MCP server (OpenShift route or :8448)
            → AAP Controller / Gateway APIs (RBAC of token)
              → jobs, inventory, etc.
```

**Dual security**

1. **Server-level**: `allow_write_operations` / `mcp_allow_write_operations` (read-only vs read-write)
2. **User-level**: AAP token RBAC + token scope (Read vs Write)

Start **read-only** unless you intentionally want Gemini to launch jobs.

---

## Progress checklist

```
- [ ] 0. Confirm AAP is up (gateway + controller API)
- [ ] 1. Access OpenShift (or containerized installer host)
- [ ] 2. Enable MCP on AAP (operator CR or inventory)
- [ ] 3. Wait for MCP pods / route; record MCP_BASE_URL
- [ ] 4. Create AAP API token → AAP_MCP_TOKEN
- [ ] 5. Smoke-test MCP HTTPS endpoint
- [ ] 6a. Configure Gemini CLI  and/or
- [ ] 6b. Create Gemini Agent with mcp_server tools
- [ ] 7. Verify with sample prompts
```

---

## Step 0 — Confirm AAP is up

```bash
export AAP_URL='https://aap-aap.apps.EXAMPLE/'   # gateway URL
curl -sk -u "admin:${AAP_PASSWORD}" \
  "${AAP_URL%/}/api/controller/v2/ping/"
```

Expect HTTP 200 and a controller `version`. Gateway root: `${AAP_URL%/}/api/` should list `controller`, `gateway`, etc.

**MCP is not enabled** if gateway `service_types` only show `gateway`, `controller`, `hub`, `eda` (no MCP) and there is no `*-mcp` OpenShift route.

---

## Step 1 — Access the cluster (OpenShift)

Console (workshop example):

`https://console-openshift-console.apps.<cluster>/`

CLI:

```bash
oc login https://api.<cluster>:6443 -u kubeadmin
# or: oc login --token=... --server=https://api.<cluster>:6443

oc whoami
oc get ansibleautomationplatform -A
oc get route -A | grep -i mcp || true
```

You must be on the **same** cluster that serves the AAP URL (hostname `apps.` prefix must match).

---

## Step 2 — Deploy / enable the MCP server

### Option A — OpenShift operator (recommended for this environment)

1. Find the AAP instance:

```bash
oc get ansibleautomationplatform -A
# note NAME and NAMESPACE (workshop: namespace aap, name aap)
```

2. Enable MCP on the platform CR (start read-only):

```bash
NS=aap
NAME=aap

oc -n "$NS" patch ansibleautomationplatform "$NAME" --type merge -p '
spec:
  mcp:
    disabled: false
    allow_write_operations: false
'
```

Or in Console: **Operators → Installed Operators → Ansible Automation Platform →** your instance → **YAML**, add under `spec:`:

```yaml
spec:
  mcp:
    disabled: false
    allow_write_operations: false
```

3. If `AnsibleMCPServer` does **not** appear within a few minutes, create it directly (AAP 2.6 Lightspeed/MCP operator reconciles this CR). Use the **AAP gateway** URL as `public_base_url`:

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
  # Optional if MCP→AAP TLS fails with self-signed/custom CA:
  # extra_settings:
  #   - setting: IGNORE_CERTIFICATE_ERRORS
  #     value: true
EOF
```

The Lightspeed operator (`ansible-lightspeed-operator-controller-manager`) runs the `mcpserver` role and creates Deployment, Service, and Route.

4. Confirm MCP workloads:

```bash
oc -n "$NS" get ansiblemcpserver
oc -n "$NS" rollout status deploy/aap-mcp --timeout=180s
oc -n "$NS" get deploy,pods,route | grep -i mcp
```

5. If you **change** `allow_write_operations` after MCP already exists, delete the `AnsibleMCPServer` CR and recreate it (required by Red Hat docs).

### Option B — Containerized AAP (RHEL)

Add to installer inventory and re-run install/upgrade:

```ini
[ansiblemcp]
aap.example.com

[all:vars]
mcp_allow_write_operations=false
mcp_ignore_certificate_errors=false
```

Confirm: `podman ps` shows `ansiblemcp`. Base URL: `https://<host>:8448`.

### Optional TLS / self-signed

Prefer mounting a CA (`bundle_cacert_secret` on `AnsibleMCPServer`) over disabling verification. Last resort:

```yaml
spec:
  mcp:
    extra_settings:
      - setting: IGNORE_CERTIFICATE_ERRORS
        value: true
```

---

## Step 3 — Record MCP base URL

| Install | How to get it |
|---------|----------------|
| OpenShift | `oc -n "$NS" get route aap-mcp -o jsonpath='https://{.spec.host}{"\n"}'` or Console → **Networking → Routes** → Location for `aap-mcp` |
| Containerized | `https://<aap-host>:8448` |

Export:

```bash
export MCP_BASE_URL='https://<mcp-host>'   # no trailing slash
# workshop example:
# export MCP_BASE_URL='https://aap-mcp-aap.apps.cluster-kw8lw-1.dyn.redhatworkshops.io'
```

### Toolset URLs

Both path styles work on current AAP MCP; pick one style and use it consistently:

```
# Style A (Red Hat client examples)
${MCP_BASE_URL}/job_management/mcp
${MCP_BASE_URL}/inventory_management/mcp
${MCP_BASE_URL}/system_monitoring/mcp
${MCP_BASE_URL}/user_management/mcp
${MCP_BASE_URL}/security_compliance/mcp
${MCP_BASE_URL}/platform_configuration/mcp

# Style B (MCP server root page)
${MCP_BASE_URL}/mcp/job_management
${MCP_BASE_URL}/mcp/inventory_management
...

# All tools
${MCP_BASE_URL}/mcp
```

Prefer **per-toolset** URLs for Gemini (smaller tool lists, clearer auth boundaries).

| Toolset | Gemini can… |
|---------|-------------|
| `job_management` | List/launch templates, jobs, logs, relaunch |
| `inventory_management` | Inventories, hosts, groups |
| `system_monitoring` | Health / activity style views |
| `user_management` | Users, teams, RBAC |
| `security_compliance` | Credential metadata / policies |
| `platform_configuration` | Settings, licenses, EEs |

---

## Step 4 — Create an AAP API token

### UI

1. Log into the **AAP gateway** URL as the integration user (admin for workshops; least-privilege user for production).
2. **Access Management → Users →** select user → **Tokens → Create token**.
3. Application: leave blank for a personal access token (or pick an OAuth app).
4. Scope: **Read** (safe) or **Write** (only if MCP write is enabled and you need launches).
5. Copy the token **once**. Export:

```bash
export AAP_MCP_TOKEN='paste-here'
```

### API (gateway)

```bash
curl -sk -u "admin:${AAP_PASSWORD}" \
  -H 'Content-Type: application/json' \
  -d '{"description":"gemini-mcp","scope":"write"}' \
  "${AAP_URL%/}/api/gateway/v1/tokens/"
```

Use the returned `token` value as `AAP_MCP_TOKEN`.

---

## Step 5 — Smoke-test MCP

```bash
# Expect non-HTML JSON/MCP response (auth may return 401 without init session;
# HTML SPA from the *gateway* host means you used the wrong host — use the MCP route)
curl -sk -o /tmp/mcp_probe.txt -w "%{http_code}\n" \
  -X POST "${MCP_BASE_URL}/job_management/mcp" \
  -H "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
head -c 400 /tmp/mcp_probe.txt; echo
```

Wrong host symptom: HTML with Monaco/SPA assets (that is the AAP UI gateway, not MCP).

---

## Step 6a — Connect Gemini CLI

Docs: [MCP servers with the Gemini CLI](https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html)

1. Install Gemini CLI and authenticate per Google’s docs.
2. Ensure `${MCP_BASE_URL}` is reachable from the machine running the CLI (trust private CA if needed).
3. Copy `configs/gemini-cli-settings.json` → `~/.gemini/settings.json` (or project `.gemini/settings.json`).
4. Replace `MCP_BASE_HOST` with the MCP host (and port if any). Keep `Authorization: Bearer ${AAP_MCP_TOKEN}`.
5. Export the token in your shell, then:

```bash
gemini mcp list
# or add one toolset:
gemini mcp add --transport http aap-job-mgmt \
  "${MCP_BASE_URL}/job_management/mcp" \
  --header "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -s user
```

**Naming:** keep server names short (≤ ~20 chars). Clients often cap `serverName + toolName` at 64 characters.

---

## Step 6b — Access and set up a Gemini Agent (Agent Platform)

This is the hosted-agent path (not only the CLI).

### Access / prerequisites

1. **Google Cloud project** with billing and permission to use Gemini Enterprise Agent Platform / Vertex AI APIs.
2. Enable the Agent Platform API for the project.
3. IAM for your user **and** the agent’s runtime service account as needed:
   - Ability to create/update agents
   - **`roles/mcp.toolUser`** if required for MCP tool invocation in your project
4. `gcloud auth login` and `gcloud auth application-default login` (or a CI service account).
5. **Network**: Agent Platform must reach `${MCP_BASE_URL}` over HTTPS. Workshop public OpenShift routes usually work; private AAP needs an approved ingress pattern (public route, reverse proxy, etc.). SSE-only MCP is **not** supported — AAP MCP must be **Streamable HTTP**.
6. AAP token available to inject as `Authorization: Bearer …` (prefer Secret Manager / deploy-time injection over hardcoding in git).

### Create an agent with AAP MCP tools

Template: `configs/gemini-agent-tools.json`.

Minimal REST create (replace placeholders):

```bash
export PROJECT_ID='your-gcp-project'
export LOCATION='global'
export MCP_BASE_URL='https://YOUR-MCP-ROUTE'
export AAP_MCP_TOKEN='...'

curl -X POST \
  "https://aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${LOCATION}/agents" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -d "{
    \"id\": \"aap-ops-agent\",
    \"base_agent\": \"antigravity-preview-05-2026\",
    \"description\": \"Operates Ansible Automation Platform via MCP\",
    \"tools\": [
      {
        \"type\": \"mcp_server\",
        \"name\": \"aap-job-mgmt\",
        \"url\": \"${MCP_BASE_URL}/job_management/mcp\",
        \"headers\": {
          \"Authorization\": \"Bearer ${AAP_MCP_TOKEN}\"
        }
      },
      {
        \"type\": \"mcp_server\",
        \"name\": \"aap-inv-mgmt\",
        \"url\": \"${MCP_BASE_URL}/inventory_management/mcp\",
        \"headers\": {
          \"Authorization\": \"Bearer ${AAP_MCP_TOKEN}\"
        }
      }
    ]
  }"
```

Python / Node SDK examples: Google’s [Create and manage agents](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/create-manage) (section “Create an agent with MCP configs”).

### Agent setup tips

- Start with **two** toolsets (`job_management`, `inventory_management`); add more after verification.
- Rotate `AAP_MCP_TOKEN` by updating the agent `tools[].headers` (PATCH agent) — do not leave workshop admin tokens in long-lived agents.
- If tools never appear: confirm Streamable HTTP, URL path ends with `/mcp`, Bearer token valid, and Agent Platform can resolve DNS to the OpenShift route.
- Optional: attach project skills under `base_environment.sources` if you also ship Cursor/agent skills for AAP runbooks.

### After create

- Deploy/runtime-enable the agent per your Agent Platform workflow ([Deploy an agent](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/runtime/deploy-an-agent)).
- Open a conversation and run the verification prompts below.

---

## Step 7 — Verify

Ask Gemini (CLI or Agent):

1. `What MCP tools are available for my Ansible Automation Platform?`
2. `List my Ansible Automation Platform job templates.`
3. `Show inventories and host counts.`

With write mode + Write token (careful):

4. `Launch job template <name> and report status.`

---

## Security and data handling

- Default MCP to **read-only** until needed.
- AAP **masks** credential secrets in API/MCP responses; it does **not** mask inventory vars, extra vars, or job logs — those may go to the LLM provider.
- Never commit `.env`, tokens, AWS keys, or kubeadmin passwords.
- Prefer a dedicated AAP service account with org/inventory limits over using `admin`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| MCP URLs return AAP UI HTML | Using gateway host, not MCP route | Copy `*-mcp` route Location |
| No `AnsibleMCPServer` / no mcp route | Platform CR not reconciled yet | Patch `spec.mcp`; if still missing, `oc apply` `AnsibleMCPServer` (see Step 2) |
| `SELF_SIGNED_CERT_IN_CHAIN` | Custom OpenShift ingress CA | `bundle_cacert_secret` on MCP CR |
| Write tools fail | Server still read-only | Set `allow_write_operations: true` and recreate MCP CR |
| Gemini Agent cannot reach MCP | Private network / firewall | Expose HTTPS route or connect via approved path |
| 401/403 from MCP | Bad/expired token or RBAC | Recreate token; check user permissions |
| HTTP 406 on stdout | Non-JSON accept | Ask agent to request JSON output |

---

## Workshop / AWS environment notes

Typical Red Hat workshop shape (`cluster-kw8lw-1` example):

| Item | Value pattern |
|------|----------------|
| AAP gateway | `https://aap-aap.apps.cluster-kw8lw-1.dyn.redhatworkshops.io` |
| OpenShift console | `https://console-openshift-console.apps.cluster-kw8lw-1.dyn.redhatworkshops.io` |
| OpenShift API | `https://api.cluster-kw8lw-1.dyn.redhatworkshops.io:6443` |
| MCP route | `https://aap-mcp-aap.apps.cluster-kw8lw-1.dyn.redhatworkshops.io` |

Verified deploy path on this workshop:

1. `oc login` with kubeadmin/token to the AAP cluster  
2. Patch `AnsibleAutomationPlatform` `spec.mcp`  
3. If needed, `oc apply` `AnsibleMCPServer` named `aap-mcp` with `public_base_url` = gateway URL  
4. Wait for `deploy/aap-mcp` Ready and route `aap-mcp`  
5. Smoke-test `POST …/job_management/mcp` initialize → 200 SSE/JSON-RPC  
6. Configure Gemini with `MCP_BASE_URL` + `AAP_MCP_TOKEN`

AWS credentials in AAP are for **playbook provisioning** (Amazon credential type), not for talking to MCP. MCP auth is always the **AAP Bearer token**.

---

## Related files in this repo

| Path | Purpose |
|------|---------|
| `.cursor/skills/aap-gemini-mcp/` | Cursor skill that follows this runbook |
| `configs/gemini-cli-settings.json` | Gemini CLI `mcpServers` template |
| `configs/gemini-agent-tools.json` | Agent Platform `tools[]` template |
| `configs/cursor-mcp.json` | Cursor/Claude-style `mcp.json` |
| `configs/.env.example` | Env var names (no secrets) |
