---
name: aap-gemini-mcp
description: >-
  Deploys Ansible Automation Platform (AAP) with the MCP server from a blank GCP
  project or existing AAP (OpenShift / RHEL Podman), then connects Cursor,
  Gemini CLI, Gemini Agent Platform, or the browser chat sandbox. Interview the
  user step by step (one decision at a time) based on their answers; ask for any
  missing inputs; on GCP optionally create RHEL 9+10 targets and a GCP dynamic
  inventory. Use for from-scratch GCP deploys, Podman AAP+MCP, MCP tokens,
  Cloud Run chatbot, or AAP MCP tool use.
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

## Step-by-step interview (mandatory)

Interview **one step at a time**. Ask the question for that step, **wait for the user’s answer**, then branch. Do **not** dump the full questionnaire in one message. Skip a step only if the answer is already clearly in the conversation or in `.local/` files the user pointed you to.

### Rules

1. Start at **Q0**. After each answer, follow the branch → next Q.  
2. If unsure, give a one-line recommendation and re-ask.  
3. After the last interview step, **summarize the plan** and get confirmation before provisioning.  
4. Missing required data → ask; never invent.

```text
Q0 starting point?
├─ blank GCP / from scratch ──► Q1
├─ existing AAP ──────────────► QE1
└─ unsure ────────────────────► brief options, re-ask Q0
```

### Blank GCP / from-scratch path

**Q1 — Are you Red Hat (or demo-catalog eligible)?**  
- **Yes** → If no project yet, tell them to order **Demo Google Open Environment**. → **Q2**  
- **No** → They need a GCP project with billing. → **Q2**

**Q2 — Do you already have a GCP project ready?**  
- **Yes** → Ask **project ID** + auth (`gcloud` user login vs SA JSON path under `.local/`). → **Q3**  
- **No** + Red Hat → Pause until openenv is ready; re-ask **Q2**  
- **No** + not Red Hat → Pause until they create a billed project; re-ask **Q2**

**Q3 — Use region/zone `us-central1` / `us-central1-a`?**  
- **Yes** → record defaults → **Q4**  
- **No** → ask for region + zone → **Q4**

**Q4 — What DNS will AAP/MCP use?** (zone + FQDNs, or lab zone from openenv)  
- Have it → record → **Q5**  
- Don’t → explain public DNS needed for Gemini TLS; wait until they have a zone → **Q5**

**Q5 — Red Hat registry credentials available?** (`registry.redhat.io`)  
- **Yes** → how provided (chat once / on VM / `.local/` path) → **Q6**  
- **No** → pause until pull secret exists → re-ask **Q5**

**Q6 — AAP containerized setup tarball available?**  
- **Yes** → path or “will copy to VM” → **Q7**  
- **No** → point to access.redhat.com; pause → **Q7** when ready

**Q7 — Which Gemini chat paths?** (multi-select OK)  
- **C** Cloud Run sandbox (recommended)  
- **B** Agent Platform  
- **A** Gemini CLI  
If none → recommend **C**, confirm → **Q8**

**Q8 — Enable MCP write mode** (create/launch)?  
- **Yes** / **No** → record → **Q9**

**Q9 — Extra target inventory?**  
> Do you want managed target hosts? If yes, I will create **one RHEL 9** and **one RHEL 10** VM and a **GCP dynamic inventory** in AAP.

- **Yes** → `CREATE_TARGET_HOSTS=yes` (VMs in Step 1b + dynamic inventory in Step 6b) → **Q10**  
- **No** → AAP server only → **Q10**

**Q10 — Ready to proceed?**  
Show a short summary (project, zone, DNS, registry, tarball, chat paths, write mode, targets).  
- **Yes** → provision via [DEPLOY-GCP-FROM-SCRATCH.md](../../../docs/DEPLOY-GCP-FROM-SCRATCH.md)  
- **Change X** → jump back to that Q  
- **No** → stop

### Existing AAP path (from Q0)

**QE1** — OpenShift vs RHEL/Podman vs unknown?  
**QE2** — AAP URL + admin access? (password only if needed)  
**QE3** — MCP already enabled? → get `MCP_BASE_URL` or enable per docs  
**QE4** — Same as **Q7–Q9** (chat paths, write mode, targets if GCP available)  
**QE5** — Confirm plan → [DEPLOY-AND-CONNECT.md](../../../docs/DEPLOY-AND-CONNECT.md) / [CONNECT-GEMINI.md](../../../docs/CONNECT-GEMINI.md)

### During deploy

If blocked on a secret (registry password, SA key path, DNS record), ask **that one thing**, then continue — still one step at a time.

---

## Access gate (summary)

**Blank GCP** — [DEPLOY-GCP-FROM-SCRATCH § GCP access](../../../docs/DEPLOY-GCP-FROM-SCRATCH.md):

- Project + billing **or** Demo Google Open Environment  
- IAM, Vertex for chat, quotas for AAP VM (+ 2 targets if Q9=yes)  
- RH registry + installer tarball + DNS  

**Existing AAP** — admin access, OpenShift or Podman path, client → MCP HTTPS.

---

## Workflow checklist

```
Progress:
- [ ] 0. Step-by-step interview done (Q0→Q10 or QE) + plan confirmed
- [ ] 1. Platform ready (VM + AAP+MCP)
- [ ] 1b. If Q9=yes: RHEL 9 + RHEL 10 VMs
- [ ] 2. Record MCP_BASE_URL (prefer :443 + public CA)
- [ ] 3. MCP user + AAP_MCP_TOKEN
- [ ] 4. Smoke-test POST ${MCP_BASE_URL}/mcp
- [ ] 5. Write mode if Q8=yes
- [ ] 5b. If Q9=yes: GCP dynamic inventory + SSH machine cred
- [ ] 6. Chat paths from Q7 (prefer Path C first)
- [ ] 7. Starter chatbot questions
```

## Blank GCP (summary)

Follow **[DEPLOY-GCP-FROM-SCRATCH.md](../../../docs/DEPLOY-GCP-FROM-SCRATCH.md)** after the interview:

0. Enable APIs → 1 AAP VM → 1b targets if Q9 → 2 DNS → 3 install → 4 token → 5 TLS → 6 write → 6b GCP inventory → 7–9 chat paths  

Secrets in `.local/` only. Lab admin password default: **`R3dh2t!2026`**.

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

After Path C works, use preloaded UI chips **or**:

1. List job templates by name.  
2. What AAP MCP tools can create or change something?  
3. List inventories / hosts (GCP dynamic hosts if synced).  
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

1. Run the **step-by-step interview** (one question/branch per turn); wait before continuing.  
2. Red Hat without a project → **Demo Google Open Environment**.  
3. **Q9 = yes** → RHEL 9+10 VMs **and** GCP dynamic inventory after AAP is up.  
4. Prefer Path C for first chat demo; never invent URLs/tokens.  
5. Stay generic in committed docs (no workshop-only hostnames).  

## Additional resources

- [reference-deploy.md](reference-deploy.md)  
- [reference-gemini.md](reference-gemini.md)  
- [examples.md](examples.md)  
- [Official AAP MCP](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server)  
- [Gemini CLI MCP](https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html)  
