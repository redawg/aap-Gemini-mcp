---
name: aap-gemini-mcp
description: >-
  Deploys Ansible Automation Platform (AAP) with the MCP server from a blank GCP
  project or existing AAP (OpenShift / RHEL Podman), then connects Cursor,
  Gemini CLI, Gemini Agent Platform, or the browser chat sandbox. On blank GCP,
  ask whether the user wants managed target hosts and if so create one RHEL 9
  and one RHEL 10 VM. Use when the user asks to build AAP MCP + Gemini from
  scratch on GCP, install AAP on RHEL with Podman, enable MCP, create an MCP
  token, deploy the Cloud Run chatbot, or list/create AAP resources via MCP.
---

# AAP MCP + Gemini / Cursor

## Canonical docs (follow these)

| Guide | When |
|-------|------|
| **[docs/DEPLOY-GCP-FROM-SCRATCH.md](../../../docs/DEPLOY-GCP-FROM-SCRATCH.md)** | **Blank GCP project** → VM → AAP+MCP → TLS → chat (master checklist) |
| [docs/DEPLOY-AAP-CONTAINERIZED.md](../../../docs/DEPLOY-AAP-CONTAINERIZED.md) | RHEL + Podman: install AAP + MCP (any cloud/bare metal) |
| [docs/DEPLOY-MCP.md](../../../docs/DEPLOY-MCP.md) | Enable MCP on **existing** OpenShift AAP, or add MCP to existing containerized AAP |
| [docs/DEPLOY-AND-CONNECT.md](../../../docs/DEPLOY-AND-CONNECT.md) | Dedicated user, token, Cursor, smoke-test |
| [docs/CONNECT-GEMINI.md](../../../docs/CONNECT-GEMINI.md) | Gemini CLI / Agent Platform / Cloud Run sandbox deep dive |

Summarized below for the agent. Prefer placeholders (`aap.example.com`), never invent real routes or tokens.

## Access gate (ask if missing)

**Blank GCP path** — confirm:

1. **GCP access** (see [DEPLOY-GCP-FROM-SCRATCH § GCP access](../../../docs/DEPLOY-GCP-FROM-SCRATCH.md)): project + billing **or** Red Hat Demo Google Open Environment; IAM/roles; Vertex for chat  
2. If user is **Red Hat**: prefer provisioning **Demo Google Open Environment** first (do not require personal billing)  
3. Red Hat registry credentials + AAP containerized setup tarball  
4. A **public DNS name** you can point at the VM / LB  
5. Desired chat path: Cloud Run sandbox (recommended), Agent Platform, and/or CLI  
6. **Target hosts?** Ask: *Do you want managed target VMs (RHEL 9 + RHEL 10) for inventories/jobs?*  
   - **Yes** → create `rhel9-target` + `rhel10-target` (see DEPLOY-GCP-FROM-SCRATCH Step 1b)  
   - **No** → AAP server only  

**Existing AAP path** — confirm:

1. AAP 2.6+/2.7+ admin access  
2. OpenShift `oc` **or** RHEL host with installer inventory  
3. Client reachability to MCP HTTPS (**public CA** for Gemini/GCP)

## Workflow checklist

```
Progress:
- [ ] 0. Choose: blank GCP (DEPLOY-GCP-FROM-SCRATCH) OR existing AAP
- [ ] 1. Platform ready (VM + AAP+MCP, or enable MCP on existing)
- [ ] 1b. If blank GCP: asked about targets; if yes → RHEL 9 + RHEL 10 VMs
- [ ] 2. Record MCP_BASE_URL (prefer :443 + public CA for Gemini)
- [ ] 3. Create dedicated MCP user + AAP_MCP_TOKEN
- [ ] 4. Smoke-test POST ${MCP_BASE_URL}/mcp initialize
- [ ] 5. Write mode if create/launch demos needed
- [ ] 5b. If targets exist: add hosts to AAP inventory
- [ ] 6. Path C Cloud Run sandbox (first chat UI) and/or Path A/B
- [ ] 7. Give user starter chatbot questions (see below)
```

## Blank GCP (summary)

Follow **[DEPLOY-GCP-FROM-SCRATCH.md](../../../docs/DEPLOY-GCP-FROM-SCRATCH.md)** in order:

0. Enable Compute, DNS, Run, AI Platform, Agent Registry APIs  
1. Create RHEL 9 VM (~8 vCPU / 32 GB / 100 GB), firewall 22/443/8448  
1b. **Ask about target hosts**; if yes → create **RHEL 9 + RHEL 10** managed VMs (`rhel9-target`, `rhel10-target`)  
2. DNS A records for AAP (+ MCP hostname)  
3. Install AAP+MCP via containerized installer on the VM  
4. MCP user + gateway token  
5. Let’s Encrypt (or org CA) + prefer HTTPS LB on **:443** for MCP  
6. Optional write mode (`ALLOW_WRITE_OPERATIONS=true`); add targets to inventory if created  
7. Deploy `sandbox/` to Cloud Run with `MCP_TOOLSETS=mcp`  
8. Optional Agent Platform `aap-ops-agent` + registry `/mcp`  
9. Optional Gemini CLI  

Secrets only in `.local/` (gitignored).

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

Greenfield: [DEPLOY-AAP-CONTAINERIZED.md](../../../docs/DEPLOY-AAP-CONTAINERIZED.md)

Critical inventory rules:

- Use an **FQDN** for hosts (not bare `localhost`) when Hub is colocated  
- **Do not** set `ansible_become=true` in `[all:vars]` (breaks non-root preflight)  
- Include `[ansiblemcp]` + `mcp_tls_*` / `mcp_allow_write_operations`  
- Default lab admin password: **`R3dh2t!2026`** (gateway/controller/hub/eda)  
- AAP 2.7+: `automationmetrics_skip_install=true` **or** configure `[automationmetrics]`  

```bash
export MCP_BASE_URL='https://aap.example.com:8448'   # or https://mcp.example.com on :443
podman ps | grep -i mcp
```

Prefer aggregate endpoint for clients: `${MCP_BASE_URL}/mcp` (all tools).

## Dedicated user + token

```bash
curl -sk -u "${MCP_USER}:${MCP_USER_PASSWORD}" \
  -H 'Content-Type: application/json' \
  -d '{"description":"mcp-client","scope":"write"}' \
  "${AAP_URL%/}/api/gateway/v1/tokens/"
```

`export AAP_MCP_TOKEN=…` — never commit.

## Connect Cursor / Gemini

- Cursor: merge `configs/cursor-mcp.json` → `aap-mcp` → `/mcp`  
- Gemini: **[CONNECT-GEMINI.md](../../../docs/CONNECT-GEMINI.md)**  
- Templates: `configs/gemini-cli-settings.json`, `configs/gemini-agent-tools.json`  
- Browser UI: `sandbox/` → Cloud Run  

```bash
gemini mcp add --transport http aap-mcp \
  "${MCP_BASE_URL}/mcp" \
  --header "Authorization: Bearer ${AAP_MCP_TOKEN}"
```

Agent Platform: publicly trusted HTTPS, `"type": "mcp_server"`, builtins  
(`google_search`, `url_context`, `code_execution`, `filesystem`),  
`base_environment.network.allowlist: [{ "domain": "*" }]`, `roles/mcp.toolUser`.

## Starter chatbot questions (give these after Path C works)

**Read**

1. What AAP MCP tools do you have, and name five that can create or change something?  
2. List job templates by name.  
3. List inventories and host counts.  
4. List projects and organizations.  
5. List execution environments.  
6. Show recent jobs and their status.  

**Web + AAP**

7. Search the web for Ansible Automation Platform MCP, then compare that to your tools.  
8. Open https://docs.redhat.com and summarize deploying the AAP MCP server.  

**Write** (only if write mode + write token)

9. Create inventory group `chatbot-demo` in inventory id 1.  
10. Launch the Demo Job Template and report job id/status.  

**Capability check**

11. Can you create a new AAP project via MCP? If not, what project tools exist?  
    *(Expect: `projects_list` only — no `projects_create`.)*

Full list: [DEPLOY-GCP-FROM-SCRATCH.md § Step 10](../../../docs/DEPLOY-GCP-FROM-SCRATCH.md).

## Verify

1. `POST ${MCP_BASE_URL}/mcp` initialize → 200 / `serverInfo` (without `-k` for Gemini)  
2. Sandbox login + “List job templates by name.”  
3. Optional: Agent Platform Interactions / Gemini CLI same prompt  

## Security

1. Default MCP **read-only** until create/launch demos need write  
2. Least-privilege token; dedicated user  
3. No secrets in git  
4. Job logs / inventory vars may reach the LLM; credential secrets are masked by AAP  

## Agent behavior

1. **Blank GCP** → start at DEPLOY-GCP-FROM-SCRATCH; state required GCP access; Red Hat users → Demo Google Open Environment; **always ask about RHEL 9+10 target hosts** before finishing compute.  
2. Prefer **Path C (sandbox)** for the first successful chat demo; Path B Interactions can stall.  
3. If access is missing, list exact gaps — do not invent URLs/tokens.  
4. After deploy, fill configs from real `MCP_BASE_URL` / token; give starter questions.  
5. On write-mode change: recreate/restart MCP (Podman) or recreate `AnsibleMCPServer` (OpenShift).  
6. Stay generic in committed docs (no workshop-specific hostnames).  

## Additional resources

- [reference-deploy.md](reference-deploy.md)  
- [reference-gemini.md](reference-gemini.md)  
- [examples.md](examples.md)  
- [Official AAP MCP](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server)  
- [Gemini CLI MCP](https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html)  
