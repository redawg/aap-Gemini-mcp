# Deploy AAP on RHEL (containerized) with MCP

Generic step-by-step: install **Ansible Automation Platform** on **RHEL 9 or 10** with the **containerized (Podman) installer**, including the **Ansible MCP server** on port **8448**.

Works on any cloud or bare metal (GCP, AWS, Azure, on-prem). Replace all placeholders (`aap.example.com`, passwords, paths) with your values.

Official references:

- [Containerized installation](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/containerized_installation/index)
- [Deploy the MCP server](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server)

After this guide, continue with [INSTALL-APD.md](INSTALL-APD.md) (product demos), then [DEPLOY-AND-CONNECT.md](DEPLOY-AND-CONNECT.md) (token + Cursor / Gemini).

**Blank Google Cloud project?** Use the master checklist [DEPLOY-GCP-FROM-SCRATCH.md](DEPLOY-GCP-FROM-SCRATCH.md) (VM + DNS + TLS + chat), which calls this guide for the AAP install steps.

---

## What you will end up with

| Component | Typical URL |
|-----------|-------------|
| AAP gateway UI | `https://aap.example.com` |
| MCP base | `https://aap.example.com:8448` |
| Toolset example | `https://aap.example.com:8448/job_management/mcp` |

---

## Prerequisites checklist

| Need | Notes |
|------|--------|
| RHEL 9.4+ or RHEL 10 | Growth topology: about **8 vCPU / 32 GB RAM / 100 GB disk** (minimums are lower; follow Red Hat sizing) |
| Non-root OS user with `sudo` | Installer **must** run as non-root (`ansible_user_uid != 0`) |
| AAP subscription | Entitlement to pull `registry.redhat.io/ansible-automation-platform-*` images |
| Registry credentials | Service account or RH login for `registry_username` / `registry_password` |
| Installer tarball | **Ansible Automation Platform *N* Containerized Setup** from [access.redhat.com downloads](https://access.redhat.com/downloads) (online ~10–15 MB) |
| DNS / hostname | An **FQDN** that resolves to the host (required when Automation Hub is colocated) |
| Firewall | **443/tcp** (UI), **8448/tcp** (MCP), **22/tcp** (SSH admin) from clients |
| `ansible-core` + Podman | From RHEL AppStream (installer also uses them) |

---

## Step 1 — Prepare the RHEL host

```bash
# As the non-root install user (example: aap)
sudo dnf -y install ansible-core podman wget curl git openssl firewalld chrony
sudo systemctl enable --now firewalld chronyd
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=8448/tcp
sudo firewall-cmd --reload
sudo loginctl enable-linger "$(whoami)"   # helpful for rootless Podman
```

Confirm you are **not** root:

```bash
id -u   # must not be 0
```

Map the FQDN locally if DNS is not ready yet (optional):

```bash
echo '127.0.0.1 aap.example.com' | sudo tee -a /etc/hosts
```

---

## Step 2 — Download and extract the installer

1. Log into [access.redhat.com](https://access.redhat.com/downloads).
2. Download **Ansible Automation Platform \<version\> Containerized Setup** (online installer).
3. Copy to the RHEL host and extract:

```bash
mkdir -p ~/aap-install && cd ~/aap-install
# scp ansible-automation-platform-containerized-setup-*.tar.gz here
tar xzf ansible-automation-platform-containerized-setup-*.tar.gz
cd ansible-automation-platform-containerized-setup-*
ls   # expect collections/, inventory templates, README
```

Bundled (offline) installs use the larger **Setup Bundle** and set `bundle_install=true` — see Red Hat docs.

---

## Step 3 — TLS material for MCP (and optionally gateway)

Self-signed lab example:

```bash
mkdir -p ~/certs
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout ~/certs/tls.key -out ~/certs/tls.crt \
  -subj "/CN=aap.example.com" \
  -addext "subjectAltName=DNS:aap.example.com,IP:127.0.0.1"
chmod 600 ~/certs/tls.key
```

Prefer a real CA-signed cert in production. For labs, you may set `mcp_ignore_certificate_errors=true` (MCP → AAP TLS only).

---

## Step 4 — Write the inventory (growth + MCP)

Use an **FQDN** for every host group when Automation Hub is on the same node. Do **not** use bare `localhost` as the inventory hostname when hub is present (OCI registry limitation).

Do **not** set `ansible_become=true` under `[all:vars]` — that makes fact gathering run as root and fails preflight (“remote user should be a non root user”). The installer playbooks become root only where needed; the OS user needs passwordless `sudo`.

AAP 2.7+ may require Automation Metrics when Controller is installed. For a minimal lab, set `automationmetrics_skip_install=true`, **or** add a real `[automationmetrics]` host and the related DB vars (see installer README).

Example inventory (save as `inventory-growth`):

```ini
# Growth topology + MCP — replace aap.example.com and all secrets

[automationgateway]
aap.example.com ansible_connection=local

[automationcontroller]
aap.example.com ansible_connection=local

[automationhub]
aap.example.com ansible_connection=local

[automationeda]
aap.example.com ansible_connection=local

[database]
aap.example.com ansible_connection=local

[ansiblemcp]
aap.example.com ansible_connection=local

[all:vars]
ansible_connection=local

postgresql_admin_username=postgres
postgresql_admin_password=<set your own>

registry_username=<registry service account or RH login>
registry_password=<registry token or password>

redis_mode=standalone

# Skip Automation Metrics in minimal labs (AAP 2.7+). Remove if you deploy [automationmetrics].
automationmetrics_skip_install=true

gateway_admin_password=R3dh2t!2026
gateway_pg_host=aap.example.com
gateway_pg_password=<set your own>

controller_admin_password=R3dh2t!2026
controller_pg_host=aap.example.com
controller_pg_password=<set your own>
controller_percent_memory_capacity=0.5

hub_admin_password=R3dh2t!2026
hub_pg_host=aap.example.com
hub_pg_password=<set your own>
hub_seed_collections=false

eda_admin_password=R3dh2t!2026
eda_pg_host=aap.example.com
eda_pg_password=<set your own>

# MCP (HTTPS :8448)
mcp_allow_write_operations=false
mcp_ignore_certificate_errors=true
mcp_tls_cert=/home/<install-user>/certs/tls.crt
mcp_tls_key=/home/<install-user>/certs/tls.key
```

**Default AAP platform admin password for installs guided by this repo:** `R3dh2t!2026`  
Use the same value for `gateway_admin_password`, `controller_admin_password`, `hub_admin_password`, and `eda_admin_password` on single-node labs so UI login stays consistent. Change it for production.

---

## Step 5 — Run the installer

From the extracted installer directory:

```bash
export ANSIBLE_COLLECTIONS_PATH="$PWD/collections:${ANSIBLE_COLLECTIONS_PATH:-}"
ansible-playbook -i inventory-growth ansible.containerized_installer.install \
  2>&1 | tee ~/aap-install.log
```

Expect **30–90+ minutes** (image pulls dominate). Watch `~/aap-install.log` or:

```bash
tail -f ~/aap-install.log
```

Success looks like `PLAY RECAP` with `failed=0`.

### Common preflight failures

| Symptom | Fix |
|---------|-----|
| `remote user should be a non root user` | Run as non-root; remove `ansible_become=true` from inventory |
| `You must have a host set in the [automationmetrics] section` | Set `automationmetrics_skip_install=true` or configure `[automationmetrics]` |
| Gateway hostname / FQDN assertion | Use `aap.example.com` (with a `.`), not `localhost` |
| Registry pull unauthorized | Fix `registry_username` / `registry_password` and entitlement |

---

## Step 6 — Verify AAP and MCP

```bash
podman ps
# expect gateway, controller, hub, postgres, redis, ansiblemcp, …

export AAP_URL='https://aap.example.com'
export MCP_BASE_URL='https://aap.example.com:8448'

curl -sk -u "admin:${GATEWAY_ADMIN_PASSWORD}" \
  "${AAP_URL%/}/api/controller/v2/ping/"

curl -sk "${MCP_BASE_URL}/"   # lists toolset paths
```

Open the UI in a browser: `https://aap.example.com` (accept self-signed cert if lab).

---

## Step 7 — Cloud notes (optional)

Same RHEL steps apply on any provider. Typical extras:

1. Create VPC / subnet / firewall (allow 22, 443, 8448).
2. Attach a static public IP (or private + VPN/bastion).
3. Create DNS **A** (or **AAAA**) record: `aap.example.com` → that IP.
4. Use a RHEL cloud image (pay-as-you-go or Cloud Access) so BaseOS/AppStream work.

Do not bake registry passwords or admin passwords into git or public images.

---

## Next

1. [INSTALL-APD.md](INSTALL-APD.md) — seed Ansible Product Demos (`install-apd.yml`)  
2. [DEPLOY-AND-CONNECT.md](DEPLOY-AND-CONNECT.md) — dedicated MCP user, API token, Cursor / Gemini clients  
3. [DEPLOY-MCP.md](DEPLOY-MCP.md) — OpenShift MCP path, or MCP-only changes on an existing containerized install  
