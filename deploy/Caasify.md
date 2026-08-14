# Deploying Apex AI on Caasify (free Docker hosting until Dec 2026)

Caasify runs your Dockerfile for free (no card) until December 31, 2026, with
persistent volumes, automatic TLS (https), and scale-to-zero. It's a good
card-free fit for Apex AI because your workspace files can persist.

## What you need

- A GitHub account (to connect the repo) — or you can push a pre-built image.
- Your API keys (Groq/Gemini) to paste as env vars.

## Step-by-step

### 1. Sign up
1. Go to https://my.caasify.com/register
2. Create an account (email + password; **no credit card required**).
3. Confirm your email.

### 2. Deploy the container
Caasify offers two ways — pick ONE:

**Option A — from GitHub (recommended):**
1. Dashboard → **Deploy** / **New container** → **Git**.
2. Connect your repo: `Davezeni/Apex-AI`.
3. It auto-detects the `Dockerfile` at the repo root.
4. Set the **port** to **8000** (or `$PORT` if it asks).

**Option B — pre-built image:**
1. Locally: `docker build -t apex-ai .` then push to Docker Hub / GHCR.
2. Caasify → **Deploy from registry** → enter the image name.

### 3. Set environment variables
Add these in the container's **Environment / Secrets** section:

```
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AQ...
ENABLE_OLLAMA=false
STORE_BACKEND=supabase          # optional — persistent memory
SUPABASE_URL=https://ezmxrmxvrklrifnxbzhh.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...   # optional
```

### 4. Attach a persistent volume (important!)
So your workspace + SQLite survive restarts and scale-to-zero wakes:
1. Container settings → **Volumes / Storage**.
2. Add a volume mounted at **`/app/workspace`** (and another at **`/app/data`**
   if it lets you add two).

> If Caasify only allows one volume, mount it at `/app` — but then the built
> frontend may be overwritten. Prefer two volumes (`/app/workspace`, `/app/data`).

### 5. Deploy + open
1. Click **Deploy** and wait ~1–2 min for the build.
2. Caasify gives you a URL like `https://apex-ai.caasify.app`.
3. Open it on your phone.

## Rebuilding after code changes

- **Git method**: push to GitHub → Caasify rebuilds (if auto-deploy is on), or
  click **Redeploy** in the dashboard.
- **Registry method**: rebuild + push the image, then redeploy.

## Honest caveats

- **Free ends Dec 31, 2026** — after that it's usage-based (a small app is
  roughly €2–5/mo). Mark your calendar.
- **Scale-to-zero** — idle containers may cold-start on first request (a short
  wait). Keep the app warm by visiting it occasionally.
- **No local Ollama** — Caasify free isn't suited to a big local model; use
  your hosted Groq/Gemini keys (set `ENABLE_OLLAMA=false`).
- **Docker sandbox** (`run_command`) — Caasify runs *your* app container, but
  the sandbox profile (Docker-in-Docker) may not be available. Static preview
  works regardless; server-side code execution depends on the platform.
