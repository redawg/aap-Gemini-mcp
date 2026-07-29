# Connect Gemini to AAP MCP

AAP MCP is a **remote HTTP** MCP server. Gemini must use Streamable HTTP (not stdio) and send `Authorization: Bearer <AAP_TOKEN>`.

## Choose Gemini surface

| Surface | Config location | Best for |
|---------|-----------------|----------|
| **Gemini CLI** | `~/.gemini/settings.json` or `.gemini/settings.json` | Interactive ops from a laptop/CI with network to AAP |
| **Gemini Agent Platform** | Managed agent `tools[]` with `type: mcp_server` | Hosted agents calling AAP as tools |

Repo templates: `configs/gemini-cli-settings.json`, `configs/gemini-agent-tools.json`.

---

## Gemini CLI

Docs: [MCP servers with the Gemini CLI](https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html)

### 1. Export token

```bash
export AAP_MCP_TOKEN='paste-token-here'
```

### 2a. Edit settings.json

Use `httpUrl` + `headers` (Gemini CLI naming — not Cursor's `type`/`url`):

```json
{
  "mcpServers": {
    "aap-job-mgmt": {
      "httpUrl": "https://MCP_BASE/job_management/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      },
      "timeout": 30000
    },
    "aap-inv-mgmt": {
      "httpUrl": "https://MCP_BASE/inventory_management/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      }
    },
    "aap-sys-mon": {
      "httpUrl": "https://MCP_BASE/system_monitoring/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      }
    },
    "aap-user-mgmt": {
      "httpUrl": "https://MCP_BASE/user_management/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      }
    },
    "aap-security": {
      "httpUrl": "https://MCP_BASE/security_compliance/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      }
    },
    "aap-plat-cfg": {
      "httpUrl": "https://MCP_BASE/platform_configuration/mcp",
      "headers": {
        "Authorization": "Bearer ${AAP_MCP_TOKEN}"
      }
    }
  }
}
```

Replace `MCP_BASE` with e.g. `aap.example.com:8448` or the OpenShift MCP route host (no trailing slash issues — keep exact path `/.../mcp`).

### 2b. Or use CLI commands

```bash
gemini mcp add --transport http aap-job-mgmt \
  "https://MCP_BASE/job_management/mcp" \
  --header "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -s user
```

Repeat per toolset. Use `-s project` for `.gemini/settings.json` in the repo.

### 3. Verify

```bash
gemini mcp list
```

In chat:

- `What MCP tools are available for my Ansible Automation Platform?`
- `List my Ansible Automation Platform job templates.`
- `Show hosts in inventory <name>.`

### Naming

Keep MCP server names short (≤ ~20 characters). Gemini combines server name + tool name; many clients cap the combined id at 64 characters.

### TLS

If AAP uses a private CA, install the CA in the OS trust store used by Node/Gemini CLI. Avoid disabling TLS verification unless required for a short debug session.

---

## Gemini Enterprise Agent Platform

Docs: [Create and manage agents](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/create-manage)

### Requirements

1. Remote MCP must implement **Streamable HTTP** (JSON-RPC `tools/list` / `tools/call` over HTTP POST).
2. Agent runtime must resolve and reach the AAP MCP URL.
3. Prefer storing the AAP token in a secret manager and injecting into agent headers at deploy time — do not hardcode long-lived tokens in source control.

### Agent tools snippet

```json
{
  "id": "aap-ops-agent",
  "base_agent": "antigravity-preview-05-2026",
  "description": "Operates Ansible Automation Platform via MCP",
  "tools": [
    {
      "type": "mcp_server",
      "name": "aap-job-mgmt",
      "url": "https://MCP_BASE/job_management/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_AAP_TOKEN"
      }
    },
    {
      "type": "mcp_server",
      "name": "aap-inv-mgmt",
      "url": "https://MCP_BASE/inventory_management/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_AAP_TOKEN"
      }
    }
  ]
}
```

Create/update via the Managed Agents API (REST/Python/Node as in Google Cloud docs). Grant MCP-related IAM only as needed for Google-hosted MCPs; for AAP, auth is the Bearer token in headers.

### Connectivity patterns

| Situation | Approach |
|-----------|----------|
| AAP MCP publicly reachable with valid TLS | Point agent `url` at MCP HTTPS endpoints |
| AAP private only | Expose via approved ingress / Private Service Connect / reverse proxy reachable from Agent Platform |
| Token rotation | Update agent tools headers or secret reference; re-deploy agent |

### Verify

After agent create/update, run a conversation that asks for AAP job templates or inventories. Confirm tool invocations appear in agent traces/logs.

---

## Cursor / Claude-style mcp.json (for comparison)

AAP docs often show Cursor-style config (`type` + `url`). Gemini CLI uses `httpUrl` instead. Map as:

| Cursor / AAP docs | Gemini CLI |
|-------------------|------------|
| `"type": "http"` | omit (implied by `httpUrl`) |
| `"url": "..."` | `"httpUrl": "..."` |
| `"headers": { "Authorization": "Bearer ..." }` | same |

---

## Minimal connect order

1. MCP base URL from admin
2. `AAP_MCP_TOKEN` from AAP user Tokens page
3. Enable only needed toolsets (start with `job_management` + `inventory_management`)
4. Configure Gemini CLI **or** Agent Platform tools
5. Run verification prompts
