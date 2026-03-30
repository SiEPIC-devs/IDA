# Build script for creating SiEPIC Probe Stage launcher executable
# Run from the project root OR from setup/ — both work.

param(
    [switch]$NoCopy   # Skip auto-copy to project root
)

$ErrorActionPreference = "Stop"

# ── Resolve paths ─────────────────────────────────────────────────
$ScriptDir   = $PSScriptRoot                          # …/setup
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$SpecFile    = Join-Path $ScriptDir "probe347.spec"
$BuildDir    = Join-Path $ProjectRoot "build"
$DistDir     = Join-Path $ProjectRoot "dist"

Write-Host "Project root : $ProjectRoot" -ForegroundColor Cyan
Write-Host "Spec file    : $SpecFile"    -ForegroundColor Cyan

# ── Ensure PyInstaller ────────────────────────────────────────────
try {
    $null = & python -m PyInstaller --version 2>&1
} catch {
    Write-Host "PyInstaller not found — installing..." -ForegroundColor Yellow
    pip install pyinstaller
}

# ── Clean previous artefacts ──────────────────────────────────────
foreach ($dir in @($BuildDir, $DistDir)) {
    if (Test-Path $dir) {
        Write-Host "Cleaning $dir ..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $dir
    }
}

# ── Build ─────────────────────────────────────────────────────────
Write-Host "`nRunning PyInstaller..." -ForegroundColor Green
Push-Location $ProjectRoot
try {
    python -m PyInstaller $SpecFile --distpath $DistDir --workpath $BuildDir
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller exited with code $LASTEXITCODE" }
} finally {
    Pop-Location
}

# ── Copy exe to project root ─────────────────────────────────────
$ExeName = "SiEPIC_ProbeStage.exe"
$ExeSrc  = Join-Path $DistDir $ExeName

if (Test-Path $ExeSrc) {
    Write-Host "`nBuild succeeded!" -ForegroundColor Green
    Write-Host "  -> $ExeSrc" -ForegroundColor Cyan

    if (-not $NoCopy) {
        $ExeDst = Join-Path $ProjectRoot $ExeName
        Copy-Item $ExeSrc $ExeDst -Force
        Write-Host "  -> Copied to $ExeDst" -ForegroundColor Cyan
        Write-Host "`nDouble-click  $ExeName  in the project folder to launch." -ForegroundColor Green
    }
} else {
    Write-Host "Build failed — executable not found!" -ForegroundColor Red
    exit 1
}