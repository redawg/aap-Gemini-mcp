# Ansible Automation Platform MCP + Gemini

Deploy the AAP Model Context Protocol (MCP) server on **OpenShift** and connect **Google Gemini** (CLI or Agent Platform) so agents can query AAP and optionally run automation.

## Deploy MCP (OpenShift)

**[docs/DEPLOY-MCP-OPENSHIFT.md](docs/DEPLOY-MCP-OPENSHIFT.md)** — `oc` / AAP Operator + `AnsibleMCPServer`.

## Full runbook (MCP → Gemini)

**[docs/DEPLOY-AND-CONNECT.md](docs/DEPLOY-AND-CONNECT.md)** — complete steps:

1. What access you need (AAP, OpenShift, Gemini / Google Cloud)
2. Enable MCP on OpenShift
3. Create an AAP API token
4. Connect **Gemini CLI** and/or create a **Gemini Agent** with `mcp_server` tools
5. Verify and troubleshoot

## Quick start

1. Open this repo in Cursor and invoke skill **aap-gemini-mcp**.
2. Follow [docs/DEPLOY-MCP-OPENSHIFT.md](docs/DEPLOY-MCP-OPENSHIFT.md), then [docs/DEPLOY-AND-CONNECT.md](docs/DEPLOY-AND-CONNECT.md).
3. Export `AAP_MCP_TOKEN` and set `MCP_BASE_URL` from the OpenShift `*-mcp` route.
4. Copy a template from `configs/`, replace placeholders.
5. Verify: `What MCP tools are available for my Ansible Automation Platform?`

## What you need access to (summary)

| System | Access |
|--------|--------|
| **AAP** | Admin (or limited service user) on the gateway URL; AAP 2.6+ / 2.7+ |
| **OpenShift** | `oc` or console on the **same** cluster as AAP — edit `AnsibleAutomationPlatform` CR, read MCP route |
| **Gemini CLI** | CLI installed; HTTPS to MCP URL; `~/.gemini/settings.json` |
| **Gemini Agent Platform** | GCP project, Agent Platform API, create-agent IAM, `roles/mcp.toolUser` as required, network path to MCP HTTPS |

## Repo layout

```
docs/DEPLOY-MCP-OPENSHIFT.md     # OpenShift MCP deploy
docs/DEPLOY-AND-CONNECT.md       # Token + Gemini connect
.cursor/skills/aap-gemini-mcp/   # Cursor Agent skill
configs/
  gemini-cli-settings.json       # Gemini CLI mcpServers template
  gemini-agent-tools.json        # Gemini Agent Platform tools[] template
  cursor-mcp.json                # Cursor/Claude-style mcp.json
  .env.example                   # Env var names (no secrets)
```

## MCP URL shape

```
https://<mcp-base>/<toolset>/mcp
```

Toolsets: `job_management`, `inventory_management`, `system_monitoring`, `user_management`, `security_compliance`, `platform_configuration`

OpenShift base: MCP route Location (`*-mcp`) — **not** the AAP gateway UI host.

## Gemini notes

- **Gemini CLI** uses `httpUrl` + `headers.Authorization`.
- **Gemini Agent Platform** uses agent `tools` entries with `"type": "mcp_server"` (Streamable HTTP only).
- Prefer **read-only** MCP (`allow_write_operations: false`) until you intentionally enable launches/changes.
- Never commit real tokens or kubeadmin passwords (use gitignored `.env`).

## Official docs

- [Deploy AAP MCP](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server)
- [Gemini CLI MCP](https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html)
- [Gemini managed agents](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/create-manage)
