---
name: aap-gemini-mcp
description: >-
  Deploys Ansible Automation Platform (AAP) with the MCP server from a blank GCP
  project or existing AAP (OpenShift / RHEL Podman), then connects Cursor,
  Gemini CLI, Gemini Agent Platform, or the browser chat sandbox. Always ask for
  any missing GCP/AAP/DNS/registry inputs. On blank GCP, ask whether the user
  wants managed target hosts; if yes create RHEL 9 + RHEL 10 VMs and a GCP
  dynamic inventory in AAP. Use for from-scratch GCP deploys, Podman AAP+MCP,
  MCP tokens, Cloud Run chatbot, or AAP MCP tool use.
---

# AAP MCP + Gemini / Cursor

## Canonical docs (follow these)

| Guide | When |
|-------|------|
| **[docs/DEPLOY-GCP-FROM-SCRATCH.md](../../../docs/DEPLOY-GCP-FROM-SCRATCH.md)** | **Blank GCP** → access gate, targets, **GCP dynamic inventory**, TLS, chat |
| [docs/DEPLOY-AAP-CONTAINERIZED.md](../../../docs/DEPLOY-AAP-CONTAINERIZED.md) | RHEL + Podman: install AAP + MCP |
| [docs/DEPLOY-MCP.md](../../../docs/DEPLOY-MCP.md) | Enable MCP on existing OpenShift / brownfield Podman |
| [docs/DEPLOY-AND-CONNECT.md](../../../docs/DEPLOY-AND-CONNECT.md) | Dedicated user, token, Cursor, smoke-test |
| [docs/CONNECT-GEMINI.md](../../../docs/CONNECT-GEMINI.md) | Gemini CLI / Agent Platform / Cloud Run sandbox |

Prefer placeholders (`aap.example.com`). **Never invent** project IDs, tokens, passwords, DNS names, or registry secrets.

---

## Interview first — ask for anything not provided

At the start of a blank-GCP (or incomplete) deploy, **ask the user for every missing item**. Do not proceed past the access gate until you have answers or an explicit “skip / N/A”.

### Required questions (ask if not already in the chat / `.local/`)

1. **Are you Red Hat (or demo-catalog eligible)?**  
   - Yes → use **Demo Google Open Environment** (do not require personal billing).  
   - No → need a GCP project with billing.
2. **GCP project ID** (and how to auth: user `gcloud` login vs path to SA JSON in `.local/`)?
3. **Preferred region/zone** (default `us-central1` / `us-central1-a` OK)?
4. **DNS**: zone/FQDN you control for AAP/MCP (lab zone name if openenv)?
5. **Red Hat registry** username + token/password (or confirm already on the VM)?
6. **AAP containerized setup tarball** available / path to copy onto the VM?
7. **Chat paths wanted**: Cloud Run sandbox (recommended) / Agent Platform / Gemini CLI?
8. **MCP write mode** for create/launch demos? (default lab: yes if they want create prompts)
9. **Managed target inventory?**  
   > Do you want extra target hosts for inventories/jobs? If yes, I will create **one RHEL 9** and **one RHEL 10** VM and a **GCP dynamic inventory** in AAP that discovers them.

### If targets = yes

1. Create `rhel9-target` + `rhel10-target` (tag `aap-target`) — [DEPLOY-GCP-FROM-SCRATCH Step 1b](../../../docs/DEPLOY-GCP-FROM-SCRATCH.md).  
2. After AAP is up: create **Google Compute Engine** credential + inventory **GCP Dynamic** with source **Google Compute Engine**, filter/tag `aap-target` — [Step 6b](../../../docs/DEPLOY-GCP-FROM-SCRATCH.md).  
3. Sync inventory; add machine SSH credential so jobs can reach hosts.

### If targets = no

Continue with AAP server only; still offer a GCP dynamic inventory later if they change their mind.

### Also confirm (existing AAP path)

1. AAP URL + admin password (lab default documented as `R3dh2t!2026` only when this repo installed it)  
2. OpenShift `oc` **or** RHEL/Podman installer access  
3. MCP reachability + public CA for Gemini  

**Missing → ask. Never invent.**

---

## Access gate (summary)

**Blank GCP** — see full list in [DEPLOY-GCP-FROM-SCRATCH § GCP access](../../../docs/DEPLOY-GCP-FROM-SCRATCH.md):

- Project + billing **or** Demo Google Open Environment  
- IAM (Owner/Editor or listed roles), Vertex for chat, quotas for AAP VM (+ 2 targets)  
- RH registry + installer tarball + DNS  

**Existing AAP** — admin access, OpenShift or Podman path, client → MCP HTTPS.

---

## Workflow checklist

```
Progress:
- [ ] 0. Interview: ask for every missing input (GCP, DNS, registry, chat paths, targets)
- [ ] 1. Choose: blank GCP (DEPLOY-GCP-FROM-SCRATCH) OR existing AAP
- [ ] 2. Platform ready (VM + AAP+MCP)
- [ ] 2b. If targets requested: RHEL 9 + RHEL 10 VMs created
- [ ] 3. Record MCP_BASE_URL (prefer :443 + public CA)
- [ ] 4. MCP user + AAP_MCP_TOKEN
- [ ] 5. Smoke-test POST ${MCP_BASE_URL}/mcp
- [ ] 6. Write mode if needed
- [ ] 6b. If targets: GCP dynamic inventory (GCE cred + sync) + SSH machine cred
- [ ] 7. Path C sandbox and/or Path A/B
- [ ] 8. Give starter chatbot questions
```

## Blank GCP (summary)

Follow **[DEPLOY-GCP-FROM-SCRATCH.md](../../../docs/DEPLOY-GCP-FROM-SCRATCH.md)**:

0. Interview + enable APIs  
1. AAP RHEL VM  
1b. **Ask targets** → optional RHEL 9 + RHEL 10  
2. DNS  
3. Install AAP+MCP  
4. Token  
5. Trusted TLS / :443  
6. Write mode  
6b. **GCP dynamic inventory** (when targets or user wants cloud inventory)  
7–9. Sandbox / Agent / CLI  

Secrets only in `.local/` (gitignored). Default lab admin password: **`R3dh2t!2026`**.

## Deploy — OpenShift (summary)

```yaml
spec:
  mcp:
    disabled: false
    allow_write_operations: false
```

`MCP_BASE_URL` = MCP route host — **not** the gateway UI host.

## Deploy — Podman / RHEL (summary)

Greenfield: [DEPLOY-AAP-CONTAINERIZED.md](../../../docs/DEPLOY-AAP-CONTAINERIZED.md)

- FQDN hosts; no `ansible_become=true` in `[all:vars]`  
- `[ansiblemcp]` + TLS / write flags  
- Admin passwords default `R3dh2t!2026` for lab installs from this repo  

Prefer `${MCP_BASE_URL}/mcp` (all tools).

## Dedicated user + token

```bash
curl -sk -u "${MCP_USER}:${MCP_USER_PASSWORD}" \
  -H 'Content-Type: application/json' \
  -d '{"description":"mcp-client","scope":"write"}' \
  "${AAP_URL%/}/api/gateway/v1/tokens/"
```

## Connect Cursor / Gemini

- Cursor / CLI templates → `aap-mcp` → `/mcp`  
- [CONNECT-GEMINI.md](../../../docs/CONNECT-GEMINI.md); sandbox in `sandbox/`  
- Agent Platform: trusted HTTPS, allowlist `*`, `roles/mcp.toolUser`

## Starter chatbot questions

After Path C works, point users at preloaded UI chips **or**:

1. List job templates by name.  
2. What AAP MCP tools can create or change something?  
3. List inventories / hosts (should include GCP dynamic hosts if synced).  
4. Search the web for AAP MCP and compare to your tools.  
5. (Write) Create group / launch Demo Job Template.  
6. Can you create a project via MCP? *(Expect list only.)*

Full list: [DEPLOY-GCP-FROM-SCRATCH § Step 10](../../../docs/DEPLOY-GCP-FROM-SCRATCH.md).

## Verify

1. MCP initialize on `/mcp` → 200 without `-k` (for Gemini)  
2. Sandbox login + starter question  
3. If GCP inventory: hosts include `rhel9-target` / `rhel10-target` after sync  

## Security

1. Read-only MCP until write demos needed  
2. Dedicated token user; no secrets in git  
3. Job logs / inventory vars may reach the LLM  

## Agent behavior (mandatory)

1. **Ask for every missing prerequisite** before creating cloud resources.  
2. Red Hat users → **Demo Google Open Environment** when they lack a project.  
3. **Always ask** about extra target inventory (RHEL 9 + RHEL 10).  
4. If yes → create VMs **and** AAP **GCP / GCE dynamic inventory** + sync.  
5. Prefer Path C for first chat demo; do not invent URLs/tokens.  
6. Stay generic in committed docs (no workshop-only hostnames).  

## Additional resources

- [reference-deploy.md](reference-deploy.md)  
- [reference-gemini.md](reference-gemini.md)  
- [examples.md](examples.md)  
- [Official AAP MCP](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server)  
- [Gemini CLI MCP](https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html)  
