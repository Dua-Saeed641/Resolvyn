<#
  Download what the epsilon engine needs to serve Resolvyn (Windows, NVIDIA GPU):

    .\download_models.ps1              llama.cpp (CUDA 12.4 build) + Qwen3.5-4B (live tier)
    .\download_models.ps1 -Deep        ...and Qwen3.8-27B IQ2_XXS (deep tier, ~9 GB)
    .\download_models.ps1 -Deep -Quant Q4_K_M   a bigger 27B quant (needs >16 GB free RAM; not recommended here)

  Files land in engine\bin (llama-server.exe + DLLs) and engine\models.
#>
param([switch]$Deep, [string]$Quant = "IQ2_XXS", [string]$LlamaBuild = "b11163")

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$bin = Join-Path $here "bin"
$models = Join-Path $here "models"
New-Item -ItemType Directory -Force $bin, $models | Out-Null

function Get-File($url, $dest) {
    if (Test-Path $dest) { Write-Host "  have $(Split-Path $dest -Leaf)"; return }
    Write-Host "  downloading $(Split-Path $dest -Leaf) ..."
    # curl.exe resumes (-C -) and follows redirects; much sturdier than Invoke-WebRequest for multi-GB files
    & curl.exe -L --fail -C - -o $dest $url
    if ($LASTEXITCODE -ne 0) { throw "download failed: $url" }
}

# 1. modern llama.cpp: Qwen3.5 / Qwen3.8 use the Gated-DeltaNet hybrid architecture, which the
#    BitNet-era build in engine\BitNet cannot load.
if (-not (Test-Path (Join-Path $bin "llama-server.exe"))) {
    $base = "https://github.com/ggml-org/llama.cpp/releases/download/$LlamaBuild"
    Get-File "$base/llama-$LlamaBuild-bin-win-cuda-12.4-x64.zip" (Join-Path $bin "llama.zip")
    Get-File "$base/cudart-llama-bin-win-cuda-12.4-x64.zip" (Join-Path $bin "cudart.zip")
    Expand-Archive (Join-Path $bin "llama.zip") $bin -Force
    Expand-Archive (Join-Path $bin "cudart.zip") $bin -Force
    Remove-Item (Join-Path $bin "llama.zip"), (Join-Path $bin "cudart.zip")
}

# 2. live tier: 4B fits fully in 4 GB of VRAM
Get-File "https://huggingface.co/bartowski/Qwen_Qwen3.5-4B-GGUF/resolve/main/Qwen_Qwen3.5-4B-Q4_K_M.gguf" (Join-Path $models "Qwen_Qwen3.5-4B-Q4_K_M.gguf")

# 3. deep tier: 27B on CPU/RAM, background analysis only
if ($Deep) {
    $file = "Qwen3.8-27B-$Quant.gguf"
    Get-File "https://huggingface.co/bartowski/Qwen3.8-27B-GGUF/resolve/main/$file" (Join-Path $models $file)
    if ($Quant -ne "IQ2_XXS") { Write-Host "  remember to point models.deep.path in config.resolvyn.yaml at $file" }
}
Write-Host "done."
