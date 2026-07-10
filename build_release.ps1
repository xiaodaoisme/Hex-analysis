param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# Build a single-file windowed executable; PyInstaller is only needed on the build machine.
if (Test-Path "build") {
    Remove-Item -Recurse -Force -ErrorAction Stop "build"
}
if (Test-Path "HexViewer.spec") {
    Remove-Item -Force -ErrorAction Stop "HexViewer.spec"
}
if (Test-Path "dist\HexViewer.exe") {
    Remove-Item -Force -ErrorAction Stop "dist\HexViewer.exe"
}
& $Python -OO -m PyInstaller --clean --noconfirm --windowed --onefile --name HexViewer app.py
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

if (-not (Test-Path "dist\HexViewer.exe")) {
    throw "dist\HexViewer.exe was not created."
}

# Keep the release directory clean; build intermediates are reproducible.
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build
Remove-Item -Force -ErrorAction SilentlyContinue HexViewer.spec

Write-Host "Release build created: dist\HexViewer.exe"
