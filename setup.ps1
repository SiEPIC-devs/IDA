# setup_venv.ps1
# PowerShell: create/refresh a venv using pyenv-win if available, else fallback.
#   Set-ExecutionPolicy -Scope Process RemoteSigned   # if activation is blocked

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TargetPy = "3.9.23"          # exact version if using pyenv
$TargetMM = "3.9"             # major.minor for the Python launcher
Write-Host "Setting up venv for Python $TargetMM ..."

# --- Locate & enable pyenv-win if present ------------------------------------
function Ensure-PyenvWin {
  # If pyenv already on PATH, we're done.
  if (Get-Command pyenv -ErrorAction SilentlyContinue) { return $true }

  # Candidate roots from env + common installers.
  $candidates = @(
    $env:PYENV, $env:PYENV_HOME, $env:PYENV_ROOT,
    "$HOME\.pyenv\pyenv-win",
    "$env:USERPROFILE\scoop\apps\pyenv-win\current",
    "C:\ProgramData\pyenv\pyenv-win"
  ) | Where-Object { $_ -and (Test-Path $_) }

  foreach ($root in $candidates) {
    $bin   = Join-Path $root "bin"
    $shims = Join-Path $root "shims"
    if (Test-Path (Join-Path $bin "pyenv.cmd")) {
      # Avoid duplicating PATH entries
      $paths = $env:Path -split ';'
      if ($paths -notcontains $bin)   { $env:Path = "$bin;$env:Path" }
      if ($paths -notcontains $shims) { $env:Path = "$shims;$env:Path" }
      $env:PYENV      = $root
      $env:PYENV_HOME = $root
      $env:PYENV_ROOT = $root
      return $true
    }
  }
  return $false
}

$hasPyenv = Ensure-PyenvWin
if ($hasPyenv) {
  Write-Host "pyenv-win detected. Ensuring Python $TargetPy ..."
  pyenv install -s $TargetPy | Out-Host
  # Use for this PowerShell session (doesn't write .python-version)
  pyenv shell $TargetPy | Out-Host
} else {
  Write-Host "pyenv-win not found; will try the Windows Python launcher or system Python."
}

# --- Resolve the python command safely (exe + args array) --------------------
function Resolve-Python {
  param([string]$mm = "3.9")
  # If pyenv-shims are active, just use 'python'
  if (Get-Command pyenv -EA SilentlyContinue -and (Get-Command python -EA SilentlyContinue)) {
    return @{ Exe = "python"; Args = @() }
  }
  # Try the Windows launcher with a version selector
  if (Get-Command py -EA SilentlyContinue) {
    # Validate that 'py -3.9' exists
    $ok = $false
    try {
      & py "-$mm" -V *> $null
      $ok = ($LASTEXITCODE -eq 0)
    } catch { $ok = $false }
    if ($ok) { return @{ Exe = "py"; Args = @("-$mm") } }
  }
  # Try direct commands
  foreach ($name in @("python$mm".Replace(".",""), "python$mm", "python3", "python")) {
    if (Get-Command $name -EA SilentlyContinue) { return @{ Exe = $name; Args = @() } }
  }
  throw "No suitable Python $mm found. Install pyenv-win or the Python $mm runtime."
}

$py = Resolve-Python -mm $TargetMM
$pyExe  = $py.Exe
$pyArgs = $py.Args

# --- (Re)create venv ---------------------------------------------------------
if (Test-Path .\venv) {
  Write-Host "Removing existing venv ..."
  Remove-Item -Recurse -Force .\venv
}
Write-Host "Creating venv with $pyExe $($pyArgs -join ' ') ..."
& $pyExe @($pyArgs + @("-m","venv","venv"))

# --- Activate ---------------------------------------------------------------
$activate = ".\venv\Scripts\Activate.ps1"
if (-not (Test-Path $activate)) { throw "Activation script not found at $activate" }
. $activate

# --- pip bootstrap -----------------------------------------------------------
python -m pip install --upgrade pip
if (Test-Path .\requirements.txt) {
  pip install -r .\requirements.txt
} else {
  Write-Host "requirements.txt not found; skipping dependency install."
}

Write-Host "Done! Using $(python --version)"
Write-Host 'To reactivate later: .\venv\Scripts\Activate.ps1'
