# Deploying Apex AI on SnapDeploy (free, no card)

SnapDeploy's free tier: 4 containers, no credit card, auto-build from GitHub,
free SSL, custom subdomains. **Caveat:** free containers auto-sleep after ~15
min idle and take ~60s to wake; WebSockets need a paid Always-On plan.

## ⚠️ Important limitation for Apex AI

Apex AI's chat streams over **WebSockets** (`/ws/chat`), which SnapDeploy's
**free tier does NOT support** (WebSockets are listed under Always-On/paid).

- The app still works on free SnapDeploy via the **HTTP fallback** (`/api/chat`
  returns the full answer in one response, no streaming).
- If you want **streaming chat**, you'd need SnapDeploy Always-On (from
  $12/mo) — or use Render/Caasify for streaming instead.

## Step-by-step

### 1. Sign up
1. Go to https://snapdeploy.dev/register
2. Create an account (email + password; **no credit card**).

### 2. Connect GitHub + deploy
1. Dashboard → **New App** / **Deploy**.
2. Choose **GitHub** → authorize → select `Davezeni/Apex-AI`.
3. SnapDeploy detects the `Dockerfile` at the repo root and builds it.
4. Set the **port** to **8000**.

### 3. Environment variables
Add:
```
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AQ...
ENABLE_OLLAMA=false
```
(Optional, for persistent memory): `STORE_BACKEND=supabase`,
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

### 4. Persistent storage
SnapDeploy free is **ephemeral** (no persistent disk on the free tier). Your
workspace + SQLite reset when the container sleeps/wakes or redeploys. So:
- Use **Supabase** (`STORE_BACKEND=supabase`) for memory — survives.
- The workspace files themselves will reset on sleep — acceptable for testing;
  for persistence use Caasify (has volumes) or a VM.

### 5. Open
SnapDeploy gives you a `https://yourapp.snapdeploy.app` (or similar) URL.
Open it on your phone.

## Honest verdict vs. your other options

| | SnapDeploy free | Caasify free | Render free |
|---|---|---|---|
| No card | ✅ | ✅ | ✅ |
| Docker | ✅ | ✅ | ❌ |
| Persistent files | ❌ | ✅ | ❌ (Supabase for memory) |
| WebSockets | ❌ (paid) | ⚠️ | ✅ |
| Wake time | ~60s | ~10-30s | ~30-50s |

**Bottom line:** SnapDeploy is fine for *testing* Apex AI's Docker build, but
its free tier (no WebSockets, no persistent disk, slow wake) is the weakest of
your three card-free options for Apex AI specifically. Caasify (persistent
volumes) or Render (WebSockets) fit better.

## Rebuilding after code changes
Push to GitHub → SnapDeploy auto-rebuilds (or click **Redeploy**).
