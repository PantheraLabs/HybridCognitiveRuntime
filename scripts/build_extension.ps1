#!/usr/bin/env powershell
# HCR VS Code Extension Build Script

$ErrorActionPreference = "Stop"
$ExtensionDir = "$PSScriptRoot\product\vscode-extension"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  HCR VS Code Extension Builder" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

if (!(Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "npm not found. Please install Node.js from https://nodejs.org/"
    exit 1
}

# Navigate to extension directory
Set-Location $ExtensionDir

# Install dependencies
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow
npm install

# Compile TypeScript
Write-Host ""
Write-Host "Compiling TypeScript..." -ForegroundColor Yellow
npm run compile

if ($LASTEXITCODE -ne 0) {
    Write-Error "TypeScript compilation failed!"
    exit 1
}

Write-Host "✅ Compilation successful!" -ForegroundColor Green

# Check for vsce
Write-Host ""
Write-Host "Checking vsce..." -ForegroundColor Yellow
$VsceInstalled = $false
try {
    $vsceVersion = npx vsce --version 2>$null
    if ($vsceVersion) {
        $VsceInstalled = $true
        Write-Host "✅ vsce found: $vsceVersion" -ForegroundColor Green
    }
} catch {
    $VsceInstalled = $false
}

if (!$VsceInstalled) {
    Write-Host "Installing vsce..." -ForegroundColor Yellow
    npm install -g vsce
}

# Package extension
Write-Host ""
Write-Host "Packaging extension..." -ForegroundColor Yellow
npx vsce package --no-yarn

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "  ✅ Extension packaged successfully!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    
    # Find the .vsix file
    $VsixFile = Get-ChildItem -Filter "*.vsix" | Select-Object -First 1
    if ($VsixFile) {
        Write-Host ""
        Write-Host "Package location: $($VsixFile.FullName)" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "To install locally:" -ForegroundColor White
        Write-Host "  code --install-extension $($VsixFile.Name)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "To publish to marketplace:" -ForegroundColor White
        Write-Host "  1. Get Personal Access Token from https://dev.azure.com" -ForegroundColor Gray
        Write-Host "  2. vsce login pantheralabs" -ForegroundColor Gray
        Write-Host "  3. vsce publish" -ForegroundColor Gray
    }
} else {
    Write-Error "Packaging failed!"
    exit 1
}

Set-Location $PSScriptRoot
