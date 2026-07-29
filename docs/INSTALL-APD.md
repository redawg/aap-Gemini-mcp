# Install Ansible Product Demos (APD) on AAP

After AAP is up, load the [Ansible Product Demos](https://github.com/ansible/product-demos) catalog with the upstream install playbook. That seeds orgs, projects, credentials, inventories, and job templates (`APD | Single demo setup`, `APD | Multi-demo setup`, plus domain demos) so MCP / Gemini prompts have real content to list and launch.

Official sources:

- Playbook: [`install-apd.yml`](https://github.com/ansible/product-demos/blob/main/install-apd.yml)
- Project README: [ansible/product-demos](https://github.com/ansible/product-demos)
- Demo catalog site: [ansible.github.io/product-demos](https://ansible.github.io/product-demos/)

Run this from a machine that can reach the AAP gateway HTTPS URL (laptop or the AAP VM). Do **not** commit tokens or passwords.

---

## Prerequisites

| Need | Notes |
|------|--------|
| AAP gateway reachable | `https://aap.example.com` (UI / API) |
| Admin (or superuser) auth | Username+password **or** gateway token |
| `ansible-navigator` | From AAP package repos or [ansible-dev-tools](https://pypi.org/project/ansible-dev-tools/) |
| Podman (or Docker) | Pulls the APD execution environment |
| Outbound HTTPS | Clone GitHub + pull `quay.io/ansible-product-demos/apd-ee-*` |

Optional env vars (only if you configure those APD credentials):

- `ANSIBLE_GALAXY_SERVER_CERTIFIED_TOKEN` / `ANSIBLE_GALAXY_SERVER_VALIDATED_TOKEN` — Automation Hub tokens  
- Cloud keys (`AWS_*`, etc.) — only for cloud demos you plan to run  

Lab installs from this repo use admin password **`R3dh2t!2026`** unless you changed it.

---

## Step 1 — Clone product-demos

```bash
git clone https://github.com/ansible/product-demos.git
cd product-demos
```

---

## Step 2 — Authenticate to AAP

```bash
export AAP_HOSTNAME='https://aap.example.com'

# Preferred for labs: admin basic auth
export AAP_USERNAME='admin'
export AAP_PASSWORD='YOUR_AAP_ADMIN_PASSWORD'

# Or use a token instead of username/password:
# export AAP_TOKEN='YOUR_GATEWAY_TOKEN'

# Labs with self-signed UI certs often need:
export AAP_VALIDATE_CERTS=false
```

`install-apd.yml` asserts that `AAP_HOSTNAME` is set and that either `AAP_TOKEN` **or** both `AAP_USERNAME` and `AAP_PASSWORD` are set.

---

## Step 3 — Run the install playbook

Uses the APD execution environment (roles from `infra.aap_configuration`):

```bash
ansible-navigator run -m stdout install-apd.yml
```

Expect the play to create (among other resources):

- Organization **Ansible Product Demos (APD)**  
- Project **Ansible Product Demos** (SCM → this GitHub repo)  
- Execution environment **Product Demos EE**  
- Inventory **Ansible Product Demos Inventory**  
- Templates **APD | Single demo setup** and **APD | Multi-demo setup**  

Optional: launch **APD | Single demo setup** (or Multi) and select categories (`linux`, `cloud`, …) to materialize additional demo job templates.

---

## Step 4 — Verify

UI: **Automation → Templates** — search `APD`.

API:

```bash
curl -sk -u "${AAP_USERNAME}:${AAP_PASSWORD}" \
  "${AAP_HOSTNAME%/}/api/controller/v2/job_templates/?search=APD"
```

MCP / Gemini smoke prompts after connect:

1. `List job templates by name.` — should include APD templates.  
2. `Launch APD | Single demo setup` — only with MCP write mode + RBAC (survey may require UI or extra vars).

---

## Where this fits in this repo

| Guide | When to run APD |
|-------|-----------------|
| [DEPLOY-GCP-FROM-SCRATCH.md](DEPLOY-GCP-FROM-SCRATCH.md) | **Step 3b** after AAP+MCP install |
| [DEPLOY-AAP-CONTAINERIZED.md](DEPLOY-AAP-CONTAINERIZED.md) | After Step 6 verify, before MCP client wiring |
| Existing AAP (any path) | Anytime after gateway API works |

Then continue with [DEPLOY-AND-CONNECT.md](DEPLOY-AND-CONNECT.md) (MCP user/token) and [CONNECT-GEMINI.md](CONNECT-GEMINI.md).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Assert on missing env vars | Export `AAP_HOSTNAME` + auth as above |
| EE pull fails | Login to Quay / fix Podman; retry `ansible-navigator` |
| SSL verify errors | `AAP_VALIDATE_CERTS=false` for lab self-signed UI |
| `ansible-navigator: command not found` | Install ansible-dev-tools or AAP navigator RPM |
| Templates missing after run | Re-run playbook; check Controller job events / play output |

Never commit `AAP_PASSWORD`, `AAP_TOKEN`, or Hub tokens. Keep them in the shell or gitignored `.local/`.
