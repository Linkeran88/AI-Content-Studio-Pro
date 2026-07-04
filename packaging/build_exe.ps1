$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

function Invoke-Step {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
  )

  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed: $FilePath $($Arguments -join ' ')"
  }
}

function Find-Python {
  $candidates = @()

  $localPython = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"
  if (Test-Path $localPython) {
    $candidates += $localPython
  }

  $pythonCommands = Get-Command python.exe -All -ErrorAction SilentlyContinue
  foreach ($command in $pythonCommands) {
    if ($command.Source -and ($candidates -notcontains $command.Source)) {
      $candidates += $command.Source
    }
  }

  foreach ($candidate in $candidates) {
    & $candidate -m pip --version *> $null
    if ($LASTEXITCODE -eq 0) {
      return $candidate
    }
  }

  throw "Python with pip was not found. Install Python 3.10 or 3.11 and enable pip."
}

$Python = Find-Python

Invoke-Step $Python -m pip install --upgrade pip
Invoke-Step $Python -m pip install -r requirements.txt

$TempRoot = Join-Path $env:TEMP "AIContentStudioProBuild"
$WorkPath = Join-Path $TempRoot "build"
$SpecPath = Join-Path $TempRoot "spec"
$DistPath = Join-Path $ProjectRoot "dist"
$AssetsPath = Join-Path $ProjectRoot "assets"
$ConfigPath = Join-Path $ProjectRoot "config.json"

foreach ($path in @($WorkPath, $SpecPath, $DistPath)) {
  if (Test-Path $path) {
    Remove-Item -LiteralPath $path -Recurse -Force
  }
}

Invoke-Step $Python -m PyInstaller `
  --clean `
  --noconfirm `
  --windowed `
  --name "AI Content Studio Pro" `
  --distpath $DistPath `
  --workpath $WorkPath `
  --specpath $SpecPath `
  --add-data "$AssetsPath;assets" `
  --add-data "$ConfigPath;." `
  --hidden-import faster_whisper `
  --hidden-import ctranslate2 `
  --collect-data faster_whisper `
  --collect-binaries ctranslate2 `
  --collect-data ctranslate2 `
  main.py

Write-Host ""
Write-Host "Build complete: $ProjectRoot\dist\AI Content Studio Pro"
