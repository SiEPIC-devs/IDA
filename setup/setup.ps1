[CmdletBinding()]
param(
  [switch]$Rebuild,
  [string]$PythonVersion = "3.9.23",      # exact version for pyenv-win
  [string]$PyMM          = "3.9"          # major.minor for Windows launcher
)

# === Splice: path anchors for setup/ layout ===
# This script lives in .../setup. Project root is one level up.
$ScriptDir   = $PSScriptRoot
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
$VenvPath    = Join-Path $ProjectRoot "venv"

# Requirements live in setup/
$ReqIn   = Join-Path $ScriptDir "requirements.in"
$ReqTxt  = Join-Path $ScriptDir "requirements.txt"
$ReqBld  = Join-Path $ScriptDir "requirements-build.txt"

# Executables inside venv (once created)
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"
$PipExe    = Join-Path $VenvPath "Scripts\pip.exe"

function Ensure-PipTools {
  & $PipExe install -U pip pip-tools | Out-Host
}

# Make requirements resolution relative to setup/
# (Other build steps can still use $ProjectRoot explicitly)
$__origLoc = Get-Location
Push-Location $ScriptDir
# === End splice ===

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Setting up venv for Python $PyMM ..."

function Ensure-PyenvWin {
  if (Get-Command pyenv -EA SilentlyContinue) { return $true }
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
  Write-Host "pyenv-win detected. Ensuring Python $PythonVersion ..."
  pyenv install -s $PythonVersion | Out-Host
  pyenv shell $PythonVersion     | Out-Host   # session-scoped
} else {
  Write-Host "pyenv-win not found; will try the Windows Python launcher or system Python."
}

function Resolve-Python {
  param([string]$mm = "3.9")
  if ($hasPyenv -and (Get-Command python -EA SilentlyContinue)) {
    return @{ Exe = "python"; Args = @() }
  }
  if (Get-Command py -EA SilentlyContinue) {
    try { & py "-$mm" -V *> $null; if ($LASTEXITCODE -eq 0) { return @{ Exe = "py"; Args = @("-$mm") } } } catch {}
  }
  foreach ($name in @("python$($mm.Replace('.',''))","python$mm","python3","python")) {
    if (Get-Command $name -EA SilentlyContinue) { return @{ Exe = $name; Args = @() } }
  }
  throw "No suitable Python $mm found. Install pyenv-win or the Python $mm runtime."
}

$py = Resolve-Python -mm $PyMM
$pyExe  = $py.Exe
$pyArgs = $py.Args

# Recreate venv if requested or missing
if ($Rebuild -and (Test-Path $VenvPath)) {
  Write-Host "Removing existing venv at $VenvPath ..."
  Remove-Item -Recurse -Force $VenvPath
}
if (-not (Test-Path $VenvPath)) {
  Write-Host "Creating venv with $pyExe $($pyArgs -join ' ') ..."
  & $pyExe @($pyArgs + @("-m","venv",$VenvPath))
}

# Activate
$activate = Join-Path $VenvPath "Scripts\Activate.ps1"
if (-not (Test-Path $activate)) { throw "Activation script not found at $activate" }
. $activate

# Robust pip bootstrap (handle interrupted upgrades)
Write-Host "Bootstrapping pip and build tools ..."
python -m ensurepip --upgrade
python -m pip install --upgrade pip setuptools wheel

# Install/upgrade pip-tools (for compile & sync)
python -m pip install --upgrade pip-tools

# Compile from .in files if present; otherwise, just sync from .txt
$compiledAny = $false

if (Test-Path $ReqIn) {
  Write-Host "Compiling $ReqIn → $ReqTxt ..."
  Ensure-PipTools; & $PythonExe -m piptools compile --resolver=backtracking --output-file $ReqTxt $ReqIn
  $compiledAny = $true
}
if (Test-Path $ReqBld) {
  Write-Host "Compiling $ReqBld → $ReqBld ..."
  Ensure-PipTools; & $PythonExe -m piptools compile --resolver=backtracking --output-file $ReqTxt $ReqIn
  $compiledAny = $true
}

# Now sync the environment exactly
if (Test-Path $ReqTxt) {
  if (Test-Path $ReqBld) {
    Write-Host "Syncing venv to requirements.txt + requirements-build.txt ..."
    Ensure-PipTools; & $PythonExe -m piptools sync $ReqTxt $ReqBld
  } else {
    Write-Host "Syncing venv to requirements.txt ..."
    Ensure-PipTools; & $PythonExe -m piptools sync $ReqTxt
  }
} elseif ($compiledAny) {
  throw "Compilation ran but requirements.txt not found."
} else {
  Write-Host "No requirements(.in|.txt) found; venv created with base tools only."
}

# Install requirements as a backup
python -m pip install -r requirements.txt
python -m pip install -r build-requirements.txt

Write-Host "Done! Using $(python --version)"
Write-Host "To reactivate later: $(Join-Path $VenvPath 'Scripts\Activate.ps1')"

# === Splice: restore original location ===
Pop-Location
Set-Location $__origLoc

# [CmdletBinding()]
# param(
  # [switch]$Rebuild,
  # [string]$PythonVersion = "3.9.23",      # exact version for pyenv-win
  # [string]$PyMM          = "3.9"          # major.minor for Windows launcher
# )

# Set-StrictMode -Version Latest
# $ErrorActionPreference = "Stop"

# Write-Host "Setting up venv for Python $PyMM ..."

# function Ensure-PyenvWin {
  # if (Get-Command pyenv -EA SilentlyContinue) { return $true }
  # $candidates = @(
    # $env:PYENV, $env:PYENV_HOME, $env:PYENV_ROOT,
    # "$HOME\.pyenv\pyenv-win",
    # "$env:USERPROFILE\scoop\apps\pyenv-win\current",
    # "C:\ProgramData\pyenv\pyenv-win"
  # ) | Where-Object { $_ -and (Test-Path $_) }
  # foreach ($root in $candidates) {
    # $bin   = Join-Path $root "bin"
    # $shims = Join-Path $root "shims"
    # if (Test-Path (Join-Path $bin "pyenv.cmd")) {
      # $paths = $env:Path -split ';'
      # if ($paths -notcontains $bin)   { $env:Path = "$bin;$env:Path" }
      # if ($paths -notcontains $shims) { $env:Path = "$shims;$env:Path" }
      # $env:PYENV      = $root
      # $env:PYENV_HOME = $root
      # $env:PYENV_ROOT = $root
      # return $true
    # }
  # }
  # return $false
# }

# $hasPyenv = Ensure-PyenvWin
# if ($hasPyenv) {
  # Write-Host "pyenv-win detected. Ensuring Python $PythonVersion ..."
  # pyenv install -s $PythonVersion | Out-Host
  # pyenv shell $PythonVersion     | Out-Host   # session-scoped
# } else {
  # Write-Host "pyenv-win not found; will try the Windows Python launcher or system Python."
# }

# function Resolve-Python {
  # param([string]$mm = "3.9")
  # if ($hasPyenv -and (Get-Command python -EA SilentlyContinue)) {
    # return @{ Exe = "python"; Args = @() }
  # }
  # if (Get-Command py -EA SilentlyContinue) {
    # try { & py "-$mm" -V *> $null; if ($LASTEXITCODE -eq 0) { return @{ Exe = "py"; Args = @("-$mm") } } } catch {}
  # }
  # foreach ($name in @("python$($mm.Replace('.',''))","python$mm","python3","python")) {
    # if (Get-Command $name -EA SilentlyContinue) { return @{ Exe = $name; Args = @() } }
  # }
  # throw "No suitable Python $mm found. Install pyenv-win or the Python $mm runtime."
# }

# # $py = Resolve-Python -mm $PyMM
# # $pyExe  = $py.Exe
# # $pyArgs = $py.Args

# Recreate venv if requested or missing
# # if ($Rebuild -and (Test-Path .\venv)) {
#   # Write-Host "Removing existing venv ..."
#   # Remove-Item -Recurse -Force .\venv
# # }
# # if (-not (Test-Path .\venv)) {
#   # Write-Host "Creating venv with $pyExe $($pyArgs -join ' ') ..."
#   # & $pyExe @($pyArgs + @("-m","venv","venv"))
# # }

# Activate
# # $activate = ".\venv\Scripts\Activate.ps1"
# # if (-not (Test-Path $activate)) { throw "Activation script not found at $activate" }
# # . $activate

# Robust pip bootstrap (handle interrupted upgrades)
# # Write-Host "Bootstrapping pip and build tools ..."
# # python -m ensurepip --upgrade
# # python -m pip install --upgrade pip setuptools wheel

# Install/upgrade pip-tools (for compile & sync)
# # python -m pip install --upgrade pip-tools

# If you want to suppress that pkg_resources deprecation in all children, uncomment:
# $env:PYTHONWARNINGS = "ignore::UserWarning:pkg_resources"

# Compile from .in files if present; otherwise, just sync from .txt
# # $compiledAny = $false

# # if (Test-Path .\requirements.in) {
#   # Write-Host "Compiling requirements.in → requirements.txt ..."
#   # pip-compile --upgrade --generate-hashes requirements.in
#   # $compiledAny = $true
# # }
# # if (Test-Path .\requirements-build.in) {
#   # Write-Host "Compiling requirements-build.in → requirements-build.txt ..."
#   # pip-compile --upgrade --generate-hashes requirements-build.in
#   # $compiledAny = $true
# # }

# Now sync the environment exactly (this solved your earlier inconsistency)
# # if (Test-Path .\requirements.txt) {
#   # if (Test-Path .\requirements-build.txt) {
#     # Write-Host "Syncing venv to requirements.txt + requirements-build.txt ..."
#     # pip-sync requirements.txt requirements-build.txt
#   # } else {
#     # Write-Host "Syncing venv to requirements.txt ..."
#     # pip-sync requirements.txt
#   # }
# # } elseif ($compiledAny) {
#   Shouldn't happen, but just in case compilation created files in a different path
#   # throw "Compilation ran but requirements.txt not found."
# # } else {
#   # Write-Host "No requirements(.in|.txt) found; venv created with base tools only."
# # }

# # Write-Host "Done! Using $(python --version)"
# # Write-Host 'To reactivate later: .\venv\Scripts\Activate.ps1'