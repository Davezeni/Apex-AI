# Deploying Apex AI — auto-deploy on every push

You want: **commit + push to GitHub → Render redeploys automatically.** Two ways
to get it. Use Method 1 (simplest — no extra permissions needed).

---

## Method 1 (recommended): Render's native auto-deploy

This works out of the box once your service is connected to GitHub.

1. On [render.com](https://render.com), open your service (`apex-ai-kbn9`).
2. Go to **Settings → Build & Deploy**.
3. Set **Auto-Deploy** to **Yes**.
4. Under **Repo**, confirm the service is connected to `Davezeni/Apex-AI`
   (branch `main`). If it shows "Not connected," click **Connect** and pick the
   repo.

After that, **every push to `main` triggers an automatic redeploy.** No GitHub
Action, no extra token permissions, nothing else to do.

> If you originally created the service *without* connecting a repo, the
> simplest fix is to delete it and create a new **Web Service → connect
> Davezeni/Apex-AI** (Render will read the code + `requirements.txt`). Or use
> Method 2 below, which works even without a Git connection.

---

## Method 2: GitHub Actions deploy hook (works even if not Git-connected)

There's a ready-made workflow at `.github/workflows/deploy.yml`. To use it you
need two things (because pushing workflow files requires the `workflow` scope):

1. **Add `workflow` permission to your token:**
   GitHub → Settings → Developer settings → Fine-grained tokens → your token →
   **Permissions → Workflows → Read and write**.
2. **Create a Render deploy hook:**
   Render → service → **Settings → Deploy Hook → Create** → copy the URL.
3. **Add it as a GitHub secret** named `RENDER_DEPLOY_HOOK`
   (repo → Settings → Secrets and variables → Actions → New repository secret).
4. Un-ignore and commit `.github/workflows/deploy.yml` (currently gitignored).

---

## One caveat

Free-tier Render services **sleep after ~15 min idle** and the filesystem is
**ephemeral** (resets on redeploy). For 24/7 + persistence, later move to a free
VM (Oracle Always Free).
