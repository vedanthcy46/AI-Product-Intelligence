# Production launcher for the UniHack dashboard (Windows).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File run_prod.ps1            # port 8000
#   powershell -ExecutionPolicy Bypass -File run_prod.ps1 -Port 8080
#
# Serves on all interfaces so other devices on the LAN can reach it.

param([int]$Port = 8000)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "=== UniHack dashboard (production mode) ===" -ForegroundColor Cyan

# 1. Environment sanity -----------------------------------------------------
if (-not (Test-Path ".env")) {
    Write-Warning ".env not found — LLM stages will silently degrade. "
    Write-Warning "Copy .env.example to .env and set GROQ_API_KEY first."
}

$master = "data\reference\UniCat_Manufacturer_and_Brand_List.xlsx"
if (-not (Test-Path $master)) {
    Write-Warning "Manufacturer master missing ($master) — entity resolution runs in pass-through mode."
}

# 2. Dependencies ------------------------------------------------------------
python -c "import waitress" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing waitress..." -ForegroundColor Yellow
    python -m pip install --quiet waitress
    if ($LASTEXITCODE -ne 0) { Write-Error "pip install waitress failed"; exit 1 }
}
python -c "import flask" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing flask..." -ForegroundColor Yellow
    python -m pip install --quiet flask
    if ($LASTEXITCODE -ne 0) { Write-Error "pip install flask failed"; exit 1 }
}

# 3. Show the URLs people can open -------------------------------------------
Write-Host ""
Write-Host "Serving on:" -ForegroundColor Green
Write-Host "  Local : http://localhost:$Port"
Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
    ForEach-Object { Write-Host ("  LAN   : http://{0}:{1}" -f $_.IPAddress, $Port) }

# First time only: open the firewall for inbound HTTP on this port.
$rule = Get-NetFirewallRule -DisplayName "UniHack $Port" -ErrorAction SilentlyContinue
if (-not $rule) {
    Write-Host ""
    Write-Host "Tip: allow LAN access with (admin):" -ForegroundColor DarkGray
    Write-Host "  netsh advfirewall firewall add rule name=""UniHack $Port"" dir=in action=allow protocol=TCP localport=$Port" -ForegroundColor DarkGray
}

# 4. Launch (single process — JOB state + JSON snapshots are per-process) ----
Write-Host ""
python -m waitress --host 0.0.0.0 --port $Port frontend.server:app
