# Run this from the extracted package on Windows. Uses GitHub CLI browser authentication.
$ErrorActionPreference = 'Stop'
$repo = 'https://github.com/Mahimedia456/Angelbirdreportsocialmedia.git'
$root = Split-Path -Parent $PSScriptRoot
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Install Git for Windows first.' }
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'Install GitHub CLI (gh) first.' }
if (-not (Test-Path (Join-Path $root '.github/workflows/daily-report.yml'))) { throw 'Workflow missing from source package.' }
gh auth status 2>$null
if ($LASTEXITCODE -ne 0) { gh auth login }
Set-Location $root
if (-not (Test-Path .git)) { git init; git branch -M main }
$origin = git remote
if ($origin -notcontains 'origin') { git remote add origin $repo }
git add .
# Never use force push. Keep pre-existing repository files safe.
if (-not (git status --porcelain)) { Write-Host 'No new changes to commit.'; exit 0 }
git -c user.name='Angelbird Setup' -c user.email='angelbird-setup@users.noreply.github.com' commit -m 'Add Angelbird AI social monitoring automation'
git push -u origin main
if ($LASTEXITCODE -ne 0) { throw 'Push failed. If repository has an existing commit, reconcile it first without force push.' }
Write-Host 'Uploaded to GitHub. Add OPENAI_API_KEY in GitHub repository secrets, then run the workflow.'
