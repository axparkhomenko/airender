$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI not found. Install and start Docker Desktop first."
}
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is not running. Start Docker Desktop and retry."
}

if (-not (Test-Path ".env")) {
    function New-Secret([string]$prefix) {
        $bytes = New-Object byte[] 32
        $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
        try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
        $hex = ([BitConverter]::ToString($bytes) -replace "-", "").ToLowerInvariant()
        return $prefix + $hex
    }
    $lines = @(
        "LITELLM_MASTER_KEY=$(New-Secret 'sk-airender-')"
        "LITELLM_SALT_KEY=$(New-Secret 'sk-salt-airender-')"
        "WEBUI_SECRET_KEY=$(New-Secret '')"
        "OPENWEBUI_PORT=3334"
        "LITELLM_PORT=4001"
        "OLLAMA_PORT=11435"
        "AIR_RENDER_API_PORT=8765"
    )
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines((Join-Path $repoRoot ".env"), $lines, $utf8NoBom)
    Write-Host "Created .env with fresh local secrets."
} else {
    Write-Host "Existing .env found; leaving your secrets unchanged."
}

docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    throw "docker compose failed. Inspect the output above and run: docker compose logs"
}
Write-Host ""
Write-Host "Airender stack started. Open OpenWebUI at http://localhost:3334"
Write-Host "First startup downloads qwen2.5:7b; monitor with: docker compose logs -f ollama-model-init"
