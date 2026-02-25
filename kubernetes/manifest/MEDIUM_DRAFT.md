# Running Ollama + Open WebUI on Kubernetes: GPU Support, Tailscale Remote Access, and a Shared LLM Backend

*Part 2 of a series on self-hosted AI infrastructure. [Part 1 covered deploying and configuring Ollama for chat and agentic coding.](https://medium.com/@ben.gordy/deploy-and-configure-ollama-for-chat-and-agentic-ai-coding-d518242db386)*

---

In Part 1, we got Ollama running and wired it into our daily workflow — powering the Continue plugin in VSCode, local Python scripts, and a basic chat interface. It worked. But it was running as a bare process on a machine, and that started to feel fragile once we wanted to:

- Access the chat UI from outside our LAN without opening firewall ports
- Expose the Ollama API to multiple machines reliably, without managing a daemon
- Toggle GPU acceleration without editing configs by hand
- Have everything restart cleanly on reboot without thinking about it

Kubernetes solves all of this. This post walks through the full deployment: a MicroK8s cluster running Open WebUI and Ollama, with GPU support via a Kustomize overlay, and a Tailscale sidecar that gives us a valid HTTPS URL from anywhere — no port forwarding, no self-signed certificates.

---

## What We're Building

```
                        ┌─────────────────────────────────────────┐
                        │         open-webui namespace            │
                        │                                         │
  Browser (LAN)  ──────►│  webui-service (LoadBalancer :80)       │
                        │         │                               │
  Browser (Remote)──────┤  ts-sidecar (Tailscale :443 HTTPS) ─┐  │
  via Tailscale         │         │                            │  │
                        │         ▼                            │  │
                        │  open-webui container (:8080) ◄──────┘  │
                        │         │                               │
                        │         │  http://ollama-service:11434  │
                        │         ▼  (in-cluster DNS)             │
                        │  ollama StatefulSet (:11434)            │
                        │         │                               │
                        └─────────┼───────────────────────────────┘
                                  │
  LAN machines ─────────────────► ollama-service (LoadBalancer :11434)
  (Continue plugin, Python,       │
   Ollama CLI)                    ▼
                             300Gi PVC (model weights)
```

One pod runs Open WebUI alongside a Tailscale sidecar for remote HTTPS. A separate StatefulSet runs Ollama with 300Gi of persistent storage for model weights. Both are wired up with services — one private (in-cluster DNS for Open WebUI → Ollama), one public to the LAN (for direct Ollama API access from other tools).

---

## Prerequisites

- **MicroK8s** installed and running. We're using the `microk8s kubectl` wrapper throughout.
- **MetalLB** enabled (`microk8s enable metallb`) with a pool of LAN IPs assigned. This is what gives our LoadBalancer services real addresses.
- **NVIDIA GPU plugin** enabled if you want GPU inference (`microk8s enable gpu`). The base manifests work without it.
- **A Tailscale account** — the free tier is fine. You'll need an auth key from the Tailscale admin console, and MagicDNS HTTPS enabled on your tailnet.

---

## Manifest Structure

We're using Kustomize to manage two deployment configurations from a single set of base manifests:

```
kubernetes/manifest/
├── base/                           # CPU-only, everything runs without a GPU
│   ├── kustomization.yaml
│   ├── open-webui.yaml             # Namespace: open-webui
│   ├── ollama-statefulset.yaml     # Ollama pod + 300Gi PVC
│   ├── ollama-service.yaml         # LoadBalancer on port 11434
│   ├── webui-deployment.yaml       # Open WebUI + Tailscale sidecar
│   ├── webui-service.yaml          # LoadBalancer on port 80
│   ├── webui-pvc.yaml              # 2Gi PVC for Open WebUI app data
│   ├── tailscale-rbac.yaml         # ServiceAccount + Role for Tailscale
│   └── tailscale-serve-config.yaml # Tailscale HTTPS proxy config
└── gpu/                            # GPU overlay — extends base
    ├── kustomization.yaml
    └── ollama-statefulset-gpu.yaml  # Patches Ollama to use 2x nvidia.com/gpu
```

The `gpu/` overlay is a pure patch — it inherits everything from `base/` and adds one thing: a resource patch that tells Kubernetes to schedule the Ollama pod on a node with NVIDIA GPUs available. You don't duplicate any other config.

---

## Step 1: Create Secrets Before Anything Else

Two secrets must exist in the cluster before the first `kubectl apply`. Kubernetes will not create them for you, and the pods will fail to start if they're missing.

**Create the namespace first:**
```bash
microk8s kubectl create namespace open-webui
```

**Tailscale auth key** — get a reusable (non-ephemeral) key from https://login.tailscale.com/admin/settings/keys:
```bash
microk8s kubectl create secret generic tailscale-auth \
  --from-literal=tskey=<your-tailscale-auth-key> \
  -n open-webui
```

**Open WebUI app secret** — used internally for session signing:
```bash
microk8s kubectl create secret generic webui-secrets \
  --from-literal=WEBUI_SECRET_KEY=$(openssl rand -hex 32) \
  -n open-webui
```

A third secret (`tailscale`) is created automatically by the Tailscale sidecar on first run and persisted across pod restarts — you don't manage this one.

---

## Step 2: Deploy

**CPU-only (Ollama runs on CPU):**
```bash
microk8s kubectl apply -k kubernetes/manifest/base/
```

**GPU (primary — Ollama gets 2× NVIDIA GPU):**
```bash
microk8s kubectl apply -k kubernetes/manifest/gpu/
```

Use the GPU overlay if the node has GPUs and the NVIDIA plugin is installed. The overlay simply patches the Ollama StatefulSet to add:

```yaml
resources:
  limits:
    nvidia.com/gpu: "2"
```

Kustomize merges this with the base definition — the CPU/memory requests, the persistent volume, the service — all remain unchanged.

**Check that everything came up:**
```bash
microk8s kubectl get pods -n open-webui
# NAME                                    READY   STATUS    RESTARTS
# ollama-0                                1/1     Running   0
# open-webui-deployment-xxxxxxxxx-xxxxx   2/2     Running   0
```

The Open WebUI pod shows `2/2` because it runs two containers: the web app and the Tailscale sidecar.

---

## Step 3: Find Your Service IPs

MetalLB assigns real LAN IPs to the LoadBalancer services after deploy. Check what they are:

```bash
microk8s kubectl get svc -n open-webui
# NAME          TYPE           CLUSTER-IP      EXTERNAL-IP      PORT(S)
# ollama        LoadBalancer   10.152.183.x    192.168.1.xxx    11434:xxxxx/TCP
# open-webui    LoadBalancer   10.152.183.x    192.168.1.yyy    80:xxxxx/TCP
```

- `http://192.168.1.yyy` — Open WebUI on the LAN
- `http://192.168.1.xxx:11434` — Ollama API on the LAN

---

## How Open WebUI Connects to Ollama (In-Cluster DNS)

This is worth calling out explicitly because it's the piece that tripped us up first.

You might be tempted to set `OLLAMA_BASE_URL` to the LAN IP that MetalLB assigns to the Ollama service. Don't. That creates a chicken-and-egg problem: MetalLB only assigns the IP *after* the service is deployed, but the deployment references the IP *before* it exists. On a fresh cluster, there's no IP to hardcode yet.

The fix is Kubernetes DNS. Every service in a cluster gets a DNS name within its namespace. We set:

```yaml
env:
- name: OLLAMA_BASE_URL
  value: "http://ollama-service:11434"
```

Kubernetes resolves `ollama-service` to the correct pod IP automatically — no LAN IP, no MetalLB address, no chicken-and-egg. The connection stays in-cluster and never touches the LAN at all.

The Ollama LoadBalancer IP that MetalLB assigns is still useful — but for *external* access from your other machines (more on that below), not for internal pod-to-pod communication.

---

## Tailscale Sidecar: Secure Remote HTTPS

The most interesting part of this setup is how remote access works. We're not opening firewall ports. We're not running a reverse proxy server. We're not managing certificates.

The Open WebUI pod runs a second container — a Tailscale sidecar:

```yaml
- name: ts-sidecar
  image: ghcr.io/tailscale/tailscale:latest
  env:
  - name: TS_USERSPACE
    value: "true"
  - name: TS_HOSTNAME
    value: "openwebui"
  - name: TS_KUBE_SECRET
    value: "tailscale"
  - name: TS_AUTHKEY
    valueFrom:
      secretKeyRef:
        name: tailscale-auth
        key: tskey
  - name: TS_SERVE_CONFIG
    value: /serve/serve.json
```

The sidecar registers itself on your Tailscale network as a machine named `openwebui`. Once registered, it's available at `openwebui.<your-tailnet>.ts.net` from any device on your tailnet.

The `TS_SERVE_CONFIG` environment variable points to a JSON file (mounted from a ConfigMap) that configures Tailscale Serve — an HTTPS reverse proxy built into the Tailscale client:

```json
{
  "TCP": {
    "443": { "HTTPS": true }
  },
  "Web": {
    "${TS_CERT_DOMAIN}:443": {
      "Handlers": {
        "/": { "Proxy": "http://127.0.0.1:8080" }
      }
    }
  }
}
```

This tells Tailscale to:
1. Listen on port 443 with TLS termination
2. Proxy all traffic to `http://127.0.0.1:8080` — which is the Open WebUI container in the same pod

Tailscale handles certificate issuance via LetsEncrypt automatically. No cert management, no browser warnings, no self-signed anything. You just get `https://openwebui.<your-tailnet>.ts.net` and it works.

**One requirement:** MagicDNS and HTTPS must be enabled in your Tailscale admin console (Admin → DNS → Enable MagicDNS + Enable HTTPS).

### State Persistence Across Restarts

The sidecar writes its Tailscale node state to a Kubernetes secret named `tailscale` (via `TS_KUBE_SECRET`). When the pod restarts — whether for a rollout, an OOM kill, or a node reboot — the sidecar reads that state and re-registers as `openwebui` on your tailnet without consuming a new auth key. The URL stays the same. You don't have to do anything.

---

## The Shared Ollama Backend

The Ollama service is exposed externally on port 11434 by design. Once you have the LAN IP from MetalLB, every machine on your network can reach it:

**VSCode + Continue plugin** — point Continue at the Ollama LoadBalancer IP:
```json
{
  "models": [{
    "provider": "ollama",
    "model": "qwen2.5-coder:14b",
    "apiBase": "http://192.168.1.xxx:11434"
  }]
}
```

**Python scripts or notebooks:**
```python
import ollama
client = ollama.Client(host="http://192.168.1.xxx:11434")
response = client.chat(model="llama3.2", messages=[...])
```

**Ollama CLI from any machine:**
```bash
OLLAMA_HOST=http://192.168.1.xxx:11434 ollama pull llama3.2
OLLAMA_HOST=http://192.168.1.xxx:11434 ollama run qwen2.5-coder:14b
```

You ran Ollama locally in Part 1. This is the same thing, but now a single instance serves every tool on your network and restarts automatically if anything goes wrong.

---

## Day-2 Operations

**Check pod status:**
```bash
microk8s kubectl get pods -n open-webui
```

**View Open WebUI logs:**
```bash
microk8s kubectl logs -n open-webui deploy/open-webui-deployment -c open-webui
```

**View Tailscale sidecar logs:**
```bash
microk8s kubectl logs -n open-webui deploy/open-webui-deployment -c ts-sidecar
```

**Confirm Tailscale Serve is active inside the pod:**
```bash
microk8s kubectl exec -n open-webui deploy/open-webui-deployment -c ts-sidecar \
  -- tailscale serve status
```

**Restart Open WebUI after a config change:**
```bash
microk8s kubectl rollout restart deployment/open-webui-deployment -n open-webui
```

### Rotating the Tailscale Auth Key

Auth keys from Tailscale expire. When yours expires, update the secret in place — don't delete and recreate it — so you don't lose the accumulated Tailscale node state:

```bash
# Generate a new reusable key at https://login.tailscale.com/admin/settings/keys
microk8s kubectl create secret generic tailscale-auth \
  --from-literal=tskey=<new-key> \
  -n open-webui --dry-run=client -o yaml | \
  microk8s kubectl apply -f -

microk8s kubectl rollout restart deployment/open-webui-deployment -n open-webui
```

The `--dry-run=client -o yaml | kubectl apply` pattern updates the secret without deleting it. Because the `tailscale` state secret still exists, the sidecar re-registers as `openwebui` with the new key and retains its identity on the tailnet.

---

## Summary

| What | How |
|------|-----|
| Open WebUI chat UI (LAN) | MetalLB LoadBalancer on port 80 |
| Open WebUI (remote, HTTPS) | Tailscale sidecar — `https://openwebui.<tailnet>.ts.net` |
| Ollama (in-cluster) | In-cluster DNS `http://ollama-service:11434` |
| Ollama (LAN tools) | MetalLB LoadBalancer on port 11434 |
| GPU acceleration | Kustomize overlay — `kubectl apply -k kubernetes/manifest/gpu/` |
| Persistence | 300Gi PVC for Ollama models, 2Gi PVC for Open WebUI data |
| Remote access security | Tailscale MagicDNS + LetsEncrypt — no open ports required |

This is a setup that's genuinely been running day-to-day: Open WebUI for chat, the Continue plugin in VSCode using the same Ollama backend for coding, Python notebooks querying it directly. Kubernetes keeps it up without babysitting it.

The manifests are in the [open-webui](https://github.com/open-webui/open-webui) repository under `kubernetes/manifest/`. If you're picking this up from Part 1 and still have Ollama running as a bare process, this is the natural next step.

---

*Have questions or run into something that isn't covered here? Drop a comment below.*
