# Ansible Automation Platform MCP + Gemini

Deploy the AAP Model Context Protocol (MCP) server and connect **Google Gemini** (CLI or Agent Platform) so agents can query AAP and optionally run automation.

## Quick start

1. Open this repo in Cursor and invoke the skill **aap-gemini-mcp** (or ask to deploy AAP MCP / connect Gemini to AAP).
2. Deploy MCP on AAP (containerized or OpenShift) — see skill references.
3. Create an AAP API token; export `AAP_MCP_TOKEN`.
4. Copy a template from `configs/`, replace `MCP_BASE_HOST` and the token placeholder.
5. Verify with: `What MCP tools are available for my Ansible Automation Platform?`

## Repo layout

```
.cursor/skills/aap-gemini-mcp/   # Cursor Agent skill (deploy + Gemini connect)
configs/
  gemini-cli-settings.json       # ~/.gemini/settings.json template
  gemini-agent-tools.json        # Gemini Agent Platform tools[] template
  cursor-mcp.json                # Cursor/Claude-style mcp.json (AAP docs format)
```

## MCP URL shape

```
https://<mcp-base>/<toolset>/mcp
```

Toolsets: `job_management`, `inventory_management`, `system_monitoring`, `user_management`, `security_compliance`, `platform_configuration`

| Install | Typical base |
|---------|----------------|
| Containerized | `https://<aap-host>:8448` |
| OpenShift | MCP route Location (`*-mcp`) |

## Gemini notes

- **Gemini CLI** uses `httpUrl` + `headers.Authorization`.
- **Gemini Agent Platform** uses agent `tools` entries with `"type": "mcp_server"`.
- Prefer **read-only** MCP (`allow_write_operations: false`) until you intentionally enable launches/changes.
- Never commit real tokens.

## Official docs

- [Deploy AAP MCP](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server)
- [Gemini CLI MCP](https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html)
- [Gemini managed agents](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/create-manage)
