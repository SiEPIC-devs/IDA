# Build script for creating executable with PyInstaller
# Run this from the project root directory

Write-Host "Building 347 Probe executable with PyInstaller..." -ForegroundColor Green

# Activate virtual environment if it exists
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    . .\venv\Scripts\Activate.ps1
} else {
    Write-Host "No virtual environment found at .\venv" -ForegroundColor Yellow
}

# Check if PyInstaller is installed
try {
    pyinstaller --version | Out-Null
} catch {
    Write-Host "PyInstaller not found. Installing..." -ForegroundColor Yellow
    pip install pyinstaller
}

# Clean previous builds
if (Test-Path ".\build") {
    Write-Host "Cleaning previous build..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force ".\build"
}
if (Test-Path ".\dist") {
    Write-Host "Cleaning previous dist..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force ".\dist"
}

# Run PyInstaller
Write-Host "Running PyInstaller..." -ForegroundColor Yellow
pyinstaller probe347.spec

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build completed successfully!" -ForegroundColor Green
    Write-Host "Executable location: .\dist\Probe347.exe" -ForegroundColor Cyan
    
    # Test the executable
    Write-Host "Testing executable..." -ForegroundColor Yellow
    if (Test-Path ".\dist\Probe347.exe") {
        Write-Host "Executable created successfully!" -ForegroundColor Green
        Write-Host "You can now run: .\dist\Probe347.exe" -ForegroundColor Cyan
    } else {
        Write-Host "Warning: Executable not found!" -ForegroundColor Red
    }
} else {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}