#!/bin/sh
# One-command start for the Apex AI stack inside a Codespace.
# Runs backend (FastAPI) and frontend (Vite) in the background.
set -e

echo "Starting Apex AI backend on :8000 ..."
(cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!

echo "Starting Apex AI frontend on :3000 ..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "Apex AI is starting."
echo "  Backend : http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "Ports are auto-forwarded by Codespaces — open the forwarded URL on your phone."
echo "Press Ctrl+C to stop."
trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null' INT TERM
wait
