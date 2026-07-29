# Deploy AAP MCP + Gemini from a blank GCP project

End-to-end runbook: **empty Google Cloud project → working AAP MCP → Gemini chat** (browser sandbox, Agent Platform, and/or CLI).

Use this when the user says they have a **blank GCP environment** (or new project) and wants the full stack built from scratch. Sibling guides cover pieces in more depth; this is the **ordered master checklist**.

| Step | Detail guide |
|------|----------------|
| 1–4 | This doc (GCP + VM + DNS) |
| 5 | [DEPLOY-AAP-CONTAINERIZED.md](DEPLOY-AAP-CONTAINERIZED.md) |
| 5b | [INSTALL-APD.md](INSTALL-APD.md) — Ansible Product Demos catalog |
| 6–7 | [DEPLOY-AND-CONNECT.md](DEPLOY-AND-CONNECT.md) + TLS notes here / [CONNECT-GEMINI.md](CONNECT-GEMINI.md) |
| 8–10 | [CONNECT-GEMINI.md](CONNECT-GEMINI.md) (Paths A/B/C) |

Replace every placeholder (`PROJECT_ID`, `ZONE`, `aap.example.com`). **Never commit secrets** — keep them in gitignored `.local/` or Secret Manager.

**Default AAP admin password for installs from this repo:** `R3dh2t!2026` (lab default; change for production).

---

## GCP access you need (state this up front)

Before provisioning anything, confirm the user (or deployer SA) has the following. **If anything is missing, stop and ask** — do not invent projects, DNS, or credentials.

### Project & identity

| Access | Required for |
|--------|----------------|
| A GCP **project ID** you can use | All resources live here |
| **Billing enabled** on that project (or a lab that already bills for you) | VMs, LB, Cloud Run, DNS, Vertex |
| `gcloud` auth as a **user** or **service account** | Create/configure resources |
| Permission to **enable APIs** (`serviceusage.services.enable`) | Compute, DNS, Run, AI Platform, … |

Practical role bar (pick one):

- **Owner** or **Editor** on the project (simplest for labs), **or**
- A custom set including at least:
  - `roles/compute.admin` — VMs, disks, firewall, addresses
  - `roles/dns.admin` — Cloud DNS records (if using Cloud DNS)
  - `roles/run.admin` — Cloud Run sandbox
  - `roles/iam.serviceAccountAdmin` + `roles/iam.serviceAccountUser` — runtime SAs
  - `roles/serviceusage.serviceUsageAdmin` — enable APIs
  - `roles/aiplatform.user` — Vertex / Gemini for sandbox + CLI
  - Ability to grant **`roles/mcp.toolUser`** (Agent Platform Path B)
  - `roles/resourcemanager.projectIamAdmin` (or Owner) — to bind the roles above

### Quotas & networking

| Need | Notes |
|------|--------|
| Compute quota for **≥1× e2-standard-8** (AAP) | Plus **2× e2-medium** if target hosts are requested |
| External IPs / firewall rules | SSH 22, HTTPS 443, MCP 8448 (lab) |
| Optional: HTTPS load balancer quota | Prefer MCP on **:443** for Gemini Agent Platform |
| Outbound HTTPS from VMs | Pull `registry.redhat.io`, Let’s Encrypt, updates |

### Gemini / Vertex (chat paths)

| Access | Path |
|--------|------|
| Vertex AI / Gemini usable in the project | Path C sandbox, Path A CLI (Vertex auth) |
| `roles/aiplatform.user` on the Cloud Run runtime SA | Path C |
| `roles/mcp.toolUser` (+ agent create rights) | Path B Agent Platform |
| Agent Registry API enabled | Path B registration |

### Outside GCP (still required)

| Need | Why |
|------|-----|
| Red Hat entitlement + `registry.redhat.io` pull credentials | AAP container images |
| AAP **containerized setup** tarball (2.7+) | Installer |
| A **DNS name** you can point at the VM or LB | Trusted TLS for Gemini |
| SSH key / OS login to the VMs | Install and operate AAP |

**Red Hat associates / partners:** you can often get a ready-made billed GCP project via **Demo Google Open Environment** — see the next section instead of bringing your own billing account.

---

## If you are Red Hat: use Demo Google Open Environment

Red Hatters (and eligible partners with demo-system access) should **not** start from a personal GCP account when a lab catalog item exists. Use the **Demo Google Open Environment** (also called **GCP Blank Open Environment** / **GCP Open Environment** in some catalogs).

### What it gives you

| Item | Typical result |
|------|----------------|
| Ephemeral **GCP project** | Often named like `openenv-<guid>` |
| **Billing and quotas** suitable for VMs / demos | No personal credit card |
| Deployer identity | User login and/or a project **service account** + key from the provisioning email |
| Lifetime | Short-lived (commonly ~48h; extend per catalog policy) — finish the stack the same day when possible |

This repo’s lab path (AAP on a RHEL VM + MCP + Cloud Run sandbox + optional Agent Platform) fits that open environment well.

### How to get it

1. Open the Red Hat demo catalog (commonly [demo.redhat.com](https://demo.redhat.com) / RHPDS — use whatever portal your org points you to).
2. Order **Demo Google Open Environment** / **GCP Blank Open Environment** (exact catalog title can vary).
3. Wait for the “ready” email (often ~10–20 minutes).
4. From the email / service page, collect:
   - **GCP project ID** (and project number)
   - How to authenticate (`gcloud auth login` and/or a **JSON service account key**)
   - Any pre-created DNS / domain notes (some labs include `*.gcp.redhatworkshops.io`-style zones)

### After the open environment is ready

1. Store credentials only under gitignored `.local/` (never commit SA keys).
2. `gcloud config set project <openenv-project-id>`
3. Confirm you can list compute: `gcloud compute instances list`
4. Continue this guide from **Step 0** (enable APIs) using that project.
5. Prefer a hostname under the lab DNS (if provided) for AAP/MCP TLS.
6. Ask about **RHEL 9 + RHEL 10 target hosts** (Step 1b) as usual.
7. Remember the env is **ephemeral** — export notes/URLs the user needs before it expires.

### Agent behavior (Red Hat users)

When the user says they are Red Hat / have demo catalog access:

1. Tell them to provision **Demo Google Open Environment** first (unless they already have an `openenv-*` project).
2. Ask for the **project ID** + how you should auth (user ADC vs SA key path in `.local/`).
3. Do **not** ask them to attach a personal billing account unless they explicitly want a long-lived project.
4. Call out TTL / teardown risk before long installs.

---

## What you will build

```text
Laptop / Cursor
      │
      ├─► Path A: Gemini CLI  ──┐
      ├─► Path B: Agent Platform ─┼─► MCP HTTPS (:443 preferred)
      └─► Path C: Cloud Run chat ─┘         │
                                            ▼
                              GCP VM (RHEL) + AAP + ansiblemcp
                              AAP UI :443 · MCP :8448 (and/or LB :443)
                                            │
                         optional managed nodes (ask user)
                         ├── rhel9-target  (RHEL 9)
                         └── rhel10-target (RHEL 10)
```

| Piece | Typical result |
|-------|----------------|
| Compute (AAP) | RHEL 9 VM, ~8 vCPU / 32 GB / 100 GB |
| Compute (targets, optional) | **2 VMs**: RHEL **9** + RHEL **10** (smaller, e.g. e2-medium) for inventories/jobs |
| AAP | `https://aap.<your-domain>` |
| MCP | `https://mcp.<your-domain>` on **:443** (LB) or `https://aap.<fqdn>:8448` |
| Chat | Cloud Run URL + password login |
| Agent | `aap-ops-agent` in Agent Platform (optional) |

---

## Prerequisites (collect before coding)

Complete **[GCP access you need](#gcp-access-you-need-state-this-up-front)** first. Summary:

| Need | Why |
|------|-----|
| GCP project + billing (or Red Hat **Demo Google Open Environment**) | VMs, Cloud Run, LB, DNS, Vertex |
| IAM as documented above (Owner/Editor or listed roles) | Provision everything |
| Red Hat entitlement + `registry.redhat.io` pull secret | AAP container images |
| AAP **containerized setup** tarball (2.7+) | Installer |
| A **public DNS name** you control (Cloud DNS or lab zone) | TLS + Gemini trusted HTTPS |
| Optional: Let’s Encrypt / ACME reachable from the VM | Public CA for MCP |

---

## Progress checklist

```text
- [ ] 0. Enable GCP APIs + gcloud config
- [ ] 1. Create AAP RHEL VM + firewall + SSH
- [ ] 1b. Ask user: target hosts? If yes → create RHEL 9 + RHEL 10 managed nodes
- [ ] 2. DNS A records (AAP + MCP hostnames)
- [ ] 3. Install AAP + MCP on the VM (containerized)
- [ ] 3b. Install Ansible Product Demos (APD) via install-apd.yml
- [ ] 4. MCP user + gateway token (write scope if creating resources)
- [ ] 5. Trusted TLS on MCP + prefer :443 for Gemini
- [ ] 6. Enable MCP write mode (optional but needed for create/launch)
- [ ] 6b. If targets requested (or user wants cloud inventory): GCP dynamic inventory + SSH machine cred
- [ ] 7. Path C — Cloud Run chat sandbox (recommended first chat UI)
- [ ] 8. Path B — Agent Platform agent + Agent Registry (optional)
- [ ] 9. Path A — Gemini CLI (optional)
- [ ] 10. Smoke-test with starter questions below
```

---

## Step 0 — GCP project and APIs

```bash
export GCP_PROJECT_ID='your-gcp-project'
export GCP_REGION='us-central1'
export GCP_ZONE='us-central1-a'
gcloud config set project "${GCP_PROJECT_ID}"

gcloud services enable \
  compute.googleapis.com \
  dns.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  agentregistry.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  --project="${GCP_PROJECT_ID}"
```

Store lab secrets under `.local/` (gitignored), for example:

```bash
mkdir -p .local
# .local/gcp.env  — PROJECT, ZONE, SA key path
# .local/aap-gcp.env — AAP_URL, MCP_BASE_URL, AAP_MCP_TOKEN, SANDBOX_PASSWORD
```

---

## Step 1 — RHEL VM, disk, firewall, SSH

Sizing (growth-ish lab): **e2-standard-8** or larger, **100 GB** boot disk, image family **rhel-9**.

```bash
export VM_NAME='aap-server'
export NETWORK='default'

gcloud compute firewall-rules create allow-aap-https \
  --allow=tcp:443 --target-tags=aap-server --direction=INGRESS --priority=1000 || true
gcloud compute firewall-rules create allow-aap-mcp \
  --allow=tcp:8448 --target-tags=aap-server --direction=INGRESS --priority=1000 || true
gcloud compute firewall-rules create allow-ssh \
  --allow=tcp:22 --target-tags=aap-server --direction=INGRESS --priority=1000 || true

gcloud compute instances create "${VM_NAME}" \
  --zone="${GCP_ZONE}" \
  --machine-type=e2-standard-8 \
  --boot-disk-size=100GB \
  --image-family=rhel-9 \
  --image-project=rhel-cloud \
  --tags=aap-server \
  --scopes=cloud-platform
```

Create a non-root OS user (e.g. `aap`) with passwordless sudo, enable linger for rootless Podman, open firewalld ports **443** and **8448**. Details: [DEPLOY-AAP-CONTAINERIZED.md](DEPLOY-AAP-CONTAINERIZED.md) Step 1.

Record:

```bash
export VM_IP="$(gcloud compute instances describe "${VM_NAME}" --zone="${GCP_ZONE}" --format='get(networkInterfaces[0].accessConfigs[0].natIP)')"
echo "${VM_IP}"
```

---

## Step 1b — Optional managed target hosts (ask the user)

**Before or right after creating the AAP server, the agent MUST ask:**

> Do you want managed target hosts for inventories/job runs? If yes, I will create **two** VMs (RHEL **9** and RHEL **10**) and a **GCP dynamic inventory** in AAP that discovers them.

| Answer | Action |
|--------|--------|
| **No** / skip | Continue without extra VMs (optional GCP inventory later) |
| **Yes** | Create `rhel9-target` + `rhel10-target`, then **Step 6b GCP dynamic inventory** |

Use smaller machines than the AAP server (lab default **e2-medium**, 20 GB disk). Same zone/network; tag **`aap-target`** (dynamic inventory filter).

```bash
# Allow SSH to targets (from anywhere in lab, or tighten to AAP VM tag later)
gcloud compute firewall-rules create allow-aap-target-ssh \
  --allow=tcp:22 --target-tags=aap-target --direction=INGRESS --priority=1000 || true

# RHEL 9 managed node
gcloud compute instances create rhel9-target \
  --zone="${GCP_ZONE}" \
  --machine-type=e2-medium \
  --boot-disk-size=20GB \
  --image-family=rhel-9 \
  --image-project=rhel-cloud \
  --tags=aap-target \
  --scopes=cloud-platform

# RHEL 10 managed node
gcloud compute instances create rhel10-target \
  --zone="${GCP_ZONE}" \
  --machine-type=e2-medium \
  --boot-disk-size=20GB \
  --image-family=rhel-10 \
  --image-project=rhel-cloud \
  --tags=aap-target \
  --scopes=cloud-platform

export RHEL9_TARGET_IP="$(gcloud compute instances describe rhel9-target --zone="${GCP_ZONE}" --format='get(networkInterfaces[0].accessConfigs[0].natIP)')"
export RHEL10_TARGET_IP="$(gcloud compute instances describe rhel10-target --zone="${GCP_ZONE}" --format='get(networkInterfaces[0].accessConfigs[0].natIP)')"
echo "rhel9-target=${RHEL9_TARGET_IP}"
echo "rhel10-target=${RHEL10_TARGET_IP}"
```

If `rhel-10` image family is unavailable in the project/region, use the latest RHEL 10 image from `rhel-cloud` (`gcloud compute images list --project=rhel-cloud --filter='family:rhel-10'`).

Record IPs in `.local/aap-gcp.env` (`RHEL9_TARGET_IP`, `RHEL10_TARGET_IP`).

**Do not manually maintain a static host list as the primary inventory** when targets were requested — after AAP is installed, continue to **Step 6b (GCP dynamic inventory)**.

---

## Step 2 — DNS

You need at least one FQDN pointing at the VM (AAP + MCP can share one name on :443/:8448, or split `aap.` / `mcp.`).

**Cloud DNS example:**

```bash
export DNS_ZONE='your-zone-name'          # existing managed zone
export AAP_FQDN='aap.example.com'
export MCP_FQDN='mcp.example.com'         # can equal AAP_FQDN if you only use :8448

gcloud dns record-sets create "${AAP_FQDN}." --zone="${DNS_ZONE}" --type=A --ttl=60 --rrdatas="${VM_IP}"
# Optional second name for LB frontend:
gcloud dns record-sets create "${MCP_FQDN}." --zone="${DNS_ZONE}" --type=A --ttl=60 --rrdatas="${VM_IP}"
# If using an HTTPS load balancer later, point MCP_FQDN at the LB IP instead.
```

Gemini Agent Platform and Cloud clients need a **publicly trusted** cert. Prefer a hostname on **port 443**.

---

## Step 3 — Install AAP + MCP on the VM

Follow **[DEPLOY-AAP-CONTAINERIZED.md](DEPLOY-AAP-CONTAINERIZED.md)** on the VM:

1. Install `ansible-core`, Podman, firewalld.
2. Extract the AAP containerized setup tarball.
3. Inventory: FQDN hosts, `[ansiblemcp]`, admin passwords defaulting to `R3dh2t!2026`, `mcp_allow_write_operations` (start `false` or `true` for lab create demos), `automationmetrics_skip_install=true` if skipping metrics.
4. **Do not** set `ansible_become=true` in `[all:vars]`.
5. Run `ansible-playbook -i inventory-growth ansible.containerized_installer.install`.

Verify:

```bash
podman ps | grep -iE 'gateway|controller|ansiblemcp'
export AAP_URL="https://${AAP_FQDN}"
export MCP_BASE_URL="https://${AAP_FQDN}:8448"   # until LB/TLS on :443
```

---

## Step 3b — Install Ansible Product Demos (APD)

Seed AAP with the official product-demo catalog so Gemini/MCP list/launch prompts have real templates.

Follow **[INSTALL-APD.md](INSTALL-APD.md)** (upstream playbook [`install-apd.yml`](https://github.com/ansible/product-demos/blob/main/install-apd.yml)):

```bash
git clone https://github.com/ansible/product-demos.git
cd product-demos
export AAP_HOSTNAME="https://${AAP_FQDN}"
export AAP_USERNAME=admin
export AAP_PASSWORD='R3dh2t!2026'   # lab default from this repo; change if you set another
export AAP_VALIDATE_CERTS=false     # until public CA on the UI
ansible-navigator run -m stdout install-apd.yml
```

Confirm **APD | Single demo setup** / **APD | Multi-demo setup** exist in the UI. Optionally launch Single/Multi to materialize linux/cloud/… demo templates.

Skip only if the user explicitly declines APD.

---

## Step 4 — MCP user + token

Follow **[DEPLOY-AND-CONNECT.md](DEPLOY-AND-CONNECT.md)** Step 4:

1. Create dedicated user (e.g. `mcp-gemini`) with enough RBAC (org admin / superuser for lab).
2. Create gateway token with `"scope":"write"` if you want create/launch tools.
3. Export `AAP_MCP_TOKEN` (never commit).

Smoke-test (**aggregate endpoint exposes all tools**):

```bash
curl -sS -D - -o /tmp/mcp-init.sse \
  -X POST "${MCP_BASE_URL}/mcp" \
  -H "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}'
```

Expect HTTP 200 and JSON-RPC `serverInfo`. APD (Step 3b) should already provide listable job templates.

---

## Step 5 — Trusted TLS + :443 for Gemini

Self-signed installer certs **block** Gemini Agent Platform (and make GCP clients painful).

Recommended lab path:

1. Issue **Let’s Encrypt** (acme.sh or certbot) for `AAP_FQDN` / `MCP_FQDN`.
2. Install cert/key on the MCP nginx paths used by the `ansiblemcp` container; restart MCP.
3. Verify **without** `-k`: `curl -sS -o /dev/null -w '%{http_code}\n' …` → `200`.
4. For Agent Platform, put MCP on **:443**:
   - GCP **HTTPS load balancer** with the public cert, backend to VM `:8086` or `:8448` (match your nginx layout), **or**
   - reverse-proxy on the VM terminating TLS on 443 for `MCP_FQDN`.

Then:

```bash
export MCP_BASE_URL="https://${MCP_FQDN}"   # no :8448
```

Full notes: [CONNECT-GEMINI.md](CONNECT-GEMINI.md) § Shared requirements.

---

## Step 6 — Write mode (create / launch)

Server gate + token scope both matter:

| Layer | Setting |
|-------|---------|
| MCP server | `ALLOW_WRITE_OPERATIONS=true` / `mcp_allow_write_operations=true` |
| Token | gateway `"scope":"write"` |
| RBAC | user can create the target objects |

On Podman, changing write mode usually means recreating/restarting the `ansiblemcp` container with `ALLOW_WRITE_OPERATIONS=true` (or re-running the installer). Confirm logs show `Write operations: ENABLED`.

**Note:** MCP exposes many create tools (groups, credentials, launches, …) but **not** `projects_create` today — only `projects_list`.

---

## Step 6b — GCP dynamic inventory in AAP (when targets were requested)

If the user said **yes** to managed targets (or asks for cloud inventory), create a **Google Compute Engine** dynamic inventory so AAP discovers VMs from GCP (including `rhel9-target` / `rhel10-target`) on sync — not a one-off static host list.

Official refs: [Inventories — Google Compute Engine source](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.4/html/automation_controller_user_guide/controller-inventories), [GCE credentials](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.4/html/automation_controller_user_guide/controller-credentials).

### 1. Service account for inventory sync

Use the openenv deployer SA **or** create a dedicated SA with `roles/compute.viewer` (minimum) on the project, download a JSON key into `.local/` (gitignored):

```bash
export GCE_SA="aap-gce-inventory@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
gcloud iam service-accounts create aap-gce-inventory --display-name='AAP GCE inventory' || true
gcloud projects add-iam-policy-binding "${GCP_PROJECT_ID}" \
  --member="serviceAccount:${GCE_SA}" --role="roles/compute.viewer"
gcloud iam service-accounts keys create .local/gce-inventory-sa.json --iam-account="${GCE_SA}"
```

### 2. Machine credential (SSH to targets)

Create an AAP **Machine** credential (SSH key or password) that can log into the target VMs from the controller. Store the private key only in AAP / `.local/`, never in git.

Ensure controller → targets on TCP 22 (firewall tag `aap-target` or shared VPC rules).

### 3. GCE credential in AAP

In the AAP UI (**Credentials** → Add → type **Google Compute Engine**):

| Field | Value |
|-------|--------|
| Name | `GCP GCE Inventory` |
| Service Account Email | from the JSON (`client_email`) |
| Project | `${GCP_PROJECT_ID}` |
| Service Account JSON File | upload `.local/gce-inventory-sa.json` |

Or via Controller API (shape varies slightly by version) — prefer UI if unsure; agent may use `/api/controller/v2/credentials/` with `credential_type` for GCE after looking up the type id.

### 4. Inventory + inventory source

1. **Inventories** → Add → name `GCP Dynamic` (organization Default or your org).
2. **Sources** → Add:
   - **Source:** Google Compute Engine  
   - **Credential:** `GCP GCE Inventory`  
   - **Source variables** (YAML), filter to lab targets / zone:

```yaml
projects:
  - YOUR_GCP_PROJECT_ID
zones:
  - us-central1-a
filters:
  - labels.tag is not defined OR status = RUNNING
# Prefer network tags via hostvars after sync; plugin filters vary by version.
# Narrow with:
# filters:
#   - name = rhel9-target OR name = rhel10-target
compose:
  ansible_host: networkInterfaces[0].accessConfigs[0].natIP
keyed_groups:
  - prefix: tag
    key: tags
hostnames:
  - name
```

A practical lab filter when only the two targets matter:

```yaml
projects:
  - YOUR_GCP_PROJECT_ID
zones:
  - YOUR_ZONE
filters:
  - name = rhel9-target OR name = rhel10-target
compose:
  ansible_host: networkInterfaces[0].accessConfigs[0].natIP
hostnames:
  - name
```

3. Enable **Overwrite** / **Update on launch** as appropriate for the lab.
4. **Sync** the source. Confirm hosts `rhel9-target` and `rhel10-target` appear with public IPs.
5. Attach the **Machine** credential on job templates that should SSH to these hosts (or set inventory-level defaults where supported).

### 5. Verify

```bash
# After sync, Controller API (admin or MCP token with rights):
curl -sk -u "admin:${AAP_PASSWORD}" \
  "${AAP_URL%/}/api/controller/v2/inventories/?search=GCP" 
# Or in sandbox: "List hosts in the GCP Dynamic inventory."
```

Agent must **ask** for the GCE SA JSON / project if not already available — never invent credentials.

---

## Step 7 — Path C: Cloud Run chat sandbox (recommended)

This is the most reliable **browser chatbot** for AAP MCP.

1. Enable Vertex usage for a runtime SA (`roles/aiplatform.user`).
2. Deploy `sandbox/` from this repo:

```bash
export SANDBOX_PASSWORD="$(openssl rand -base64 18)"
export SESSION_SECRET="$(openssl rand -hex 32)"
export RUNTIME_SA="aap-mcp-sandbox@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create aap-mcp-sandbox --display-name='AAP MCP sandbox' || true
gcloud projects add-iam-policy-binding "${GCP_PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/aiplatform.user"

cd sandbox
gcloud run deploy aap-mcp-sandbox \
  --project="${GCP_PROJECT_ID}" --region="${GCP_REGION}" --source=. \
  --allow-unauthenticated --service-account="${RUNTIME_SA}" \
  --memory=1Gi --cpu=1 --timeout=300 \
  --set-env-vars="^@^GOOGLE_CLOUD_PROJECT=${GCP_PROJECT_ID}@GOOGLE_CLOUD_LOCATION=global@MCP_BASE_URL=${MCP_BASE_URL}@GEMINI_MODEL=gemini-2.5-flash@AAP_MCP_TOKEN=${AAP_MCP_TOKEN}@SANDBOX_PASSWORD=${SANDBOX_PASSWORD}@SESSION_SECRET=${SESSION_SECRET}@ENABLE_GOOGLE_SEARCH=true@ENABLE_URL_CONTEXT=true@ENABLE_CODE_EXECUTION=true@MCP_TOOLSETS=mcp"
```

3. Open the Cloud Run URL, log in with `SANDBOX_PASSWORD`, ask a starter question below.

Details / local run: [CONNECT-GEMINI.md](CONNECT-GEMINI.md) Path C.

**Vertex note:** Search + MCP function declarations in one request often 400; the sandbox falls back by intent.

---

## Step 8 — Path B: Gemini Agent Platform (optional)

1. Grant `roles/mcp.toolUser` (and usually `roles/aiplatform.user`) to principals that create/run agents.
2. Fill `configs/gemini-agent-tools.json` → single `aap-mcp` tool URL `${MCP_BASE_URL}/mcp`, Bearer token, `network.allowlist: [{ "domain": "*" }]`.
3. `POST .../agents` (or PATCH existing `aap-ops-agent`).
4. Register Agent Registry service for `${MCP_BASE_URL}/mcp`.
5. Call Interactions API with `background: true` (and typically `stream: true`).

**Reality check:** Interactions sometimes stay `in_progress` without binding MCP tools. Prefer Path C for demos. Still deploy Path B when you need the managed agent resource.

---

## Step 9 — Path A: Gemini CLI (optional)

```bash
export AAP_MCP_TOKEN='...'
export MCP_BASE_URL='https://mcp.example.com'
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT="${GCP_PROJECT_ID}"
export GEMINI_CLI_TRUST_WORKSPACE=true

gemini mcp add --transport http aap-mcp \
  "${MCP_BASE_URL}/mcp" \
  --header "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -s user

gemini --skip-trust -y -p "List Ansible job template names using MCP."
```

---

## Step 10 — Starter questions for the chatbot

Use these after Path C (or CLI) is up. Copy/paste into the sandbox chat.

### Read / discover (safe)

1. **What AAP MCP tools do you have, and name five that can create or change something.**
2. **List job templates by name.**
3. **List inventories and how many hosts each has.**
4. **List projects and organizations.**
5. **List execution environments.**
6. **Show recent jobs and their status.**
7. **List users and teams (names only).**

### Web + AAP combined

8. **Search the web for Ansible Automation Platform MCP, then compare that to the tools you actually have.**
9. **Open https://docs.redhat.com and summarize how to deploy the AAP MCP server in a few bullets.**

### Write mode (only if write is enabled)

10. **Create an inventory group named `chatbot-demo` in inventory id 1 with a short description.**
11. **Create a team named `mcp-demo-team` in the Default organization (or the org id you have).**
12. **Launch APD | Single demo setup (or another APD template) and report the job id and status.** *(survey/extra vars may be required; may 403 if RBAC is tight)*

### If target hosts / GCP dynamic inventory

13. **List hosts in the GCP Dynamic inventory — you should see `rhel9-target` and `rhel10-target` after sync.**
14. **Which groups did the GCP inventory sync create for those hosts?**

### Capability checks

15. **Can you create a new AAP project via MCP? If not, what project tools exist?**  
    *(Expect: only `projects_list` — no `projects_create`.)*
16. **Cancel nothing — just explain which cancel tools you see.**

---

## Agent / Cursor skill behavior (blank GCP)

Run the **step-by-step interview** in [SKILL.md](../.cursor/skills/aap-gemini-mcp/SKILL.md) (Q0→Q10): **one step per turn**, branch on answers, then confirm the plan before provisioning.

Highlights:

1. Ask starting point (blank GCP vs existing AAP).  
2. Red Hat → Demo Google Open Environment when no project.  
3. Collect project/auth, zone, DNS, registry, tarball, chat paths, write mode, APD.  
4. Ask about **target inventory**; if yes → RHEL 9+10 VMs + **GCP dynamic inventory** (Step 6b).  
5. Default **yes** for APD install (Step 3b) unless the user declines.  
6. Summarize and get confirmation → execute this checklist.  
7. Never invent secrets or hostnames; prefer Path C for first chat.

---

## Troubleshooting (GCP-specific)

| Symptom | Fix |
|---------|-----|
| Installer preflight non-root / become | Remove `ansible_become=true` from `[all:vars]` |
| Hub + `localhost` hostname | Use FQDN in inventory |
| MCP returns AAP UI HTML | Wrong host — use MCP LB / `:8448`, not gateway-only URL |
| Agent create hangs / 404 | Public CA on MCP; prefer `:443` |
| Sandbox chat 400 with Search+MCP | Expected; sandbox tool-bundle fallback |
| Interactions stuck `in_progress` | Use Path C; check registry, allowlist `*`, `roles/mcp.toolUser` |
| Write tools missing | `ALLOW_WRITE_OPERATIONS=true` + write token + restart MCP |
| Cloud Run cannot call Vertex | `roles/aiplatform.user` on runtime SA |

---

## Related files

| Path | Purpose |
|------|---------|
| [DEPLOY-AAP-CONTAINERIZED.md](DEPLOY-AAP-CONTAINERIZED.md) | RHEL/Podman AAP + MCP install |
| [INSTALL-APD.md](INSTALL-APD.md) | Ansible Product Demos (`install-apd.yml`) |
| [DEPLOY-MCP.md](DEPLOY-MCP.md) | OpenShift / brownfield MCP |
| [DEPLOY-AND-CONNECT.md](DEPLOY-AND-CONNECT.md) | User, token, Cursor |
| [CONNECT-GEMINI.md](CONNECT-GEMINI.md) | Gemini paths A/B/C deep dive |
| [`sandbox/`](../sandbox/) | Chat UI source |
| [`configs/`](../configs/) | CLI / agent / Cursor templates |
