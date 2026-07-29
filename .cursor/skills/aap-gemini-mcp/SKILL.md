---
name: aap-gemini-mcp
description: >-
  Deploys Ansible Automation Platform (AAP) with the MCP server (OpenShift or
  RHEL containerized/Podman) and connects Cursor, Gemini CLI, Gemini Agent
  Platform, or the browser chat sandbox. Use when the user asks to deploy AAP
  MCP, install AAP on RHEL with Podman, create an MCP service user/token, wire
  Cursor mcp.json or Gemini to AAP toolsets, deploy the Gemini chat sandbox, or
  list AAP projects/job templates via MCP.
---

# AAP MCP + Gemini / Cursor

## Canonical docs (follow these)

| Guide | When |
|-------|------|
| [docs/DEPLOY-AAP-CONTAINERIZED.md](../../../docs/DEPLOY-AAP-CONTAINERIZED.md) | **Greenfield** RHEL + Podman: install AAP + MCP from scratch |
| [docs/DEPLOY-MCP.md](../../../docs/DEPLOY-MCP.md) | Enable MCP on **existing** OpenShift AAP, or add MCP to existing containerized AAP |
| [docs/DEPLOY-AND-CONNECT.md](../../../docs/DEPLOY-AND-CONNECT.md) | Dedicated user, token, Cursor, smoke-test |
| [docs/CONNECT-GEMINI.md](../../../docs/CONNECT-GEMINI.md) | **Gemini AI**: CLI, Agent Platform, trusted TLS, Cloud Run chat sandbox |

Summarized below for the agent. Prefer placeholders (`aap.example.com`), never invent real routes or tokens.

## Access gate (ask if missing)

1. **AAP** 2.6+/2.7+ (or ability to install it) + admin credentials  
2. **OpenShift** `oc` **or** RHEL 9/10 host + containerized installer + registry credentials  
3. **Client**: Cursor and/or Gemini CLI and/or GCP Agent Platform and/or Cloud Run sandbox  
4. Network: client → MCP HTTPS (route or `:8448`; **public CA** for Gemini/GCP)

## Workflow checklist

```
Progress:
- [ ] 0. Platform ready (or install via DEPLOY-AAP-CONTAINERIZED)
- [ ] 1. Choose path: OpenShift OR Podman on RHEL
- [ ] 2. Enable / deploy MCP
- [ ] 3. Record MCP_BASE_URL
- [ ] 4. Create dedicated MCP user + AAP_MCP_TOKEN
- [ ] 5. Smoke-test initialize
- [ ] 5b. Trusted TLS for Gemini/GCP (CONNECT-GEMINI)
- [ ] 6. Cursor and/or Gemini CLI / Agent / sandbox
- [ ] 7. Verify tools / prompts
```

## Deploy — OpenShift (summary)

```yaml
spec:
  mcp:
    disabled: false
    allow_write_operations: false
```

If needed, apply `AnsibleMCPServer` with `public_base_url` = AAP gateway URL.  
`MCP_BASE_URL` = `https://$(oc -n aap get route aap-mcp -o jsonpath='{.spec.host}')`  
**Not** the gateway UI host.

## Deploy — Podman / RHEL (summary)

Greenfield: full inventory + `ansible-playbook -i inventory-growth ansible.containerized_installer.install`  
→ [DEPLOY-AAP-CONTAINERIZED.md](../../../docs/DEPLOY-AAP-CONTAINERIZED.md)

Critical inventory rules:

- Use an **FQDN** for hosts (not bare `localhost`) when Hub is colocated  
- **Do not** set `ansible_become=true` in `[all:vars]` (breaks non-root preflight)  
- Include `[ansiblemcp]` + `mcp_tls_*` / `mcp_allow_write_operations`  
- AAP 2.7+: `automationmetrics_skip_install=true` **or** configure `[automationmetrics]`  

```bash
export MCP_BASE_URL='https://aap.example.com:8448'
podman ps | grep -i mcp
```

## Dedicated user + token

Create a service user (`is_superuser` and/or org roles), then:

```bash
curl -sk -u "${MCP_USER}:${MCP_USER_PASSWORD}" \
  -H 'Content-Type: application/json' \
  -d '{"description":"mcp-client","scope":"write"}' \
  "${AAP_URL%/}/api/gateway/v1/tokens/"
```

`export AAP_MCP_TOKEN=…` — never commit.

## Connect Cursor

Merge `configs/cursor-mcp.json` into `~/.cursor/mcp.json`, set real MCP host + Bearer token, reload MCP. Keep server names short (`aap-job-mgmt`, …).

## Connect Gemini

**Follow [CONNECT-GEMINI.md](../../../docs/CONNECT-GEMINI.md).**

Templates: `configs/gemini-cli-settings.json`, `configs/gemini-agent-tools.json`.  
Browser UI: deploy `sandbox/` to Cloud Run.

```bash
gemini mcp add --transport http aap-job-mgmt \
  "${MCP_BASE_URL}/job_management/mcp" \
  --header "Authorization: Bearer ${AAP_MCP_TOKEN}"
```

Agent Platform must use publicly trusted HTTPS, `"type": "mcp_server"`, plus built-in  
`google_search` / `url_context` / `code_execution` / `filesystem`, and  
`base_environment.network.allowlist: [{ "domain": "*" }]`.

## Verify

1. Initialize MCP → HTTP 200 / `serverInfo` (prefer without `-k` for Gemini)  
2. List tools (job templates, inventories, projects)  
3. Prompt: `List my Ansible Automation Platform job templates.`

## Security

1. Default MCP **read-only** (`allow_write_operations` / `mcp_allow_write_operations` false)  
2. Least-privilege token; dedicated user  
3. No secrets in git  
4. Job logs / inventory vars may reach the LLM; credential secrets are masked by AAP  

## Agent behavior

1. Point users at the docs table above; stay generic (no workshop-specific hostnames).  
2. If access is missing, list exact gaps — do not invent URLs/tokens.  
3. After deploy, fill configs from real `MCP_BASE_URL` / token.  
4. For Gemini/GCP, insist on trusted TLS and document CLI + sandbox as proven chat paths.  
5. On write-mode change: OpenShift recreate `AnsibleMCPServer`; Podman re-run installer.  

## Additional resources

- [reference-deploy.md](reference-deploy.md)  
- [reference-gemini.md](reference-gemini.md)  
- [examples.md](examples.md)  
- [Official AAP MCP](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server)  
- [Gemini CLI MCP](https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html)  
