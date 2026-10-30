param(
  [string]$Owner = "Mahimedia456",
  [string]$RepoName = "Atomosreportsocialmedia",
  [string]$Destination = "$PWD\Atomosreportsocialmedia"
)
$ErrorActionPreference = "Stop"
foreach ($command in @('git','gh')) {
  if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
    throw "$command is required. Install Git and GitHub CLI, then run gh auth login."
  }
}
& gh auth status
if ($LASTEXITCODE -ne 0) { throw "Sign in first using: gh auth login" }
if (Test-Path $Destination) { throw "Destination already exists: $Destination" }
# gh repo view exits non-zero for a new repository. PowerShell 5.1 can treat
# its stderr as a terminating error when ErrorActionPreference is Stop.
# List the authenticated owner's repository names instead (read-only and no 404).
Write-Host "Checking whether $Owner/$RepoName already exists..."
$existingRepoNames = @(& gh repo list "$Owner" --limit 1000 --json name --jq '.[].name')
if ($LASTEXITCODE -ne 0) {
  throw "Could not check GitHub repositories. Run: gh repo list $Owner"
}
if ($existingRepoNames -contains $RepoName) {
  throw "Repository $Owner/$RepoName already exists. Refusing to overwrite it."
}
Write-Host "Target repository does not exist; proceeding with a new independent clone."
& git clone --single-branch -b atomos-report-clone-ready "https://github.com/$Owner/Angelbirdreportsocialmedia.git" "$Destination"
if ($LASTEXITCODE -ne 0) { throw "Could not clone Atomos source branch." }
Push-Location $Destination
try {
  # New orphan root prevents Angelbird data/history being imported into the new repository.
  & git checkout --orphan main
  & git add -A
  & git -c user.name="Atomos-report-setup" -c user.email="41898282+github-actions[bot]@users.noreply.github.com" commit -m "Initial independent Atomos monitoring app"
  if ($LASTEXITCODE -ne 0) { throw "Initial Atomos commit failed." }
  Write-Host "Creating GitHub repository $Owner/$RepoName..."
  & gh repo create "$Owner/$RepoName" --public
  if ($LASTEXITCODE -ne 0) { throw "GitHub repository creation failed." }
  & git remote set-url origin "https://github.com/$Owner/$RepoName.git"
  Write-Host "Pushing isolated Atomos app to GitHub main..."
  & git push -u origin main
  if ($LASTEXITCODE -ne 0) { throw "GitHub push failed." }
  Write-Host "Created independent repository: https://github.com/$Owner/$RepoName"
  Write-Host "NEXT: Add OPENAI_API_KEY and YOUTUBE_API_KEY in its Actions Secrets."
  Write-Host "NEXT: Import new repository into Vercel, build: node scripts/build_website.mjs, output: _site."
} finally {
  Pop-Location
}
