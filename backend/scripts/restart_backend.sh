#!/bin/bash
# Restart the backend (and the llama-server it owns). Usage: scripts/restart_backend.sh [--fresh-db]
cd "$(dirname "$0")/.."
powershell -NoProfile -Command "\$p=(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select -First 1).OwningProcess; if (\$p) { Stop-Process -Id \$p -Force }; Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force"
sleep 3
[ "$1" == "--fresh-db" ] && rm -f data/resolvyn.db data/resolvyn.db-wal data/resolvyn.db-shm
(nohup ./.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000 > ../backend_run.log 2>&1 &)
for i in $(seq 1 40); do
  sleep 1
  if curl -s localhost:8000/health | grep -q '"llm_ready":true'; then echo "backend ready ($i s)"; exit 0; fi
done
echo "backend not ready in 40s"; tail -20 ../backend_run.log
