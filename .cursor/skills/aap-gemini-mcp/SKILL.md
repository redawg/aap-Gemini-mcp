---
name: aap-gemini-mcp
description: >-
  Deploys the Ansible Automation Platform (AAP) MCP server and connects Google
  Gemini (CLI or Agent Platform) to it. Use when the user asks to deploy AAP MCP,
  wire Gemini to Ansible Automation Platform, configure mcpServers for AAP
  toolsets, or connect Gemini Agent to job/inventory/security MCP endpoints.
---

# AAP MCP + Gemini

Guide the user end-to-end: deploy AAP MCP, create an API token, then connect Gemini.

## Prerequisites checklist

Confirm before deploying:

- [ ] AAP **2.6+** (2.7+ for GA MCP support)
- [ ] Admin access for deploy (container inventory **or** OpenShift operator)
- [ ] AAP user/service account for the token (RBAC = what Gemini can do)
- [ ] Gemini CLI installed **and/or** Gemini Enterprise Agent Platform access
- [ ] Network path from Gemini client → AAP MCP URL (HTTPS)

## Workflow

Copy and track:

```
Progress:
- [ ] 1. Choose deploy path (containerized vs OpenShift)
- [ ] 2. Deploy / enable MCP server
- [ ] 3. Record MCP base URL
- [ ] 4. Create AAP API token
- [ ] 5. Connect Gemini (CLI and/or Agent Platform)
- [ ] 6. Verify tools + sample prompt
```

### Step 1 — Choose deploy path

| Path | When |
|------|------|
| **Containerized** | AAP on RHEL via containerized installer |
| **OpenShift** | AAP via Ansible Automation Platform operator |

Details: [reference-deploy.md](reference-deploy.md)

### Step 2 — Deploy MCP

**Containerized** — add to installer inventory, then re-run install:

```ini
[ansiblemcp]
aap.example.com

[all:vars]
mcp_allow_write_operations=false
mcp_ignore_certificate_errors=false
```

- Start **read-only** (`mcp_allow_write_operations=false`) unless the user explicitly needs job launch / writes.
- MCP listens on **HTTPS port 8448**. Base URL: `https://<host>:8448`.

**OpenShift** — under AAP CR `spec`:

```yaml
spec:
  mcp:
    disabled: false
    allow_write_operations: false
```

- MCP route: Networking → Routes → `*-mcp` (copy Location).
- After changing write permissions post-deploy, delete/recreate the `AnsibleMCPServer` CR so the operator reconciles.

### Step 3 — MCP base URL

| Install | Base URL |
|---------|----------|
| Containerized | `https://<aap-host>:8448` |
| OpenShift | Route Location for `aap-mcp` (or `<aap-name>-mcp`) |

Toolset URLs:

```
{BASE}/{toolset}/mcp
```

Toolsets: `job_management`, `inventory_management`, `system_monitoring`, `user_management`, `security_compliance`, `platform_configuration`

### Step 4 — API token

In AAP UI: **Access Management → Users → (user) → Tokens → Create token**

- Scope: **Read** for read-only; **Write** only if MCP is read-write and user needs mutations
- Copy token immediately (shown once)
- Store as env var, e.g. `AAP_MCP_TOKEN` — never commit tokens

### Step 5 — Connect Gemini

Prefer configs under `configs/` in this repo. Full recipes: [reference-gemini.md](reference-gemini.md)

**Gemini CLI** — `~/.gemini/settings.json` or project `.gemini/settings.json`:

```json
{
  "mcpServers": {
    "aap-job-mgmt": {
      "httpUrl": "https://aap.example.com:8448/job_management/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      }
    },
    "aap-inv-mgmt": {
      "httpUrl": "https://aap.example.com:8448/inventory_management/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      }
    }
  }
}
```

Or:

```bash
export AAP_MCP_TOKEN='...'
gemini mcp add --transport http aap-job-mgmt \
  "https://aap.example.com:8448/job_management/mcp" \
  --header "Authorization: Bearer ${AAP_MCP_TOKEN}"
```

**Gemini Agent Platform** (managed agent) — remote Streamable HTTP MCP in agent `tools`:

```json
{
  "type": "mcp_server",
  "name": "aap-job-mgmt",
  "url": "https://aap.example.com:8448/job_management/mcp",
  "headers": {
    "Authorization": "Bearer YOUR_AAP_TOKEN"
  }
}
```

Requirements for Agent Platform:

- MCP must be **Streamable HTTP** (`tools/list` / `tools/call` over HTTP POST)
- Agent/runtime must reach the AAP MCP URL (public or private connectivity)
- Keep MCP server names **≤ ~20 chars** (combined server+tool name often capped at 64)

### Step 6 — Verify

1. `gemini mcp list` (CLI) or confirm agent tools list includes AAP MCP
2. Prompt: `What MCP tools are available for my Ansible Automation Platform?`
3. Prompt: `List my recent Ansible Automation Platform jobs.`

## Security rules (always enforce)

1. Default MCP to **read-only** unless user opts into write.
2. Token RBAC must be least privilege for the intended toolsets.
3. Never put tokens in git; use env vars or a secret store.
4. Warn: tool results (inventory, IPs, job logs) go to the LLM provider — secrets in AAP credential fields are masked; host vars / extra vars / job output are not.
5. Self-signed certs: prefer trust store / CA bundle over `IGNORE_CERTIFICATE_ERRORS`.

## Agent behavior

When invoked:

1. Ask which path: containerized vs OpenShift, Gemini CLI vs Agent Platform (or both).
2. Produce concrete inventory/CR edits and Gemini config from their hostnames.
3. Point them at `configs/gemini-cli-settings.json` and `configs/gemini-agent-tools.json` as starting templates.
4. Do not invent OpenShift routes or tokens — collect real values from the user.
5. After connect steps, give 2–3 verification prompts.

## Additional resources

- [reference-deploy.md](reference-deploy.md) — full deploy + troubleshooting
- [reference-gemini.md](reference-gemini.md) — Gemini CLI + Agent Platform details
- [examples.md](examples.md) — end-to-end examples
- Official AAP docs: https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server
- Gemini CLI MCP: https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html
- Gemini managed agents + MCP: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/create-manage
