# Open WebUI — Kubernetes Manifests

Deploys the Open WebUI frontend and Ollama LLM backend into the `open-webui` namespace on a MicroK8s cluster.

## Folder Structure

```
kubernetes/manifest/
├── base/                          # Core resources (CPU-only Ollama)
│   ├── kustomization.yaml
│   ├── open-webui.yaml            # Namespace definition
│   ├── ollama-service.yaml        # Ollama LoadBalancer service
│   ├── ollama-statefulset.yaml    # Ollama pod (CPU mode)
│   ├── webui-deployment.yaml      # Open WebUI + Tailscale sidecar
│   ├── webui-service.yaml         # Open WebUI LoadBalancer service
│   ├── webui-pvc.yaml             # 2Gi PVC for Open WebUI data
│   ├── tailscale-rbac.yaml        # ServiceAccount, Role, RoleBinding for Tailscale
│   └── tailscale-serve-config.yaml # Tailscale HTTPS serve config
└── gpu/                           # GPU overlay (extends base)
    ├── kustomization.yaml          # References ../base, patches Ollama for GPU
    └── ollama-statefulset-gpu.yaml # Patches Ollama to use 2x nvidia.com/gpu
```

## Deploying

### Prerequisites — secrets must exist before first apply

The deployment references two secrets that Kubernetes will not create automatically.
Create them before running `kubectl apply`:

```bash
# 1. Tailscale auth key (get a reusable key from https://login.tailscale.com/admin/settings/keys)
microk8s kubectl create namespace open-webui   # if not already present
microk8s kubectl create secret generic tailscale-auth \
  --from-literal=tskey=<your-tailscale-auth-key> \
  -n open-webui

# 2. Open WebUI app secrets (can be empty to start; add WEBUI_SECRET_KEY etc. as needed)
microk8s kubectl create secret generic webui-secrets \
  --from-literal=WEBUI_SECRET_KEY=<random-string> \
  -n open-webui
```

### The Ollama IP chicken-and-egg

`webui-deployment.yaml` needs the MetalLB-assigned LAN IP of the Ollama service
in `OLLAMA_BASE_URL` — but MetalLB only assigns that IP *after* the service is
deployed. Two ways to handle this:

**Option A — Two-phase deploy (quick fix):**
1. Apply everything (Open WebUI will start but will show "cannot connect to Ollama"):
   ```bash
   microk8s kubectl apply -k kubernetes/manifest/gpu/
   ```
2. Look up the IP MetalLB gave the Ollama service:
   ```bash
   microk8s kubectl get svc -n open-webui
   # Note the EXTERNAL-IP on the ollama-service row
   ```
3. Edit `base/webui-deployment.yaml` — replace `<LAN-IP-ollama>` with that IP,
   then re-apply:
   ```bash
   microk8s kubectl apply -k kubernetes/manifest/gpu/
   ```

**Option B — Use in-cluster DNS (recommended, eliminates the problem entirely):**

Because both pods live in the same `open-webui` namespace, Kubernetes DNS resolves
the service name directly — no external IP needed:

```yaml
# in base/webui-deployment.yaml, change OLLAMA_BASE_URL to:
value: "http://ollama-service:11434"
```

With this change you never need to know or hardcode the MetalLB IP for the
Ollama→WebUI connection. The LoadBalancer IP is still useful for reaching the
Ollama API directly from your LAN (e.g., with `curl` or the Ollama CLI).

---

**Normal deployment (CPU Ollama):**
```bash
microk8s kubectl apply -k kubernetes/manifest/base/
```

**GPU deployment (primary — patches Ollama to use 2x NVIDIA GPU):**
```bash
microk8s kubectl apply -k kubernetes/manifest/gpu/
```

The `gpu/` overlay extends `base/` — it deploys everything in base plus patches
the Ollama StatefulSet to request `nvidia.com/gpu: "2"`. Use this for day-to-day
operations if the node has GPUs available.

## Services & Access

<!-- Replace <LAN-IP-webui> and <LAN-IP-ollama> with the actual external IPs
     assigned by your LoadBalancer (e.g. MetalLB on your home/office subnet).
     These are private LAN addresses — change them to match your environment. -->
| Service      | Type         | External IP       | Port  | Description                  |
|--------------|--------------|-------------------|-------|------------------------------|
| open-webui   | LoadBalancer | &lt;LAN-IP-webui&gt;  | 80    | LAN HTTP access (→ pod :8080)|
| ollama       | LoadBalancer | &lt;LAN-IP-ollama&gt; | 11434 | Ollama API (LAN only)        |

**Tailscale HTTPS (remote access):**
```
https://<your-node>.<your-tailnet>.ts.net
```
<!-- Replace <your-node> with the Tailscale machine name you assigned (e.g. "openwebui")
     and <your-tailnet> with your tailnet ID shown in the Tailscale admin console
     (e.g. "tail1234ab"). This URL is unique to your Tailscale account — anyone
     with a valid Tailscale auth on your tailnet can reach the service at this address. -->
Provided by the Tailscale sidecar inside the `open-webui-deployment` pod using
Tailscale Serve. Valid LetsEncrypt certificate — no browser warnings.
Requires Tailscale MagicDNS HTTPS to be enabled in the Tailscale admin console.

## Architecture

The `open-webui-deployment` pod runs two containers:

1. **open-webui** — the chat UI, listens on port 8080, connects to Ollama at
   `http://<LAN-IP-ollama>:11434`
   <!-- <LAN-IP-ollama> is the MetalLB-assigned LAN IP for the ollama LoadBalancer service -->
2. **ts-sidecar** — Tailscale in userspace mode, runs an HTTPS reverse proxy
   via `TS_SERVE_CONFIG` that proxies `<your-node>.<your-tailnet>.ts.net:443` →
   `http://127.0.0.1:8080`
   <!-- <your-node>.<your-tailnet>.ts.net is your Tailscale FQDN — unique to your tailnet -->

Tailscale node state is persisted in the `tailscale` Kubernetes secret so the
node reconnects as `openwebui` across pod restarts without consuming a new
auth key use.

## Secrets

| Secret           | Key    | Description                              |
|------------------|--------|------------------------------------------|
| `tailscale-auth` | `tskey` | Tailscale auth key for node registration |
| `tailscale`      | (many) | Tailscale node state (auto-managed)      |
| `webui-secrets`  | —      | Open WebUI application secrets           |

### Tailscale Auth Key Rotation

The current auth key **expires May 20, 2026**.

To rotate:
1. Generate a new reusable (non-ephemeral) auth key at https://login.tailscale.com/admin/settings/keys
2. Update the secret:
   ```bash
   microk8s kubectl create secret generic tailscale-auth \
     --from-literal=tskey=<new-key> \
     -n open-webui --dry-run=client -o yaml | \
     microk8s kubectl apply -f -
   ```
3. Restart the deployment to pick up the new key:
   ```bash
   microk8s kubectl rollout restart deployment/open-webui-deployment -n open-webui
   ```

> Note: Because Tailscale state is persisted in the `tailscale` secret, the node
> will re-register as `openwebui` using the new key and retain its place on the
> tailnet. You do not need to delete the `tailscale` state secret.

## Common Operations

**Check pod status:**
```bash
microk8s kubectl get pods -n open-webui
```

**View Tailscale sidecar logs:**
```bash
microk8s kubectl logs -n open-webui deploy/open-webui-deployment -c ts-sidecar
```

**Confirm Tailscale serve is active:**
```bash
microk8s kubectl exec -n open-webui deploy/open-webui-deployment -c ts-sidecar \
  -- tailscale serve status
```

**Restart Open WebUI (e.g., after config changes):**
```bash
microk8s kubectl rollout restart deployment/open-webui-deployment -n open-webui
```

**Update the Tailscale serve config** (edit `base/tailscale-serve-config.yaml`, then):
```bash
microk8s kubectl apply -k kubernetes/manifest/gpu/
microk8s kubectl rollout restart deployment/open-webui-deployment -n open-webui
```
