# Running Apex AI in GitHub Codespaces (phone-friendly)

You never install Docker or run anything locally. GitHub runs the whole stack
in a cloud container; you open a URL in your phone's browser.

## One-time setup

1. Open `github.com/Davezeni/Apex-AI` on your phone.
2. Tap **`<> Code` → Codespaces → Create codespace on main**.
3. Wait ~2 minutes. The container auto-installs Python deps + npm packages.

## Start the app

In the Codespace's built-in terminal:

```bash
cp .env.example .env        # paste your Groq/Gemini keys (optional)
bash .devcontainer/start.sh
```

Codespaces auto-forwards ports **8000** (backend) and **3000** (frontend).
Open the forwarded **3000** URL in your browser to use the app.

## Notes

- If you skip `.env`, the app falls back to local Ollama (you'd also need to
  `ollama pull qwen2.5:14b` inside the Codespace).
- For a 24/7 always-on instance, deploy to a free VM (Oracle Always Free)
  instead — Codespaces auto-stops after inactivity.
