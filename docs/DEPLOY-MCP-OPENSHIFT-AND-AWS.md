# Deploy AAP MCP: OpenShift vs AWS containers

Two supported ways to run the **Ansible Automation Platform MCP server**, plus an AWS ECS option for a standalone MCP sidecar when AAP already exists elsewhere.

| Target | When to use | MCP URL shape |
|--------|-------------|---------------|
| **OpenShift (operator)** | AAP installed via AAP Operator on OCP / ROSA | `https://<mcp-route>/…/mcp` |
| **AWS RHEL + containerized AAP** | AAP on EC2/RHEL with Red Hat containerized installer (Podman) | `https://<host>:8448/…/mcp` |
| **AWS ECS (standalone MCP)** | AAP already running; you only need an MCP HTTP front-end on ECS/Fargate | `https://<alb>/mcp` or `/job_management/mcp` |

Official Red Hat docs: [Deploy the MCP server](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/html/extending_ansible_automation_platform_with_ai/extend-assembly_deploying_ansible_mcp_server).

After MCP is up, continue with tokens + Gemini in [DEPLOY-AND-CONNECT.md](DEPLOY-AND-CONNECT.md).

---

## 1. Deploy on an OpenShift cluster (`oc`)

### Prerequisites

- `oc` logged into the **same** cluster that hosts AAP  
- Cluster-admin or edit rights in the AAP namespace (workshop: `aap`)  
- AAP Operator installed; AAP instance healthy  

```bash
oc login https://api.<cluster>:6443 --token='…'   # or kubeadmin
oc whoami --show-server
oc get ansibleautomationplatform -A
```

### Step A — Enable MCP on the platform CR

```bash
NS=aap
NAME=aap   # CR name from: oc -n aap get ansibleautomationplatform

oc -n "$NS" patch ansibleautomationplatform "$NAME" --type merge -p '
spec:
  mcp:
    disabled: false
    allow_write_operations: false
'
```

Console alternative: **Operators → Ansible Automation Platform →** instance → **YAML** → add the same `spec.mcp` block.

### Step B — Ensure `AnsibleMCPServer` exists

```bash
oc -n "$NS" get ansiblemcpserver
```

If nothing appears within a few minutes, create it (Lightspeed / MCP operator reconciles this CR):

```bash
AAP_HOST=$(oc -n "$NS" get route aap -o jsonpath='{.spec.host}')

cat <<EOF | oc apply -f -
apiVersion: mcpserver.ansible.com/v1alpha1
kind: AnsibleMCPServer
metadata:
  name: aap-mcp
  namespace: ${NS}
spec:
  public_base_url: "https://${AAP_HOST}"
  allow_write_operations: false
EOF
```

Optional if MCP cannot trust AAP TLS:

```yaml
spec:
  extra_settings:
    - setting: IGNORE_CERTIFICATE_ERRORS
      value: true
```

Prefer a CA bundle secret (`bundle_cacert_secret`) over ignoring certs in production.

### Step C — Wait for workload + route

```bash
oc -n "$NS" rollout status deploy/aap-mcp --timeout=180s
oc -n "$NS" get pods,svc,route -l app.kubernetes.io/name=aap-mcp

export MCP_BASE_URL="https://$(oc -n "$NS" get route aap-mcp -o jsonpath='{.spec.host}')"
echo "$MCP_BASE_URL"
```

Workshop example:

`https://aap-mcp-aap.apps.cluster-kw8lw-1.dyn.redhatworkshops.io`

### Step D — Smoke test

```bash
export AAP_MCP_TOKEN='…'   # from AAP UI Tokens or gateway API

curl -sk -X POST "${MCP_BASE_URL}/job_management/mcp" \
  -H "Authorization: Bearer ${AAP_MCP_TOKEN}" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
```

Expect HTTP 200 and JSON-RPC `serverInfo`. Root page (`GET $MCP_BASE_URL/`) lists toolset paths.

### Step E — Write mode (optional)

```bash
oc -n "$NS" patch ansiblemcpserver aap-mcp --type merge -p '
spec:
  allow_write_operations: true
'
# Per Red Hat: delete and recreate AnsibleMCPServer if write mode was changed after first deploy
```

### OpenShift notes

- MCP is **not** the AAP gateway host (`aap-aap.apps…`). Use the **`aap-mcp`** route.  
- Reconciler: `ansible-lightspeed-operator-controller-manager` (role `mcpserver`).  
- Changing write permissions after deploy: delete `AnsibleMCPServer` and recreate.

---

## 2. Deploy with Red Hat containerized AAP on AWS (EC2 / RHEL)

This is the **supported** path when AAP runs as containers on **RHEL 9/10** in AWS (typically an EC2 instance), using the AAP **containerized installer** (Podman), not ECS.

### Prerequisites

| Need | Notes |
|------|--------|
| RHEL 9/10 EC2 (or similar) sized for AAP | Same host often runs gateway + MCP |
| AAP 2.6+ subscription / installer bundle | Containerized installer (`setup.sh` / inventory) |
| Podman (installer-managed) | MCP runs as an `ansiblemcp` container |
| Security group | Allow **8448/tcp** from Gemini clients (and 443 for AAP UI) |
| DNS / TLS | Hostname for MCP; certs for HTTPS |

### Step A — Inventory: add MCP host + vars

Edit the AAP containerized installer inventory (path varies; often under the installer directory or `/etc/ansible-automation-platform/inventory`):

```ini
# MCP server host (same as AAP host is common)
[ansiblemcp]
aap.example.com

[all:vars]
# false = read-only (recommended first)
mcp_allow_write_operations=false
mcp_ignore_certificate_errors=false

# TLS for MCP HTTPS on 8448
mcp_tls_cert=/path/to/tls.crt
mcp_tls_key=/path/to/tls.key

# Optional
# mcp_extra_settings='[{"setting": "DEFAULT_PAGE_SIZE", "value": "25"}]'
```

### Step B — Run the containerized installer / upgrade

From the installer directory (exact command depends on your AAP bundle):

```bash
./setup.sh
# or, if your env uses an explicit inventory:
# ./setup.sh --inventory /path/to/inventory
```

Re-run after inventory changes so the MCP component is deployed or updated.

### Step C — Verify on the host

```bash
podman ps | grep -i mcp
# expect an ansiblemcp (or similar) container listening for HTTPS

export MCP_BASE_URL="https://aap.example.com:8448"
```

Open AWS security group / NACL for **8448** from clients that will call MCP (Gemini CLI, Agent Platform egress, etc.).

### Step D — Smoke test

Same `curl` initialize call as OpenShift, against `https://<host>:8448/job_management/mcp`.

### AWS EC2 networking checklist

1. Elastic IP or Route53 name → instance  
2. SG inbound: `443` (AAP UI), `8448` (MCP), SSH as needed  
3. Outbound: registry.redhat.io (install), and whatever execution nodes need  
4. Put MCP behind an AWS ALB only if you terminate TLS correctly and forward to 8448  

---

## 3. Deploy standalone AAP MCP on **Amazon ECS** (Fargate/EC2)

Use this when **AAP already exists** (for example OpenShift AAP in a workshop) and you want MCP as a **separate** container service on AWS ECS. This is **not** the operator-integrated MCP; it is the community/standalone [aap-mcp-server](https://github.com/ansible/aap-mcp-server) (or the Red Hat MCP image if you mirror it into ECR) talking to AAP over HTTPS.

> Prefer OpenShift operator MCP or containerized installer MCP for production AAP. Use ECS when you need MCP in an AWS account next to Gemini/other clients and AAP is remote.

### Architecture

```
Gemini → ALB (HTTPS) → ECS task (MCP :3000)
                           → HTTPS → existing AAP gateway/API
```

### Prerequisites

- ECS cluster (Fargate recommended)  
- ECR repository for the MCP image  
- Secrets Manager / SSM for `AAP_MCP_TOKEN` (and never bake tokens into the image)  
- Outbound HTTPS from tasks to AAP URL  
- Inbound HTTPS from Gemini to the ALB  

### Step A — Build/push image

Example using the public project (adjust to your hardened/prod image):

```bash
git clone https://github.com/ansible/aap-mcp-server.git
cd aap-mcp-server
npm ci && npm run build

# Example Dockerfile (illustrative — pin versions for prod)
# FROM node:22-alpine
# WORKDIR /app
# COPY package*.json ./
# RUN npm ci --omit=dev
# COPY dist ./dist
# COPY aap-mcp.yaml data ./
# ENV MCP_PORT=3000
# EXPOSE 3000
# CMD ["node", "dist/index.js"]   # confirm entrypoint from project

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com"
docker build -t aap-mcp-server .
docker tag aap-mcp-server:latest "$ECR_URI:latest"
docker push "$ECR_URI:latest"
```

### Step B — Task definition (env)

| Env var | Purpose |
|---------|---------|
| `BASE_URL` | AAP gateway URL, e.g. `https://aap-aap.apps.…` |
| `BEARER_TOKEN_OAUTH2_AUTHENTICATION` | Optional default token; better to require client Bearer |
| `MCP_PORT` | `3000` |
| `ALLOW_WRITE_OPERATIONS` | `false` initially |

Mount or bake `aap-mcp.yaml` with `ignore-certificate-errors` only if required.

### Step C — Service + ALB

1. Create ECS service (1+ tasks), port **3000**.  
2. Application Load Balancer, HTTPS listener (ACM cert), target group → tasks:3000.  
3. Health check: `GET /api/v1/health` (if exposed) or TCP 3000.  
4. Security groups: ALB ← clients; tasks ← ALB only; tasks → 443 to AAP.  

```bash
export MCP_BASE_URL="https://mcp.yourdomain.com"   # ALB DNS / custom domain
```

### Step D — Client config

Point Gemini at ALB toolset URLs the same way as platform MCP:

```text
https://mcp.yourdomain.com/job_management/mcp
```

(Confirm path layout for the image you run: standalone often uses `/mcp` and `/mcp/{toolset}`.)

Clients still send:

```http
Authorization: Bearer <AAP_API_TOKEN>
```

### ECS security notes

- Store AAP tokens in **Secrets Manager**; inject as env or have clients send Bearer (preferred).  
- Restrict ALB with WAF / IP allowlists if MCP is not public.  
- Keep `ALLOW_WRITE_OPERATIONS=false` until required.  

---

## Path cheat sheet

| Deploy | Base URL |
|--------|----------|
| OpenShift | `https://aap-mcp-<instance>.apps.<cluster>` |
| Containerized on AWS EC2 | `https://<rhel-host>:8448` |
| ECS standalone | `https://<alb-or-domain>` |

Toolsets (either style, depending on build):

```text
{BASE}/job_management/mcp
{BASE}/mcp/job_management
{BASE}/mcp
```

---

## Which should you choose?

| Situation | Choose |
|-----------|--------|
| AAP already on OpenShift (this workshop) | **§1 OpenShift** (already verified) |
| Greenfield AAP on RHEL in AWS | **§2 Containerized installer** on EC2 |
| AAP remote; need MCP inside an AWS VPC for Gemini | **§3 ECS** standalone MCP |

---

## Next

1. Create AAP token → `AAP_MCP_TOKEN`  
2. Wire Gemini CLI / Agent → [DEPLOY-AND-CONNECT.md](DEPLOY-AND-CONNECT.md)  
3. Templates: `configs/gemini-cli-settings.json`, `configs/gemini-agent-tools.json`  
