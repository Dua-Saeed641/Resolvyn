<#
  Stop Resolvyn: the API (which owns the llama-server processes) and the web UI.
#>
param([switch]$Quiet)

foreach ($port in 8000, 3000) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
# llama-server children normally exit with the API; make sure no orphan keeps the GPU/RAM.
Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
if (-not $Quiet) { Write-Host "[resolvyn] stopped" -ForegroundColor Cyan }
