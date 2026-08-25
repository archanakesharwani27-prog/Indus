# INDUS Setup Script (install.ps1)
# Run this once to install all dependencies
# Usage: PowerShell -ExecutionPolicy Bypass -File install.ps1

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  INDUS AI Assistant — Dependency Installer" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Python packages
Write-Host "[1/4] Installing Python packages..." -ForegroundColor Yellow
pip install -r requirements.txt
if ( -ne 0) {
    Write-Host "  ERROR: pip install failed. Make sure Python 3.10+ and pip are installed." -ForegroundColor Red
    exit 1
}
Write-Host "  Done." -ForegroundColor Green

# 2. Playwright browsers
Write-Host ""
Write-Host "[2/4] Installing Playwright browsers (for browser_control tool)..." -ForegroundColor Yellow
python -m playwright install chromium
Write-Host "  Done." -ForegroundColor Green

# 3. Tesseract check
Write-Host ""
Write-Host "[3/4] Checking Tesseract-OCR..." -ForegroundColor Yellow
 = "C:\Program Files\Tesseract-OCR\tesseract.exe"
if (Test-Path ) {
    Write-Host "  Tesseract found at " -ForegroundColor Green
} else {
     = Get-Command tesseract -ErrorAction SilentlyContinue
    if () {
        Write-Host "  Tesseract found in PATH: " -ForegroundColor Green
    } else {
        Write-Host "  WARN: Tesseract not found." -ForegroundColor Yellow
        Write-Host "  Download from: https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Yellow
        Write-Host "  Vision OCR will not work without it." -ForegroundColor Yellow
    }
}

# 4. Config check
Write-Host ""
Write-Host "[4/4] Checking config/api_keys.json..." -ForegroundColor Yellow
 = Join-Path  "config\api_keys.json"
if (Test-Path ) {
    Write-Host "  Config file found." -ForegroundColor Green
} else {
    Write-Host "  Creating empty config/api_keys.json template..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path (Split-Path ) -Force | Out-Null
    '{"gemini_api_key": "PASTE_YOUR_KEY_HERE"}' | Set-Content -Path  -Encoding UTF8
    Write-Host "  Created. Edit config/api_keys.json and add your Gemini API key." -ForegroundColor Yellow
}

# 5. Final preflight
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Running preflight check..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
python scripts/preflight_check.py

Write-Host ""
Write-Host "Setup complete! Run INDUS with:" -ForegroundColor Green
Write-Host "  python main.py" -ForegroundColor White
Write-Host ""
