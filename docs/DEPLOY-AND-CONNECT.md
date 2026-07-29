# Deploy AAP MCP and connect Gemini

End-to-end runbook: enable the Ansible Automation Platform (AAP) MCP server, authenticate, then connect clients (Cursor / Gemini).

**Gemini-specific guide (CLI, Agent Platform, trusted TLS, browser sandbox):**  
→ **[CONNECT-GEMINI.md](CONNECT-GEMINI.md)**

Official AAP reference: [Deploy the MCP server on Ansible Automation Platform](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server)

**Platform deploy how-to:**

- OpenShift or existing Podman MCP: [DEPLOY-MCP.md](DEPLOY-MCP.md)
- Greenfield RHEL containerized AAP + MCP: [DEPLOY-AAP-CONTAINERIZED.md](DEPLOY-AAP-CONTAINERIZED.md)

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

### B. Platform host (pick one)

| Path | Need |
|------|------|
| **OpenShift** | `oc`/console on the **same** cluster as AAP; edit `AnsibleAutomationPlatform` / read MCP route |
| **Podman on RHEL** | RHEL 9/10 with AAP containerized installer; inventory access; firewall for **8448** |

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
          → AAP MCP server (OpenShift route OR host:8448 on Podman/RHEL)
            → AAP Controller / Gateway APIs (RBAC of token)
              → jobs, inventory, etc.
```

**Dual security**

1. **Server-level**: `allow_write_operations` (read-only vs read-write)
2. **User-level**: AAP token RBAC + token scope (Read vs Write)

Start **read-only** unless you intentionally want Gemini to launch jobs.

---

## Progress checklist

```
- [ ] 0. Confirm AAP is up (gateway + controller API)
- [ ] 1. Choose deploy path: OpenShift OR Podman on RHEL (see deploy docs)
- [ ] 2. Enable MCP
- [ ] 3. Wait for MCP; record MCP_BASE_URL (route or :8448)
- [ ] 4. Create dedicated MCP user + AAP_MCP_TOKEN
- [ ] 5. Smoke-test MCP HTTPS endpoint
- [ ] 5b. (Gemini/GCP) Ensure publicly trusted TLS; prefer :443 — see CONNECT-GEMINI.md
- [ ] 6a. Configure Gemini CLI  and/or
- [ ] 6b. Create Gemini Agent Platform agent  and/or
- [ ] 6c. Configure Cursor ~/.cursor/mcp.json  and/or
- [ ] 6d. Deploy browser chat sandbox (sandbox/)
- [ ] 7. Verify with sample prompts / list tools
```

---

## Step 0 — Confirm AAP is up

```bash
export AAP_URL='https://aap-aap.apps.EXAMPLE/'   # gateway URL
curl -sk -u "admin:${AAP_PASSWORD}" \
  "${AAP_URL%/}/api/controller/v2/ping/"
```

Expect HTTP 200 and a controller `version`. Gateway root: `${AAP_URL%/}/api/` should list `controller`, `gateway`, etc.

**MCP is not enabled** if gateway `service_types` only show `gateway`, `controller`, `hub`, `eda` (no MCP), and there is no `*-mcp` OpenShift route **or** no MCP listener on `:8448` (Podman/RHEL).

---

## Step 1 — Access the platform host

### OpenShift

Console: `https://console-openshift-console.apps.<cluster>/`

```bash
oc login https://api.<cluster>:6443 -u kubeadmin
# or: oc login --token=... --server=https://api.<cluster>:6443

oc whoami
oc get ansibleautomationplatform -A
oc get route -A | grep -i mcp || true
```

You must be on the **same** cluster that serves the AAP URL.

### Podman on RHEL

SSH to the AAP host. Confirm Podman and the containerized installer inventory are available:

```bash
podman ps
ls /path/to/aap-installer/inventory   # path varies by install
```

---

## Step 2 — Deploy / enable the MCP server

Full procedures: [DEPLOY-MCP.md](DEPLOY-MCP.md) (OpenShift **or** Podman on RHEL). Summaries below.

### OpenShift (summary)

1. Find the AAP instance: `oc get ansibleautomationplatform -A`
2. Enable MCP (read-only first):

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

3. If `AnsibleMCPServer` does not appear, apply it with `public_base_url` = AAP gateway URL (see [DEPLOY-MCP.md](DEPLOY-MCP.md)).
4. Confirm: `oc -n "$NS" rollout status deploy/aap-mcp --timeout=180s`
5. Changing write mode after deploy: delete/recreate `AnsibleMCPServer`.

Prefer a CA bundle (`bundle_cacert_secret`) over `IGNORE_CERTIFICATE_ERRORS`.

### Podman on RHEL (summary)

1. Add to installer inventory:

```ini
[ansiblemcp]
aap.example.com

[all:vars]
mcp_allow_write_operations=false
mcp_ignore_certificate_errors=false
mcp_tls_cert=/path/to/tls.crt
mcp_tls_key=/path/to/tls.key
```

2. Re-run `./setup.sh` (or your bundle’s install/upgrade command).
3. Confirm: `podman ps | grep -i mcp` → base URL `https://<host>:8448`.
4. Open **8448/tcp** from Gemini clients. Changing write mode: set `mcp_allow_write_operations=true` and re-run the installer.

---

## Step 3 — Record MCP base URL

| Install | How to get it |
|---------|----------------|
| OpenShift | `oc -n "$NS" get route aap-mcp -o jsonpath='https://{.spec.host}{"\n"}'` or Console → **Networking → Routes** → Location for `aap-mcp` |
| Podman on RHEL | `https://<aap-host>:8448` (after `podman ps` shows the MCP container) |

Export:

```bash
export MCP_BASE_URL='https://<mcp-host>'          # OpenShift route, no trailing slash
# or:
export MCP_BASE_URL='https://aap.example.com:8448' # Podman on RHEL
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

## Step 4 — Create a dedicated MCP user and API token

Prefer a **dedicated service account** (not shared `admin`) so you can rotate tokens and limit blast radius.

### 4a. Create user (UI)

1. Log into the AAP **gateway** as platform admin.
2. **Access Management → Users → Create user**.
3. Set username (e.g. `mcp-service`), password, and grant **Superuser** (or least-privilege org/inventory roles for production).
4. Optionally assign **Organization Admin** on the Default (or target) organization.

### 4b. Create user (gateway API)

```bash
export AAP_URL='https://aap.example.com'
export AAP_PASSWORD='…'          # platform admin
export MCP_USER='mcp-service'
export MCP_USER_PASSWORD='…'      # strong password

curl -sk -u "admin:${AAP_PASSWORD}" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"${MCP_USER}\",\"password\":\"${MCP_USER_PASSWORD}\",\"email\":\"mcp-service@example.com\",\"is_superuser\":true}" \
  "${AAP_URL%/}/api/gateway/v1/users/"
```

Assign **Organization Admin** (role definition id varies by install — list with `/api/gateway/v1/role_definitions/?search=Organization`):

```bash
# Example: role_definition id for "Organization Admin", object_id = Default org id
curl -sk -u "admin:${AAP_PASSWORD}" \
  -H 'Content-Type: application/json' \
  -d '{"user":<USER_ID>,"role_definition":<ORG_ADMIN_ROLE_ID>,"object_id":1}' \
  "${AAP_URL%/}/api/gateway/v1/role_user_assignments/"
```

### 4c. Create API token (UI)

1. Log in as the MCP user (or admin creating a token for that user, if your UI allows).
2. **Access Management → Users →** select user → **Tokens → Create token**.
3. Scope: **Read** (safe) or **Write** (only if MCP write is enabled and you need launches).
4. Copy the token **once**. Export:

```bash
export AAP_MCP_TOKEN='paste-here'
```

### 4d. Create API token (gateway API as the MCP user)

```bash
curl -sk -u "${MCP_USER}:${MCP_USER_PASSWORD}" \
  -H 'Content-Type: application/json' \
  -d '{"description":"cursor-gemini-mcp","scope":"write"}' \
  "${AAP_URL%/}/api/gateway/v1/tokens/"
```

Use the returned `token` value as `AAP_MCP_TOKEN`. Never commit it.

---

## Step 5 — Smoke-test MCP

```bash
# Expect non-HTML JSON/MCP response
# HTML SPA from the *gateway* host means wrong host — use MCP route or :8448
curl -sk -o /tmp/mcp_probe.txt -w "%{http_code}\n" \
  -X POST "${MCP_BASE_URL}/job_management/mcp" \
  -H "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
head -c 400 /tmp/mcp_probe.txt; echo
```

Wrong host symptom: HTML with Monaco/SPA assets (AAP UI gateway, not MCP).

To list tools over HTTP you typically need the `Mcp-Session-Id` from the initialize response headers, then `tools/list` on the same session.

---

## Step 6a / 6b / 6d — Connect Gemini (CLI, Agent Platform, chat sandbox)

Full Gemini runbook (trusted TLS, Vertex auth, Agent Registry, Cloud Run sandbox, troubleshooting):

→ **[CONNECT-GEMINI.md](CONNECT-GEMINI.md)**

Short version:

1. Ensure MCP HTTPS is **publicly trusted** (Let’s Encrypt / org CA Google trusts). Prefer **:443** for Agent Platform.
2. **CLI:** copy `configs/gemini-cli-settings.json`, set `httpUrl` + `Bearer ${AAP_MCP_TOKEN}`, run `gemini mcp list` / verification prompts.
3. **Agent Platform:** create agent from `configs/gemini-agent-tools.json` (includes `base_environment.network.allowlist: ["*"]` and `system_instruction`), grant `roles/mcp.toolUser`, register MCP URLs in Agent Registry, interact via Interactions API.
4. **Browser sandbox:** deploy `sandbox/` to Cloud Run with `MCP_BASE_URL`, `AAP_MCP_TOKEN`, and `SANDBOX_PASSWORD`.

---

## Step 6c — Connect Cursor (this IDE)

Template: `configs/cursor-mcp.json`.

1. Merge AAP entries into `~/.cursor/mcp.json` (preserve any existing servers).
2. Replace `MCP_BASE_HOST` with your MCP host **including port** when using Podman (`aap.example.com:8448`). On OpenShift use the MCP route host (no `:8448`).
3. Set `Authorization: Bearer <AAP_MCP_TOKEN>` (literal token or env expansion if your Cursor build supports it).
4. Reload MCP servers in Cursor (Settings → MCP, or restart the agent).
5. Confirm tools appear under each `aap-*` server (job templates, inventories, etc.).

Example fragment:

```json
{
  "mcpServers": {
    "aap-job-mgmt": {
      "url": "https://aap.example.com:8448/job_management/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_AAP_MCP_TOKEN"
      }
    },
    "aap-inv-mgmt": {
      "url": "https://aap.example.com:8448/inventory_management/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_AAP_MCP_TOKEN"
      }
    }
  }
}
```

Self-signed MCP TLS: trust the CA on the workstation, or use a public cert. If Cursor cannot connect, verify `curl -sk` works first, then fix trust.

---

## Step 7 — Verify

Ask Gemini (CLI or Agent) or use Cursor MCP tools:

1. `What MCP tools are available for my Ansible Automation Platform?`
2. `List my Ansible Automation Platform job templates.`
3. `Show inventories and host counts.`
4. `List projects and their playbooks.`

With write mode + Write token (careful):

4. `Launch job template <name> and report status.`

---

## Security and data handling

- Default MCP to **read-only** until needed.
- AAP **masks** credential secrets in API/MCP responses; it does **not** mask inventory vars, extra vars, or job logs — those may go to the LLM provider.
- Never commit `.env`, tokens, or kubeadmin passwords.
- Prefer a dedicated AAP service account with org/inventory limits over using `admin`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| MCP URLs return AAP UI HTML | Using gateway host, not MCP | OpenShift: `*-mcp` route; Podman: `https://host:8448` |
| No `AnsibleMCPServer` / no mcp route | Platform CR not reconciled yet | Patch `spec.mcp`; if still missing, `oc apply` `AnsibleMCPServer` (see [DEPLOY-MCP.md](DEPLOY-MCP.md)) |
| No MCP on Podman/RHEL | Inventory missing `[ansiblemcp]` / vars | Add inventory + re-run installer; check `podman ps` and **8448** |
| `SELF_SIGNED_CERT_IN_CHAIN` | Custom / self-signed TLS | OpenShift: `bundle_cacert_secret`; Podman: real `mcp_tls_*` certs |
| Write tools fail | Server still read-only | OpenShift: enable write + recreate MCP CR; Podman: inventory + reinstall |
| Gemini Agent cannot reach MCP | Private network / self-signed TLS / no egress | Public trusted HTTPS (prefer :443); set network allowlist `*`; see [CONNECT-GEMINI.md](CONNECT-GEMINI.md) |
| Agent only uses `list_dir` / `run_command` | MCP tools not attached | Trusted cert, allowlist, Agent Registry, `roles/mcp.toolUser` |
| 401/403 from MCP | Bad/expired token or RBAC | Recreate token; check user permissions |
| HTTP 406 on stdout | Non-JSON accept | Ask agent to request JSON output |

---

## Related files in this repo

| Path | Purpose |
|------|---------|
| [CONNECT-GEMINI.md](CONNECT-GEMINI.md) | Full Gemini AI connect guide |
| `.cursor/skills/aap-gemini-mcp/` | Cursor skill that follows this runbook |
| `configs/gemini-cli-settings.json` | Gemini CLI `mcpServers` template |
| `configs/gemini-agent-tools.json` | Agent Platform `tools[]` template |
| `configs/cursor-mcp.json` | Cursor/Claude-style `mcp.json` |
| `configs/.env.example` | Env var names (no secrets) |
| `sandbox/` | Browser chat UI (Gemini + AAP MCP) |
