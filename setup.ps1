# Chess Roguelike - One-Time Setup Script
Write-Host ""
Write-Host "=== Chess Roguelike Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check and install Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Installing Python (you may need to click Allow)..." -ForegroundColor Yellow
    winget install Python.Python.3.13 --accept-package-agreements --accept-source-agreements --silent
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Python install failed. Install manually from https://python.org" -ForegroundColor Red
        Write-Host "  (Check 'Add to PATH' during install!)" -ForegroundColor Red
        pause; exit 1
    }
} else {
    Write-Host "Python already installed." -ForegroundColor Green
}

# Check and install Git
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Write-Host "Installing Git (you may need to click Allow)..." -ForegroundColor Yellow
    winget install Git.Git --accept-package-agreements --accept-source-agreements --silent
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Git install failed. Install manually from https://git-scm.com" -ForegroundColor Red
        pause; exit 1
    }
} else {
    Write-Host "Git already installed." -ForegroundColor Green
}

# Refresh PATH so we can use the newly installed tools
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Verify tools are available
$python = Get-Command python -ErrorAction SilentlyContinue
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Python not found in PATH. Please restart your computer and run this again." -ForegroundColor Red
    pause; exit 1
}
if (-not $git) {
    Write-Host "Git not found in PATH. Please restart your computer and run this again." -ForegroundColor Red
    pause; exit 1
}

# Create game directory and clone
$gamePath = "C:\Games\ChessRoguelike"
Write-Host "Downloading game to $gamePath..." -ForegroundColor Cyan

if (Test-Path "$gamePath\.git") {
    Write-Host "Game already downloaded. Updating..." -ForegroundColor Yellow
    Set-Location $gamePath
    & git pull
} else {
    New-Item -ItemType Directory -Force -Path $gamePath | Out-Null
    Set-Location $gamePath
    & git clone https://github.com/marrichard/Chess.git .
}

# Install Python dependencies
Write-Host "Installing game dependencies..." -ForegroundColor Cyan
& python -m pip install -r requirements.txt --quiet

# Create desktop bat files
$desktop = [Environment]::GetFolderPath("Desktop")

@"
@echo off
cd /d C:\Games\ChessRoguelike
python main.py
"@ | Set-Content "$desktop\Play Chess Roguelike.bat" -Encoding ASCII

@"
@echo off
echo Updating Chess Roguelike...
cd /d C:\Games\ChessRoguelike
git pull
python -m pip install -r requirements.txt --quiet
echo.
echo Updated! You can close this window and click Play.
pause
"@ | Set-Content "$desktop\Update Chess Roguelike.bat" -Encoding ASCII

Write-Host ""
Write-Host "=== Setup Complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Two files are on your desktop:" -ForegroundColor White
Write-Host "  Play Chess Roguelike.bat    - Double-click to play" -ForegroundColor White
Write-Host "  Update Chess Roguelike.bat  - Double-click when told to update" -ForegroundColor White
Write-Host ""
pause
