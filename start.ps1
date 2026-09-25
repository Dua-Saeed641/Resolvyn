<#
  Start Resolvyn (backend + team/customer web UI).

    .\start.ps1            start both (installs what is missing on the first run)
    .\start.ps1 -Dev       run the frontend in dev mode instead of the production build
    .\start.ps1 -Fresh     wipe the local SQLite database first (seeds are re-created)
    .\start.ps1 -Tunnel    also open an ngrok tunnel so a phone can reach it (prints the public URLs)

  Backend  : http://localhost:8000   (FastAPI; loads Qwen through the epsilon engine in ./engine)
  Web UI   : http://localhost:3000   customer side      http://localhost:3000/ops   team side
#>
param([switch]$Dev, [switch]$Fresh, [switch]$Tunnel)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$engine = Join-Path $root "engine"

function Say($m) { Write-Host "[resolvyn] $m" -ForegroundColor Cyan }

# ── engine sanity ────────────────────────────────────────────────────────────
$server = Join-Path $engine "bin\llama-server.exe"
$fast = Join-Path $engine "models\Qwen_Qwen3.5-4B-Q4_K_M.gguf"
$deep = Join-Path $engine "models\Qwen3.8-27B-IQ2_XXS.gguf"
if (-not (Test-Path $server)) { Write-Warning "engine\bin\llama-server.exe is missing - see engine\README.md. The app still runs on the deterministic fallback." }
if (-not (Test-Path $fast)) { Write-Warning "Live model not found: $fast - see engine\README.md" }
if (-not (Test-Path $deep)) { Write-Host "[resolvyn] (optional) 27B deep-tier model not found; post-call deep analysis will be skipped." -ForegroundColor DarkGray }

# ── backend ──────────────────────────────────────────────────────────────────
$py = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Say "creating backend virtualenv (Python 3.11)..."
    py -3.11 -m venv (Join-Path $backend ".venv")
    & $py -m pip install -q --upgrade pip
    & $py -m pip install -q -r (Join-Path $backend "requirements.txt")
}
& $py -c "import langgraph" 2>$null
if ($LASTEXITCODE -ne 0) { Say "installing orchestration layer requirements..."; & $py -m pip install -q -r (Join-Path $root "agents\requirements.txt") }
if (-not (Test-Path (Join-Path $backend ".env"))) { Copy-Item (Join-Path $backend ".env.example") (Join-Path $backend ".env") }
if ($Fresh) { Remove-Item (Join-Path $backend "data\resolvyn.db*") -Force -ErrorAction SilentlyContinue; Say "database wiped" }

# ── frontend ─────────────────────────────────────────────────────────────────
if (-not (Test-Path (Join-Path $frontend "node_modules"))) { Say "installing frontend packages..."; Push-Location $frontend; npm install --no-audit --no-fund; Pop-Location }
if (-not (Test-Path (Join-Path $frontend ".env.local"))) { Copy-Item (Join-Path $frontend ".env.local.example") (Join-Path $frontend ".env.local") }
if (-not $Dev -and -not (Test-Path (Join-Path $frontend ".next\BUILD_ID"))) { Say "building the frontend (first run)..."; Push-Location $frontend; npm run build; Pop-Location }

# ── launch ───────────────────────────────────────────────────────────────────
& (Join-Path $root "stop.ps1") -Quiet
$publicUrl = $null
if ($Tunnel) {
    if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) { throw "ngrok not found. Install it and run: ngrok config add-authtoken <token>" }
    Say "opening ngrok tunnel to the web UI (port 3000)..."
    Start-Process -FilePath "ngrok" -ArgumentList "http", "3000" -WindowStyle Minimized
    for ($i = 0; $i -lt 20 -and -not $publicUrl; $i++) {
        Start-Sleep -Seconds 1
        try { $publicUrl = (Invoke-RestMethod http://127.0.0.1:4040/api/tunnels -TimeoutSec 2).tunnels | Where-Object { $_.public_url -like "https*" } | Select-Object -First 1 -ExpandProperty public_url } catch { }
    }
    if (-not $publicUrl) { Write-Warning "Could not read the ngrok URL (is your authtoken set?)" } else { $env:PUBLIC_BASE_URL = $publicUrl }
}
Say "starting backend (model load takes ~10 s)..."
Start-Process -FilePath $py -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8000" -WorkingDirectory $backend -WindowStyle Minimized
Say "starting web UI..."
$npmCmd = if ($Dev) { "run dev" } else { "run start" }
Start-Process -FilePath "npm.cmd" -ArgumentList $npmCmd -WorkingDirectory $frontend -WindowStyle Minimized

Say "waiting for the backend..."
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    try { $h = Invoke-RestMethod http://localhost:8000/health -TimeoutSec 2; if ($h.llm_ready) { break } } catch { }
}
Write-Host ""
Write-Host "  Customer side : http://localhost:3000" -ForegroundColor Green
Write-Host "  Team console  : http://localhost:3000/ops" -ForegroundColor Green
Write-Host "  API docs      : http://localhost:8000/docs"
if ($publicUrl) {
    Write-Host ""
    Write-Host "  PHONE (browser) : open $publicUrl on your phone, tap Call Riya" -ForegroundColor Yellow
    Write-Host "  PHONE (Twilio)  : voice webhook (POST) = $publicUrl/api/telephony/twilio/voice" -ForegroundColor Yellow
}
Write-Host "  Voice calls need Chrome or Edge (browser speech recognition). Use headphones."
Write-Host "  Stop everything with .\stop.ps1"
