# Install dependencies one at a time to avoid npm install timeouts
# Run from: E:\Projects\stella\frontend
# Usage: powershell -ExecutionPolicy Bypass -File install-deps.ps1

$ErrorActionPreference = 'Continue'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

# List of packages to install (name@version)
# Order matters: install core framework first, then dependencies
$packages = @(
  # Core framework (must match versions)
  'react@^19.3.1',
  'react-dom@^19.3.1',
  'next@^16.4.5',
  
  # Motion & animations
  'motion@^14.10.1',
  
  # UI libraries
  'lucide-react@^1.70.0',
  'clsx@^2.1.1',
  'tailwind-merge@^3.7.0',
  'class-variance-authority@^0.7.1',
  
  # Forms
  '@hookform/resolvers@^7.0.5',
  
  # Styling
  'tailwindcss@^4.3.5',
  '@tailwindcss/postcss@^4.3.5',
  '@tailwindcss/typography@^0.5.20',
  'postcss@^8.5.32',
  'autoprefixer@^10.6.2',
  'tw-animate-css@^1.4.0',
  
  # Maps & location
  '@vis.gl/react-google-maps@^1.10.2',
  'canvas-confetti@^1.9.4',
  '@types/canvas-confetti@^1.9.0',
  'qrcode@^1.5.4',
  '@types/qrcode@^1.5.6',
  
  # AI
  '@google/genai@^3.0.0',
  
  # State management
  'zustand@^5.1.0',
  
  # Utilities
  'jsqr@^1.4.0',
  'uuid@^14.0.3',
  
  # Dev tools
  'typescript@^5.9.3',
  '@types/node@^26.6.6',
  '@types/react@^19.3.0',
  '@types/react-dom@^19.3.0',
  'eslint@^10.14.0',
  'eslint-config-next@^16.4.5',
  'oxlint@^1.92.0',
  'firebase-tools@^15.35.0',
)

$success = @()
$failed = @()

foreach ($pkg in $packages) {
  Write-Host "Installing $pkg ..." -ForegroundColor Cyan
  $result = npm install --save-dev $pkg 2>&1
  $exitCode = $LASTEXITCODE
  
  if ($exitCode -eq 0) {
    Write-Host "  OK: $pkg" -ForegroundColor Green
    $success += $pkg
  } else {
    Write-Host "  FAILED: $pkg" -ForegroundColor Red
    $failed += $pkg
  }
  Write-Host ""
}

Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Installation complete!" -ForegroundColor Yellow
Write-Host "Successful: $($success.Count)" -ForegroundColor Green
Write-Host "Failed: $($failed.Count)" -ForegroundColor Red

if ($failed.Count -gt 0) {
  Write-Host "Failed packages:" -ForegroundColor Red
  $failed | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
  exit 1
}
