<#
  🔑 ref.tools API Key Generator (Windows Installer)
  Usage:
    iwr -useb https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/install.ps1 | iex
#>

$ErrorActionPreference = "Stop"
$scriptUrl = "https://raw.githubusercontent.com/ashfaqmehmood/ref-tools-keygen/main/get_ref_key.py"

Write-Host ""
Write-Host "🔑 ref.tools API Key Generator" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

if (-not (Get-Command "python" -ErrorAction SilentlyContinue) -and -not (Get-Command "python3" -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python 3.8+ is required." -ForegroundColor Red
    exit 1
}

# Pick correct alias
$python = "python"
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    $python = "python3"
}

$KEEP_FILES = $env:KEEP_FILES
if (-not $KEEP_FILES) { $KEEP_FILES = "0" }

$tempRoot = Join-Path -Path ([System.IO.Path]::GetTempPath()) -ChildPath ("refkey_" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempRoot | Out-Null
$scriptPath = Join-Path $tempRoot "get_ref_key.py"

Write-Host "📥 Downloading Python script..."
Invoke-WebRequest -Uri $scriptUrl -OutFile $scriptPath -UseBasicParsing

Write-Host ""
Write-Host "🚀 Running key generator..."
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

$env:RTK_TEMP_ROOT = "$tempRoot\run"
$env:KEEP_FILES = $KEEP_FILES
& $python $scriptPath

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if ($KEEP_FILES -eq "1") {
    Write-Host "ℹ️  Keeping temp files at: $tempRoot"
} else {
    Write-Host ""
    Write-Host "🧹 Cleaning up..."
    Remove-Item -Recurse -Force $tempRoot
    Write-Host "✨ Done!"
}