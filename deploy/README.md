# Deploying Apex AI on Oracle Always Free VM (24/7, free)

This gets Apex AI running **always-on** with Docker, so:
- The app never sleeps (unlike Render free).
- Files persist on the VM's disk (no more ephemeral-filesystem wipes).
- The Docker sandbox can actually run the code the agent builds.

## Why Oracle Always Free

Oracle's Always Free tier gives a VM with **4 ARM cores + 24 GB RAM** — enough to
run Apex AI *and* a local Ollama model — permanently free. (Note: this is the
**Always Free VM**, NOT the paid "AI Data Platform".)

## One-time VM setup (~15 min)

1. Sign up at [oracle.com/cloud/free](https://www.oracle.com/cloud/free/) (credit
   card required for identity, but you are NOT charged on Always Free).
2. Create an instance: **Compute → Instances → Create instance**.
   - Image: **Ubuntu 22.04** (or Oracle Linux).
   - Shape: **VM.Standard.A1.Flex**, 4 OCPUs, 24 GB RAM (all Always Free).
   - Generate + download an **SSH key** (or use an existing one).
3. Open **port 8000** in the subnet's **security list** (Ingress → TCP 8000 from
   0.0.0.0/0). Port 22 (SSH) is open by default.

## Deploy Apex AI

From your computer, SSH into the VM and run:

```bash
ssh ubuntu@<VM_PUBLIC_IP>

# Install Docker + Compose (one-liner, Ubuntu)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# (log out and back in, or use `newgrp docker`)

# Clone and configure
git clone https://github.com/Davezeni/Apex-AI.git
cd Apex-AI
cp .env.example .env
nano .env   # paste GROQ_API_KEY, GEMINI_API_KEY, GITHUB_TOKEN, and
            # STORE_BACKEND=supabase + SUPABASE_URL/SERVICE_ROLE_KEY if using it

# Build + start (app + ollama + sandbox)
docker compose --profile ollama --profile sandbox up -d --build

# Pull a local model for the unlimited fallback
docker exec apex-ollama ollama pull qwen2.5:14b
```

Then open **http://<VM_PUBLIC_IP>:8000** on your phone. That's it.

## Rebuilding after I push code

```bash
cd Apex-AI
git pull
docker compose --profile ollama --profile sandbox up -d --build
```

## Notes / caveats (honest)

- **No HTTPS**: port 8000 is plain HTTP. Fine for personal use on an IP. For a
  domain + TLS, add Caddy/nginx later (I can add a config).
- **Sandbox uses Docker-in-Docker**: on ARM it works but the sandbox container
  needs `privileged: true` on some hosts; if `run_command` fails, tell me and
  I'll adjust `docker-compose.yml`.
- **ARM architecture**: all images (Python, Node, Ollama) are multi-arch, so
  this works on Oracle's ARM shape.
- **Ollama on ARM**: some models are slower on ARM without GPU, but Qwen 14B
  runs fine for fallback.
- **Persistence**: workspace + SQLite live in `./workspace` and `./data` on the
  VM disk — they survive restarts. Supabase (optional) adds cross-host memory.

## Free VM alternatives

If Oracle's signup fights you, the same steps work on any Linux VM:
- **Hetzner** (~$4/mo, cheapest reliable paid)
- **Google Cloud e2-micro** (free but only 1 GB RAM — no local model, use
  hosted keys only)
