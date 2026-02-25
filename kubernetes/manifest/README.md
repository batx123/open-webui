# Open WebUI — Kubernetes Manifests

Deploys Open WebUI, Ollama, Open WebUI Pipelines, and Langfuse (LLM tracing) onto a MicroK8s cluster across two namespaces: `open-webui` and `langfuse`.

## Folder Structure

```
kubernetes/manifest/
├── base/                             # Core resources (CPU-only Ollama)
│   ├── kustomization.yaml
│   ├── open-webui.yaml               # Namespace definition
│   ├── ollama-service.yaml           # Ollama LoadBalancer service
│   ├── ollama-statefulset.yaml       # Ollama pod (CPU mode)
│   ├── webui-deployment.yaml         # Open WebUI + Tailscale sidecar
│   ├── webui-service.yaml            # Open WebUI LoadBalancer service
│   ├── webui-pvc.yaml                # 2Gi PVC for Open WebUI data
│   ├── tailscale-rbac.yaml           # ServiceAccount, Role, RoleBinding for Tailscale
│   ├── tailscale-serve-config.yaml   # Tailscale HTTPS serve config
│   ├── pipelines-deployment.yaml     # Open WebUI Pipelines service
│   ├── pipelines-service.yaml        # Pipelines ClusterIP service (port 9099)
│   ├── pipelines-pvc.yaml            # 2Gi PVC for installed pipeline scripts
│   └── pipelines-secret.yaml         # Pipelines API key (gitignored — create locally)
├── gpu/                              # GPU overlay (extends base)
│   ├── kustomization.yaml            # References ../base, patches Ollama for GPU
│   └── ollama-statefulset-gpu.yaml   # Patches Ollama to use 2x nvidia.com/gpu
└── langfuse/                         # Langfuse LLM tracing (separate namespace)
    ├── kustomization.yaml
    ├── namespace.yaml                # langfuse namespace
    ├── postgres-pvc.yaml             # 10Gi PVC for trace storage
    ├── postgres-deployment.yaml      # Postgres 15
    ├── postgres-service.yaml         # Postgres ClusterIP service
    ├── langfuse-deployment.yaml      # Langfuse v2 + Tailscale sidecar
    ├── langfuse-service.yaml         # Langfuse ClusterIP service (port 3000)
    ├── tailscale-rbac.yaml           # ServiceAccount, Role, RoleBinding for Tailscale
    ├── tailscale-serve-config.yaml   # Tailscale HTTPS serve config (proxies port 3000)
    └── langfuse-secret.yaml          # DB creds + NextAuth secrets (gitignored — create locally)
```

---

## Deploying

### open-webui namespace

#### Prerequisites — secrets must exist before first apply

```bash
# 1. Create namespace
microk8s kubectl create namespace open-webui

# 2. Tailscale auth key (get a reusable key from https://login.tailscale.com/admin/settings/keys)
microk8s kubectl create secret generic tailscale-auth \
  --from-literal=tskey=<your-tailscale-auth-key> \
  -n open-webui

# 3. Open WebUI app secrets
microk8s kubectl create secret generic webui-secrets \
  --from-literal=WEBUI_SECRET_KEY=$(openssl rand -hex 32) \
  -n open-webui

# 4. Pipelines API key — copy base/pipelines-secret.yaml.example, fill in a random key,
#    save as base/pipelines-secret.yaml (already gitignored)
openssl rand -hex 32   # use this as PIPELINES_API_KEY
microk8s kubectl apply -f kubernetes/manifest/base/pipelines-secret.yaml
```

#### Deploy

**CPU-only (Ollama runs on CPU):**
```bash
microk8s kubectl apply -k kubernetes/manifest/base/
```

**GPU (primary — patches Ollama to use 2x NVIDIA GPU):**
```bash
microk8s kubectl apply -k kubernetes/manifest/gpu/
```

---

### langfuse namespace

#### Prerequisites

```bash
# 1. Create namespace
microk8s kubectl create namespace langfuse

# 2. Tailscale auth key — must be a separate key from the open-webui one
microk8s kubectl create secret generic tailscale-auth \
  --from-literal=tskey=<your-second-tailscale-auth-key> \
  -n langfuse

# 3. Langfuse secrets — copy langfuse/langfuse-secret.yaml, fill in values, apply
#    (file is gitignored — never commit it)
#
#    Required values:
#      POSTGRES_PASSWORD: any strong password
#      DATABASE_URL: postgresql://langfuse:<POSTGRES_PASSWORD>@postgres-service:5432/langfuse
#      NEXTAUTH_SECRET: $(openssl rand -base64 32)
#      SALT: $(openssl rand -base64 32)   # must differ from NEXTAUTH_SECRET
#      NEXTAUTH_URL: https://langfuse.<your-tailnet>.ts.net
microk8s kubectl apply -f kubernetes/manifest/langfuse/langfuse-secret.yaml
```

#### Deploy

```bash
microk8s kubectl apply -k kubernetes/manifest/langfuse/
microk8s kubectl rollout status deployment/langfuse -n langfuse
microk8s kubectl rollout status deployment/postgres -n langfuse
```

---

## Connecting Pipelines to Open WebUI

The Pipelines service URL is registered as an **OpenAI-compatible connection**, not in the Pipelines settings page. Open WebUI detects it as a Pipelines server automatically.

1. **Admin Panel → Settings → Connections → OpenAI API → +**
2. URL: `http://pipelines-service:9099`
3. Key: the value from `pipelines-secret.yaml`
4. Save

Once connected, go to **Admin Panel → Settings → Pipelines** — the server URL will appear in the dropdown and you can install pipeline scripts.

### Installing the Langfuse Filter Pipeline

From the Pipelines management page, paste this URL into the "Install from GitHub URL" field:
```
https://github.com/open-webui/pipelines/blob/main/examples/filters/langfuse_filter_pipeline.py
```

After installing, select the filter and configure its valves:
- **Secret Key**: `sk-lf-...` (from Langfuse project → Settings → API Keys)
- **Public Key**: `pk-lf-...` (same location)
- **Host**: `http://langfuse-service.langfuse.svc.cluster.local:3000`

---

## Services & Access

| Service              | Namespace   | Type         | Access                                              |
|----------------------|-------------|--------------|-----------------------------------------------------|
| open-webui           | open-webui  | LoadBalancer | `http://<LAN-IP>` (MetalLB)                         |
| open-webui (remote)  | open-webui  | Tailscale    | `https://openwebui.<tailnet>.ts.net`                |
| ollama               | open-webui  | LoadBalancer | `http://<LAN-IP>:11434` (LAN tools, Continue, etc.) |
| pipelines-service    | open-webui  | ClusterIP    | `http://pipelines-service:9099` (in-cluster only)   |
| langfuse             | langfuse    | Tailscale    | `https://langfuse.<tailnet>.ts.net`                 |
| langfuse (in-cluster)| langfuse    | ClusterIP    | `http://langfuse-service.langfuse.svc.cluster.local:3000` |
| postgres             | langfuse    | ClusterIP    | `postgres-service:5432` (in-cluster only)           |

---

## Architecture

```
Browser (LAN/remote)
        │
        ▼
open-webui-deployment pod (open-webui namespace)
├── open-webui (:8080)
│   ├── → http://ollama-service:11434    (Ollama, in-cluster DNS)
│   └── → http://pipelines-service:9099  (Pipelines, registered as OpenAI connection)
│           └── Langfuse filter → http://langfuse-service.langfuse.svc.cluster.local:3000
└── ts-sidecar (Tailscale, proxies :443 → :8080)

langfuse pod (langfuse namespace)
├── langfuse (:3000) → postgres-service:5432
└── ts-sidecar (Tailscale, proxies :443 → :3000)
```

### imagePullPolicy

All containers tracking mutable remote tags (`:main`, `:latest`) use `imagePullPolicy: Always`. This means Kubernetes checks the remote registry digest on every pod start and pulls only changed layers — not a full re-download. Postgres uses `IfNotPresent` since it's pinned to `postgres:15`.

---

## Secrets

### open-webui namespace

| Secret            | Key                | Description                                      |
|-------------------|--------------------|--------------------------------------------------|
| `tailscale-auth`  | `tskey`            | Tailscale auth key for Open WebUI sidecar        |
| `tailscale`       | (many)             | Tailscale node state (auto-managed by sidecar)   |
| `webui-secrets`   | `WEBUI_SECRET_KEY` | Open WebUI session signing key                   |
| `pipelines-secret`| `PIPELINES_API_KEY`| API key for Pipelines ↔ Open WebUI auth (**gitignored**) |

### langfuse namespace

| Secret             | Keys                                                    | Description                        |
|--------------------|---------------------------------------------------------|------------------------------------|
| `tailscale-auth`   | `tskey`                                                 | Tailscale auth key for Langfuse sidecar |
| `tailscale`        | (many)                                                  | Tailscale node state (auto-managed) |
| `langfuse-secrets` | `POSTGRES_PASSWORD`, `DATABASE_URL`, `NEXTAUTH_SECRET`, `SALT`, `NEXTAUTH_URL` | Langfuse app secrets (**gitignored**) |

### Tailscale Auth Key Rotation

To rotate either Tailscale auth key (update in-place to preserve node state):

```bash
# For open-webui namespace:
microk8s kubectl create secret generic tailscale-auth \
  --from-literal=tskey=<new-key> \
  -n open-webui --dry-run=client -o yaml | microk8s kubectl apply -f -
microk8s kubectl rollout restart deployment/open-webui-deployment -n open-webui

# For langfuse namespace:
microk8s kubectl create secret generic tailscale-auth \
  --from-literal=tskey=<new-key> \
  -n langfuse --dry-run=client -o yaml | microk8s kubectl apply -f -
microk8s kubectl rollout restart deployment/langfuse -n langfuse
```

---

## Common Operations

**Check all pods:**
```bash
microk8s kubectl get pods -n open-webui
microk8s kubectl get pods -n langfuse
```

**Update images (rolling restart — no node reboot needed):**
```bash
microk8s kubectl rollout restart deployment/open-webui-deployment -n open-webui
microk8s kubectl rollout restart statefulset/ollama -n open-webui
microk8s kubectl rollout restart deployment/langfuse -n langfuse
```

**View logs:**
```bash
microk8s kubectl logs -n open-webui deploy/open-webui-deployment -c open-webui
microk8s kubectl logs -n open-webui deploy/open-webui-deployment -c ts-sidecar
microk8s kubectl logs -n open-webui deploy/pipelines
microk8s kubectl logs -n langfuse deploy/langfuse -c langfuse
```

**Confirm Tailscale serve is active:**
```bash
microk8s kubectl exec -n open-webui deploy/open-webui-deployment -c ts-sidecar \
  -- tailscale serve status
```

**After updating a secret, restart the affected deployment:**
```bash
# Secrets are not hot-reloaded — pods must restart to pick up changes
microk8s kubectl rollout restart deployment/<name> -n <namespace>
```

**Ollama connectivity from LAN tools:**
```bash
# Find the MetalLB-assigned IP
microk8s kubectl get svc -n open-webui
# Use it for Continue plugin, Python scripts, Ollama CLI, etc.
OLLAMA_HOST=http://<LAN-IP>:11434 ollama run llama3.2
```
