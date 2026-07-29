# Ansible Automation Platform MCP + Gemini / Cursor

Deploy AAP’s Model Context Protocol (MCP) server and connect **Cursor**, **Gemini CLI**, **Gemini Agent Platform**, or the **browser chat sandbox**.

## Step-by-step guides

| Doc | Purpose |
|-----|---------|
| **[docs/DEPLOY-GCP-FROM-SCRATCH.md](docs/DEPLOY-GCP-FROM-SCRATCH.md)** | **Blank GCP** → VM → AAP+MCP → APD → TLS → Gemini chat (GCP access list, Red Hat Demo Google Open Environment, starter questions) |
| **[docs/DEPLOY-AAP-CONTAINERIZED.md](docs/DEPLOY-AAP-CONTAINERIZED.md)** | Install AAP on **RHEL + Podman** from scratch **including MCP** |
| **[docs/INSTALL-APD.md](docs/INSTALL-APD.md)** | Seed **Ansible Product Demos** via [`install-apd.yml`](https://github.com/ansible/product-demos/blob/main/install-apd.yml) |
| **[docs/DEPLOY-MCP.md](docs/DEPLOY-MCP.md)** | Enable MCP on **OpenShift**, or add MCP to an existing containerized AAP |
| **[docs/DEPLOY-AND-CONNECT.md](docs/DEPLOY-AND-CONNECT.md)** | Dedicated MCP user, API token, Cursor wiring, smoke-tests |
| **[docs/CONNECT-GEMINI.md](docs/CONNECT-GEMINI.md)** | **Gemini AI**: CLI, Agent Platform, trusted TLS, chat sandbox |

## Quick start

1. Open this repo in Cursor and invoke skill **aap-gemini-mcp**.
2. Deploy:
   - **Blank GCP** → [DEPLOY-GCP-FROM-SCRATCH.md](docs/DEPLOY-GCP-FROM-SCRATCH.md)
   - No AAP yet (any cloud) → [DEPLOY-AAP-CONTAINERIZED.md](docs/DEPLOY-AAP-CONTAINERIZED.md)
   - AAP on OpenShift / existing Podman → [DEPLOY-MCP.md](docs/DEPLOY-MCP.md)
3. Install Ansible Product Demos → **[INSTALL-APD.md](docs/INSTALL-APD.md)** (recommended)
4. Create MCP user + token → [DEPLOY-AND-CONNECT.md](docs/DEPLOY-AND-CONNECT.md)
5. Connect Gemini → **[CONNECT-GEMINI.md](docs/CONNECT-GEMINI.md)** (prefer Cloud Run chat sandbox first)
6. Copy templates from `configs/`, replace placeholders (never commit secrets).
7. Ask starter questions from [DEPLOY-GCP-FROM-SCRATCH.md § Step 10](docs/DEPLOY-GCP-FROM-SCRATCH.md).

## What you need (summary)

| System | Access |
|--------|--------|
| **Blank GCP** | Billing, `gcloud`, DNS name, RH registry + AAP installer tarball |
| **AAP** | 2.6+ / 2.7+; admin (or ability to install) |
| **OpenShift** *or* **RHEL + Podman** | Operator path **or** containerized installer + registry credentials |
| **Cursor** | Edit `~/.cursor/mcp.json`; HTTPS to MCP |
| **Gemini CLI** | CLI + `~/.gemini/settings.json`; token in env |
| **Gemini Agent Platform** | GCP project, Agent API, `roles/mcp.toolUser`, **publicly trusted HTTPS** to MCP |
| **Chat sandbox** | GCP project + Cloud Run (`sandbox/`) |

## Repo layout

```
docs/DEPLOY-GCP-FROM-SCRATCH.md   # Blank GCP → full stack + chatbot questions
docs/DEPLOY-AAP-CONTAINERIZED.md  # Greenfield RHEL/Podman AAP + MCP
docs/INSTALL-APD.md               # Ansible Product Demos (install-apd.yml)
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

Prefer the **aggregate** endpoint (all tools):

```
https://<mcp-base>/mcp
```

Curated toolsets (optional):

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

- **Cursor** / **Gemini CLI**: HTTP MCP + `Authorization: Bearer <token>` → `/mcp`.
- **Gemini Agent Platform**: `"type": "mcp_server"`, Streamable HTTP only, sandbox `network.allowlist: ["*"]`.
- **Chat sandbox**: password login → Vertex Gemini → MCP tool calls (`sandbox/`).
- Prefer **read-only** MCP until you intentionally enable write operations.
- Never commit tokens, registry passwords, or service-account keys.

## Official docs

- [Deploy AAP MCP](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server)
- [Containerized installation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/containerized_installation/index)
- [Gemini CLI MCP](https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html)
- [Gemini managed agents](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/create-manage)
