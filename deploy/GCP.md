# Deploying Apex AI on Google Cloud free VM (e2-micro)

Google's `e2-micro` VM is **permanently free** (1 per month, US regions only:
`us-east1`, `us-central1`, `us-west1`). It has **1 GB RAM**, which is enough to
run Apex AI with hosted models (Groq/Gemini) but NOT local Ollama — so we skip
Ollama on this host.

## 1. Create the VM (in the Google Cloud Console)

1. Open the **Console**: https://console.cloud.google.com
2. Top bar → **Create a project** (name it `apex-ai`), wait for it to appear.
3. Left menu → **Compute Engine → VM instances** → **Create instance**.
4. Configure:
   - **Name**: `apex-ai`
   - **Region/Zone**: pick one with `us-east1`, `us-central1`, or `us-west1`
     (REQUIRED for free tier).
   - **Machine type**: `e2-micro` (must be this exact type for free).
   - **Boot disk** → Change → **Ubuntu 22.04 LTS**, size 30 GB.
   - **Firewall**: check ✅ **Allow HTTP traffic** and ✅ **Allow HTTPS traffic**.
5. Click **Create**.

## 2. Open the app port (8000)

By default only 80/443 are open. Add 8000:

1. Left menu → **VPC network → Firewall**.
2. **Create firewall rule**:
   - Name: `apex-8000`
   - Targets: **All instances in the network**
   - Source IP ranges: `0.0.0.0/0`
   - Protocols and ports → **TCP → 8000**
3. **Create**.

## 3. SSH in and deploy

In the VM list, click the **SSH** button next to `apex-ai` (opens a browser
terminal). Then run:

```bash
# Install Docker (Ubuntu one-liner)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Clone + configure
git clone https://github.com/Davezeni/Apex-AI.git
cd Apex-AI
cp .env.example .env
nano .env   # paste GROQ_API_KEY and GEMINI_API_KEY
            # set ENABLE_OLLAMA=false  (no local model on 1GB VM)
            # (optional) STORE_BACKEND=supabase + SUPABASE keys for persistence

# Build + run (NO ollama profile on this small VM)
docker compose up -d --build
```

Then open **http://<VM_EXTERNAL_IP>:8000** on your phone.

## 4. Rebuild after code changes

```bash
cd Apex-AI
git pull
docker compose up -d --build
```

## Honest caveats (1 GB RAM)

- **No local Ollama** — 1 GB is too small. The app uses your hosted Groq/Gemini
  keys instead. (`ENABLE_OLLAMA=false` avoids wasted failover to a dead local
  server.)
- **Memory is tight** — the app + a couple of models' request buffers fit, but
  avoid running the Docker sandbox profile on this VM (it needs extra RAM).
  Static preview still works (serves index.html); *server* preview (Docker
  sandbox) is the thing you give up on e2-micro.
- **Free-tier billing** — you get $300/90-day trial + the permanent free tier.
  As long as you only use ONE e2-micro in a US region and stay within limits,
  you are not charged. Set a **budget alert** (Billing → Budgets) so you get an
  email if anything would ever cost money.
- If you later get a physical card, **Hetzner (~$4/mo)** or the **Oracle Always
  Free VM (4 cores/24GB)** are strictly better (they can run Ollama + sandbox).

## Get your VM's public IP

Console → **Compute Engine → VM instances** → the **External IP** column is the
address to open on your phone.
