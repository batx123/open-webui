# LLM Observability on Kubernetes: Self-Hosted Tracing with Langfuse and Open WebUI Pipelines

*Part 4 of a series on self-hosted AI infrastructure. [Part 1](https://medium.com/@ben.gordy/deploy-and-configure-ollama-for-chat-and-agentic-ai-coding-d518242db386) covered deploying Ollama. [Part 2](https://medium.com/@ben.gordy/running-ollama-open-webui-on-kubernetes-gpu-support-tailscale-remote-access-and-a-shared-llm-backend) moved everything onto Kubernetes with GPU support and Tailscale remote access. [Part 3](https://medium.com/@ben.gordy/running-a-gpu-accelerated-tts-api-on-kubernetes-with-open-webui-integration-d77e5d716733) added a GPU-accelerated TTS engine and voice cloning.*

---

Somewhere around the third time you reboot your home lab server and come back to find Open WebUI serving a six-month-old version of itself, you start to wonder why you're running Kubernetes at all.

That was the starting point for this one. The pods were up. The URLs worked. But the images were stale because `imagePullPolicy` had defaulted to `IfNotPresent` on a tag that gets rebuilt daily, and nothing was pulling updates unless you physically restarted the node. Not exactly the self-managing infrastructure the brochure promised.

Fixing that took about five minutes. What came next took longer — and turned out to be more interesting.

Once images were actually updating on restart, the obvious next question was: *what is this thing doing?* You send it a message. It responds. But you have no idea how long the inference took, how many tokens were used, what the full prompt looked like after system context was injected, or whether the model is getting slower as context grows. The stack was running. It was just opaque.

This post adds observability. Specifically: [Langfuse](https://langfuse.com/) — an open-source LLM tracing platform — deployed in-cluster alongside the Open WebUI Pipelines service that acts as the middleware between your chat UI and the tracer. By the end, every conversation that goes through Open WebUI will generate a trace in Langfuse with the full prompt, response, model name, latency, and token counts. All local. No SaaS. No sending your conversations anywhere.

---

## What We're Building

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         open-webui namespace                            │
│                                                                         │
│  Browser ──► ts-sidecar (Tailscale :443) ──► open-webui (:8080)         │
│                                                    │                    │
│                                          pipelines-service (:9099)      │
│                                          (Langfuse filter installed)    │
└────────────────────────────────────────────────────┼────────────────────┘
                                                     │  in-cluster DNS
                                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          langfuse namespace                             │
│                                                                         │
│  Browser ──► ts-sidecar (Tailscale :443) ──► langfuse (:3000)           │
│                                                    │                    │
│                                            postgres-service (:5432)     │
│                                            10Gi PVC (trace storage)     │
└─────────────────────────────────────────────────────────────────────────┘
```

Langfuse runs in its own namespace with a dedicated Postgres instance for trace storage. It gets its own Tailscale sidecar so you can reach the UI at `https://langfuse.<your-tailnet>.ts.net`. The Open WebUI Pipelines service runs in the `open-webui` namespace alongside the existing stack and communicates with Langfuse via in-cluster DNS — no traffic leaves the cluster.

The data flow on every chat message: Open WebUI → Pipelines (Langfuse filter intercepts) → Ollama → Pipelines (response captured) → Langfuse (trace stored) → Open WebUI (response rendered).

---

## Prerequisites

Everything from Parts 1–3 should be in place:

- **MicroK8s** running with `metallb`, `gpu`, `hostpath-storage` addons enabled
- **Open WebUI** deployed in the `open-webui` namespace with Ollama as the backend
- **Tailscale account** with MagicDNS and HTTPS enabled — you'll need a second auth key for the Langfuse sidecar

---

## Step 1: Fix imagePullPolicy (or: Why Your Stack Was Running Stale Images)

Before getting into observability, there was a more basic problem to fix. Open WebUI uses the `:main` tag — a mutable tag that gets rebuilt on every commit to the main branch. With `imagePullPolicy: IfNotPresent` (the default for non-`:latest` tags), Kubernetes never checks for a newer image once one is cached on the node. Reboot the server, pod restarts, same old image.

The fix is one line per container:

```yaml
- name: open-webui
  image: ghcr.io/open-webui/open-webui:main
  imagePullPolicy: Always
```

`Always` doesn't mean "re-download the entire image on every restart." It means "contact the registry and compare the remote digest against the local cache." If the digest matches, nothing is downloaded. If it doesn't, only the changed layers are pulled. The overhead is a single registry API call, not a full image download.

The tradeoff: if the registry is unreachable when the pod starts (network hiccup, registry outage), the pod will fail rather than fall back to the cached image. For images from GitHub Container Registry over a home internet connection, this is rarely a problem. For images from a local registry — like the chatterbox images from Part 3 — `IfNotPresent` is still the right call.

Apply this to every container that tracks a mutable remote tag: `open-webui:main`, `tailscale:latest`, and `ollama:latest` in our case.

### Rolling Restarts Without Rebooting

Once `imagePullPolicy: Always` is in place, you no longer need to reboot the host to pick up new images. You just need to restart the pods:

```bash
# Apply the updated manifests first
microk8s kubectl apply -k kubernetes/manifest/base/

# Then trigger rolling restarts
microk8s kubectl rollout restart deployment/open-webui-deployment -n open-webui
microk8s kubectl rollout restart statefulset/ollama -n open-webui

# Watch progress
microk8s kubectl rollout status deployment/open-webui-deployment -n open-webui
```

The Deployment does a true rolling restart — new pod comes up before the old one terminates, so Open WebUI stays available. The StatefulSet restarts in-place, so Ollama has a brief gap. With one replica, that's unavoidable.

To confirm the update landed:
```bash
microk8s kubectl describe pod -l app=open-webui -n open-webui | grep Image
```

---

## Step 2: Deploy Langfuse

Langfuse needs a namespace, a Postgres instance for persistence, the app itself, and a Tailscale sidecar for UI access.

### Secrets First

Two secrets must exist before anything else. Create the namespace, then the secrets:

```bash
microk8s kubectl create namespace langfuse
```

**Tailscale auth key** — get a new reusable key from https://login.tailscale.com/admin/settings/keys. Each Tailscale node needs its own key — you can't reuse the one from the `open-webui` namespace:

```bash
microk8s kubectl create secret generic tailscale-auth \
  --from-literal=tskey=<your-new-tailscale-auth-key> \
  -n langfuse
```

**Langfuse secrets** — create a file called `langfuse-secret.yaml` (add it to `.gitignore` before you do anything else):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: langfuse-secrets
  namespace: langfuse
type: Opaque
stringData:
  POSTGRES_USER: langfuse
  POSTGRES_PASSWORD: <your-db-password>
  DATABASE_URL: "postgresql://langfuse:<your-db-password>@postgres-service:5432/langfuse"
  NEXTAUTH_SECRET: <openssl rand -base64 32>
  SALT: <openssl rand -base64 32>   # must differ from NEXTAUTH_SECRET
  NEXTAUTH_URL: "https://langfuse.<your-tailnet>.ts.net"
```

Generate the random values:
```bash
openssl rand -base64 32   # for NEXTAUTH_SECRET
openssl rand -base64 32   # for SALT (run again, don't reuse)
```

Find your tailnet name with `tailscale status` or from https://login.tailscale.com/admin/dns.

Apply the secret:
```bash
microk8s kubectl apply -f langfuse-secret.yaml
```

### Deploy Postgres

Langfuse v2 needs Postgres. We use a `Recreate` strategy because the PVC is `ReadWriteOnce` — only one pod can mount it at a time.

```yaml
# postgres-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: langfuse
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        imagePullPolicy: IfNotPresent
        env:
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: langfuse-secrets
              key: POSTGRES_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: langfuse-secrets
              key: POSTGRES_PASSWORD
        - name: POSTGRES_DB
          value: langfuse
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-data
        persistentVolumeClaim:
          claimName: postgres-pvc
```

### Deploy Langfuse

The Langfuse deployment follows the same sidecar pattern as Open WebUI in Part 2 — the app runs alongside a Tailscale sidecar that proxies HTTPS traffic from your tailnet to the app container.

One non-obvious environment variable is required: `HOSTNAME: "0.0.0.0"`. More on why in the Lessons Learned section — but skip it and the pod will start, report itself as ready, and still refuse connections. Add it.

```yaml
# langfuse-deployment.yaml (relevant env section)
env:
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: langfuse-secrets
      key: DATABASE_URL
- name: NEXTAUTH_SECRET
  valueFrom:
    secretKeyRef:
      name: langfuse-secrets
      key: NEXTAUTH_SECRET
- name: SALT
  valueFrom:
    secretKeyRef:
      name: langfuse-secrets
      key: SALT
- name: NEXTAUTH_URL
  valueFrom:
    secretKeyRef:
      name: langfuse-secrets
      key: NEXTAUTH_URL
- name: PORT
  value: "3000"
- name: HOSTNAME
  value: "0.0.0.0"
```

The Tailscale serve config proxies port 443 → port 3000, matching Langfuse's default:

```json
{
  "TCP": { "443": { "HTTPS": true } },
  "Web": {
    "${TS_CERT_DOMAIN}:443": {
      "Handlers": { "/": { "Proxy": "http://127.0.0.1:3000" } }
    }
  }
}
```

Apply everything:

```bash
microk8s kubectl apply -k kubernetes/manifest/langfuse/
microk8s kubectl rollout status deployment/langfuse -n langfuse
microk8s kubectl rollout status deployment/postgres -n langfuse
```

Once the pods are up, open `https://langfuse.<your-tailnet>.ts.net`. You'll be walked through creating an organization and a project. Do that now — you'll need the API keys from the project in Step 4.

---

## Step 3: Deploy the Pipelines Service

Here's where the architecture gets slightly non-obvious. Langfuse integration in Open WebUI does **not** work as a direct connection. There's no "enter your Langfuse URL here" field in Open WebUI's settings. The integration goes through [Open WebUI Pipelines](https://github.com/open-webui/pipelines) — a separate Python service that acts as middleware between Open WebUI and any backend you want to instrument.

The Pipelines service is lightweight: a FastAPI server that Open WebUI treats as an OpenAI-compatible endpoint. You install "pipeline" scripts into it — Python files that intercept requests, do something (log to Langfuse, rate-limit, filter), and pass them along. No database required. Just a PVC to persist the installed pipeline scripts across restarts.

```bash
# Generate an API key for Open WebUI to authenticate with the Pipelines service
openssl rand -hex 32
```

Save that key — you'll need it twice: once in the Kubernetes secret, once in the Open WebUI admin panel.

The deployment lives in the `open-webui` namespace so it can communicate with Open WebUI via in-cluster DNS:

```yaml
# pipelines-deployment.yaml (key parts)
- name: pipelines
  image: ghcr.io/open-webui/pipelines:main
  imagePullPolicy: Always
  env:
  - name: PIPELINES_API_KEY
    valueFrom:
      secretKeyRef:
        name: pipelines-secret
        key: PIPELINES_API_KEY
  ports:
  - containerPort: 9099
  volumeMounts:
  - name: pipelines-data
    mountPath: /app/pipelines
```

Apply:

```bash
microk8s kubectl apply -k kubernetes/manifest/base/
microk8s kubectl rollout status deployment/pipelines -n open-webui
```

---

## Step 4: Connect Pipelines to Open WebUI

This step has a specific pitfall: the Pipelines server URL is not configured in the Pipelines settings page. It's registered as an OpenAI-compatible API connection, and Open WebUI detects it as a Pipelines server from there.

In Open WebUI:

1. **Admin Panel → Settings → Connections**
2. Under **OpenAI API**, click **+** to add a new connection
3. URL: `http://pipelines-service:9099`
4. Key: the hex string you generated in Step 3
5. Save

Now navigate to **Admin Panel → Settings → Pipelines**. The page that previously showed "Pipelines Not Detected" will now show a dropdown with `http://pipelines-service:9099` selected. That's the confirmation — Pipelines is connected.

---

## Step 5: Install and Configure the Langfuse Filter

With Pipelines connected, you can install the Langfuse filter directly from the Pipelines management page:

1. In the **Install from GitHub URL** field, paste:
   ```
   https://github.com/open-webui/pipelines/blob/main/examples/filters/langfuse_filter_pipeline.py
   ```
2. Click the install button

The filter downloads and installs into the Pipelines service's PVC. It will appear in the pipeline list below the install form.

Select the Langfuse filter and fill in the **valves** (the filter's configuration):

- **Secret Key**: `sk-lf-...` (from your Langfuse project → Settings → API Keys)
- **Public Key**: `pk-lf-...` (same place)
- **Host**: `http://langfuse-service.langfuse.svc.cluster.local:3000`

Note the host URL: in-cluster DNS, not the Tailscale URL. Traffic from Pipelines to Langfuse never leaves the cluster.

Save. Send a chat message in Open WebUI. Open Langfuse → **Traces**. Your conversation should appear within a few seconds with the full prompt, response, model name, latency breakdown, and token counts.

---

## Lessons Learned

### The HOSTNAME Environment Variable Will Betray You

Kubernetes automatically injects a `HOSTNAME` environment variable into every container, set to the pod name — something like `langfuse-7665b7db4b-dptvj`. Next.js 14 (which Langfuse v2 is built on) uses `HOSTNAME` to decide what network interface to bind to. If `HOSTNAME` is a pod name, Next.js resolves that name to the pod's cluster IP and binds to that IP only — not to `127.0.0.1`.

The Tailscale sidecar proxies to `127.0.0.1:3000`. If Next.js isn't listening on localhost, the proxy fails with `connection refused`. The Langfuse logs will say `✓ Ready in 4.9s`. The pod will show `2/2 Running`. Everything will look fine until you try to actually load the page and get nothing.

The fix: add `HOSTNAME: "0.0.0.0"` to your container env. This overrides the Kubernetes-injected value and tells Next.js to bind to all interfaces, including localhost. Add it. Don't learn this the hard way.

### Secrets Don't Hot-Reload

If you update a Kubernetes secret after a pod has already started, the pod continues using the values it loaded at startup. The updated secret is sitting there in etcd, visible if you `kubectl get secret`, but the running container doesn't see it.

This bit us when the `NEXTAUTH_URL` placeholder was still in the secret when the Langfuse pod first started. NextAuth failed to initialize. The pod restarted, failed again, restarted again — three restarts total — before the correct URL was in place and a fresh restart picked it up.

The rule: get your secrets right before the first `kubectl apply`. If you have to update a secret after the fact, follow it with `kubectl rollout restart` to force the pods to reload.

### Pipelines Is Not a Direct Connection

If you go looking for "Langfuse" in Open WebUI's Connections settings, you won't find it. The documentation mentions Langfuse integration, but the integration path goes through Pipelines — not through a dedicated Langfuse field.

The operational model is: Pipelines is a filter layer. Open WebUI sends every request through the Pipelines service (which you register as an OpenAI-compatible connection). The Langfuse filter pipeline intercepts the request, logs it, and passes it along. From Open WebUI's perspective, it's just talking to another OpenAI endpoint. The tracing happens invisibly.

This is actually a cleaner design once you understand it — the same Pipelines service can run multiple filters simultaneously (rate limiting, content filtering, logging) without Open WebUI needing to know about any of them. But the indirection isn't obvious at first.

### The Pipelines Settings Page Is Not Where You Set the URL

When you navigate to Admin Panel → Settings → Pipelines in Open WebUI, you'll see "Pipelines Not Detected" and a page for managing installed pipeline scripts. There is no URL field here.

The URL is set in **Connections**, under the OpenAI API section. Add `http://pipelines-service:9099` as an OpenAI-compatible endpoint with your Pipelines API key. Open WebUI detects that it's a Pipelines server (not a real OpenAI endpoint) and populates the Pipelines management page. Only then can you install and manage pipeline scripts.

### imagePullPolicy: Always vs. IfNotPresent

Part 3 recommended `IfNotPresent` for images stored in a local MicroK8s registry — and that's still the right call for local images. The local registry can be unreachable briefly after a node reboot, and `Always` will fail the pod rather than use the cached image.

For images pulled from remote registries like GitHub Container Registry, `Always` is the right call when you're tracking a mutable tag like `:main` or `:latest`. The overhead is one registry API call per pod start, not a full image download — Kubernetes only pulls layers that have actually changed.

The pattern: `IfNotPresent` for local registry images, `Always` for remote mutable tags.

---

## Day-2 Operations

**Update Open WebUI to the latest image:**
```bash
microk8s kubectl rollout restart deployment/open-webui-deployment -n open-webui
```

**Check all pods across relevant namespaces:**
```bash
microk8s kubectl get pods -n open-webui
microk8s kubectl get pods -n langfuse
```

**View Langfuse logs:**
```bash
microk8s kubectl logs -n langfuse deployment/langfuse -c langfuse --tail=50
```

**View Pipelines logs:**
```bash
microk8s kubectl logs -n open-webui deployment/pipelines --tail=30
```

**Verify Pipelines is receiving requests from Open WebUI:**
```bash
microk8s kubectl logs -n open-webui deployment/pipelines -f
# Send a chat message in Open WebUI — you should see GET/POST requests appear
```

**Restart Langfuse after a secret update:**
```bash
microk8s kubectl apply -f langfuse-secret.yaml
microk8s kubectl rollout restart deployment/langfuse -n langfuse
```

---

## The Stack So Far

Four posts in, here's the full picture:

| Part | What was added |
|------|----------------|
| 1 | Ollama running locally, wired into VSCode via the Continue plugin |
| 2 | Everything on Kubernetes — GPU acceleration, MetalLB LAN IPs, Tailscale HTTPS sidecar |
| 3 | GPU-accelerated TTS in its own namespace, custom voice cloning, Open WebUI audio integration |
| 4 | LLM tracing — Langfuse + Pipelines, every conversation traced with full prompt/response/latency |

The cluster now runs across four namespaces: `open-webui` (chat UI, Ollama, Pipelines), `chatterbox` (TTS), and `langfuse` (traces + Postgres). Everything communicates via in-cluster DNS. Nothing is exposed to the public internet. The only external surfaces are the two Tailscale nodes — one for Open WebUI, one for Langfuse — reachable only from devices on your tailnet.

The manifests for the Langfuse and Pipelines deployments are in the `kubernetes/manifest/` directory of the [open-webui repository](https://github.com/open-webui/open-webui) alongside the manifests from Parts 2 and 3.

---

*Have questions or ran into something that isn't covered here? Drop a comment below.*
