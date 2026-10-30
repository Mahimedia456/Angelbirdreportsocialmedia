$ErrorActionPreference='Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
$env:DRY_RUN='true'
$env:REPORT_DATE='2026-10-30'
python -m src.main
if ($LASTEXITCODE -ne 0) { throw 'Demo PDF failed' }
