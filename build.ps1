# build.ps1 -- all in one: bump version -> git push -> PyInstaller -> Inno -> GitHub Release (tag + .exe)
# Run from D:\X\App:   .\build.ps1 1.7 "fix: import-status cache"
# ASCII-only so PowerShell 5.1 reads it regardless of file encoding.

param(
    [Parameter(Mandatory=$true)][string]$Ver,
    [string]$Notes = "release"
)

$ErrorActionPreference = "Stop"
$ISCC = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"   # fix path if Inno is elsewhere

function Step($n) { Write-Host "`n=== $n ===" -ForegroundColor Cyan }
function Check($w) { if ($LASTEXITCODE -ne 0) { throw "$w failed (exit $LASTEXITCODE)" } }

if (-not (Test-Path $ISCC)) { throw "ISCC.exe not found at $ISCC -- fix the path." }

# Pick Python: prefer a local venv, else global python on PATH
$py = "python"
foreach ($c in @(".\venv\Scripts\python.exe", ".\.venv\Scripts\python.exe", ".\env\Scripts\python.exe")) {
    if (Test-Path $c) { $py = $c; break }
}
Write-Host "Python: $py"
& $py -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) { throw "PyInstaller not installed for $py. Run: $py -m pip install pyinstaller" }

# Guard: do not build a version <= the latest published GitHub release
$latestTag = ""
try { $latestTag = (gh release view --json tagName -q ".tagName" 2>$null) } catch {}
if ($latestTag) {
    $greater = $true
    try { $greater = ([version]$Ver -gt [version]($latestTag.TrimStart('v','V'))) } catch { $greater = $true }
    if (-not $greater) { throw "Version $Ver must be GREATER than latest release $latestTag. Pick a higher number." }
    Write-Host "Latest release: $latestTag  ->  building $Ver" -ForegroundColor Cyan
}

# 1. Bump version in version.py and installer.iss (read/write as UTF-8, replace one line)
Step "Version -> $Ver"
$vp = Get-Content version.py -Raw -Encoding UTF8
$vp = $vp -replace '__version__\s*=\s*".*"', "__version__ = `"$Ver`""
Set-Content version.py -Value $vp -NoNewline -Encoding UTF8

$iss = Get-Content installer.iss -Raw -Encoding UTF8
$iss = $iss -replace '#define MyAppVersion ".*"', "#define MyAppVersion `"$Ver`""
Set-Content installer.iss -Value $iss -NoNewline -Encoding UTF8

# 2. Git: commit + push (Render redeploys on push). Tolerate "nothing to commit" on re-runs.
Step "Git push"
git add -A
git commit -m "v$Ver`: $Notes"
if ($LASTEXITCODE -ne 0) { Write-Host "Nothing new to commit -- continuing." -ForegroundColor Yellow }
git push
Check "git push"

# 3. PyInstaller -> dist\<AppDir>\
Step "PyInstaller"
& $py -m PyInstaller --noconfirm --clean desktop.spec
Check "pyinstaller"

# 4. Inno Setup -> dist\installer\*setup_$Ver.exe
Step "Installer (Inno)"
& $ISCC installer.iss
Check "ISCC"

# 5. GitHub Release: create tag v$Ver on main + upload the .exe (auto-update reads releases/latest)
Step "GitHub Release v$Ver"
$setup = Get-ChildItem "dist\installer" -Filter "*setup_$Ver.exe" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
if (-not $setup) { throw "setup .exe for $Ver not found in dist\installer" }
gh release create "v$Ver" $setup --target main --title "v$Ver" --notes "$Notes"
Check "gh release"

Write-Host "`nDONE: v$Ver pushed, built, release published with the installer." -ForegroundColor Green
