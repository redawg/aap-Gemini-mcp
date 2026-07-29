# Ansible Automation Platform MCP + Gemini / Cursor

Deploy AAP’s Model Context Protocol (MCP) server and connect **Cursor**, **Gemini CLI**, **Gemini Agent Platform**, or the **browser chat sandbox**.

## Step-by-step guides

| Doc | Purpose |
|-----|---------|
| **[docs/DEPLOY-AAP-CONTAINERIZED.md](docs/DEPLOY-AAP-CONTAINERIZED.md)** | Install AAP on **RHEL + Podman** from scratch **including MCP** |
| **[docs/DEPLOY-MCP.md](docs/DEPLOY-MCP.md)** | Enable MCP on **OpenShift**, or add MCP to an existing containerized AAP |
| **[docs/DEPLOY-AND-CONNECT.md](docs/DEPLOY-AND-CONNECT.md)** | Dedicated MCP user, API token, Cursor wiring, smoke-tests |
| **[docs/CONNECT-GEMINI.md](docs/CONNECT-GEMINI.md)** | **Gemini AI end-to-end**: CLI, Agent Platform, trusted TLS, chat sandbox |

## Quick start

1. Open this repo in Cursor and invoke skill **aap-gemini-mcp**.
2. Deploy MCP:
   - No AAP yet → [DEPLOY-AAP-CONTAINERIZED.md](docs/DEPLOY-AAP-CONTAINERIZED.md)
   - AAP on OpenShift / existing Podman → [DEPLOY-MCP.md](docs/DEPLOY-MCP.md)
3. Create MCP user + token → [DEPLOY-AND-CONNECT.md](docs/DEPLOY-AND-CONNECT.md)
4. Connect Gemini → **[CONNECT-GEMINI.md](docs/CONNECT-GEMINI.md)** (CLI, Agent Platform, or Cloud Run chat UI)
5. Copy templates from `configs/`, replace placeholders (never commit secrets).
6. Verify: list job templates via MCP or ask Gemini the same.

## What you need (summary)

| System | Access |
|--------|--------|
| **AAP** | 2.6+ / 2.7+; admin (or ability to install) |
| **OpenShift** *or* **RHEL + Podman** | Operator path **or** containerized installer + registry credentials |
| **Cursor** | Edit `~/.cursor/mcp.json`; HTTPS to MCP |
| **Gemini CLI** | CLI + `~/.gemini/settings.json`; token in env |
| **Gemini Agent Platform** | GCP project, Agent API, `roles/mcp.toolUser`, **publicly trusted HTTPS** to MCP |
| **Chat sandbox** | GCP project + Cloud Run (optional browser UI in `sandbox/`) |

## Repo layout

```
docs/DEPLOY-AAP-CONTAINERIZED.md  # Greenfield RHEL/Podman AAP + MCP
docs/DEPLOY-MCP.md                # OpenShift MCP / brownfield Podman MCP
docs/DEPLOY-AND-CONNECT.md        # User, token, Cursor, smoke-test
docs/CONNECT-GEMINI.md            # Gemini CLI / Agent Platform / sandbox
sandbox/                          # Browser chat app (Gemini + AAP MCP)
.cursor/skills/aap-gemini-mcp/    # Cursor Agent skill
configs/
  gemini-cli-settings.json
  gemini-agent-tools.json
  cursor-mcp.json
  .env.example
```

## MCP URL shape

```
https://<mcp-base>/<toolset>/mcp
```

Toolsets: `job_management`, `inventory_management`, `system_monitoring`, `user_management`, `security_compliance`, `platform_configuration`

| Install | Typical base |
|---------|----------------|
| OpenShift | MCP route (`*-mcp`) — **not** the AAP gateway UI host |
| Podman on RHEL | `https://<aap-fqdn>:8448` |
| Gemini / GCP runtimes | Prefer a **public CA** on the MCP hostname; **:443** via LB/proxy when possible |

## Client notes

- **Cursor** / **Gemini CLI**: HTTP MCP + `Authorization: Bearer <token>`.
- **Gemini Agent Platform**: `"type": "mcp_server"`, Streamable HTTP only, sandbox `network.allowlist: ["*"]`.
- **Chat sandbox**: password login → Vertex Gemini → MCP tool calls (`sandbox/`).
- Prefer **read-only** MCP until you intentionally enable write operations.
- Never commit tokens, registry passwords, or kubeadmin credentials.

## Official docs

- [Deploy AAP MCP](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server)
- [Containerized installation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/containerized_installation/index)
- [Gemini CLI MCP](https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html)
- [Gemini managed agents](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/create-manage)
