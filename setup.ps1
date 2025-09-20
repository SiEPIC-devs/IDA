# setup_venv.ps1
# PowerShell version of your Bash script
# Run in a PowerShell window. If activation is blocked, run:
#   Set-ExecutionPolicy -Scope Process RemoteSigned

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Setting up venv for Python 3.9..."

# --- pyenv-win bootstrap (adjust if installed elsewhere) ---
$pyenvHome = "$env:USERPROFILE\.pyenv\pyenv-win"
if (Test-Path $pyenvHome) {
  $env:PYENV = $pyenvHome
  $env:Path = "$pyenvHome\bin;$pyenvHome\shims;$env:Path"
} else {
  Write-Host "pyenv-win not found at $pyenvHome. Skipping pyenv usage."
}

# --- ensure Python 3.9 is available (prefer pyenv-win if present) ---
$pyVersion = "3.9.23"
if (Get-Command pyenv -ErrorAction SilentlyContinue) {
  Write-Host "Using pyenv-win to install/use Python $pyVersion"
  pyenv install -s $pyVersion | Out-Host
  pyenv shell $pyVersion       | Out-Host
} else {
  Write-Host "pyenv not found. Falling back to system Python 3.9 (via 'py -3.9' if available)."
}

# --- choose the python launcher ---
function Resolve-Python {
  if (Get-Command python -ErrorAction SilentlyContinue) { return "python" }
  if (Get-Command py -ErrorAction SilentlyContinue)     { return "py -3.9" }
  throw "No suitable Python found. Install Python 3.9 or pyenv-win."
}
$py = Resolve-Python

# --- (re)create venv ---
if (Test-Path .\venv) { Remove-Item -Recurse -Force .\venv }
& $py -m venv venv

# --- activate ---
$activate = ".\venv\Scripts\Activate.ps1"
if (-not (Test-Path $activate)) { throw "Activation script not found at $activate" }
. $activate

# --- pip setup ---
python -m pip install --upgrade pip

if (Test-Path .\requirements.txt) {
  pip install -r .\requirements.txt
} else {
  Write-Host "requirements.txt not found; skipping dependency install."
}

Write-Host "Done! Now running $(python --version)"
Write-Host 'To reactivate later: .\venv\Scripts\Activate.ps1'
