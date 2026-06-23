# build.ps1 -- all in one: bump version -> git push -> PyInstaller -> Inno -> GitHub Release
# Run from D:\X\App:   .\build.ps1 1.5.2 "fix: import-status cache"
# ASCII-only on purpose so PowerShell 5.1 reads it regardless of file encoding.

param(
    [Parameter(Mandatory=$true)][string]$Ver,
    [string]$Notes = "release"
)

$ErrorActionPreference = "Stop"
$ISCC = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"   # fix path if Inno is elsewhere

function Step($n) { Write-Host "`n=== $n ===" -ForegroundColor Cyan }
function Check($w) { if ($LASTEXITCODE -ne 0) { throw "$w failed (exit $LASTEXITCODE)" } }

if (-not (Test-Path $ISCC)) { throw "ISCC.exe not found at $ISCC -- fix the path in the script." }

# 1. Bump version in version.py and installer.iss (read/write as UTF-8, replace one line)
Step "Version -> $Ver"
$vp = Get-Content version.py -Raw -Encoding UTF8
$vp = $vp -replace '__version__\s*=\s*".*"', "__version__ = `"$Ver`""
Set-Content version.py -Value $vp -NoNewline -Encoding UTF8

$iss = Get-Content installer.iss -Raw -Encoding UTF8
$iss = $iss -replace '#define MyAppVersion ".*"', "#define MyAppVersion `"$Ver`""
Set-Content installer.iss -Value $iss -NoNewline -Encoding UTF8

# 2. Git: commit + push (Render redeploys on push)
Step "Git push"
git add -A
git commit -m "v$Ver`: $Notes"
Check "git commit"
git push
Check "git push"

# 3. PyInstaller -> dist\<AppDir>\
Step "PyInstaller"
pyinstaller --noconfirm --clean desktop.spec
Check "pyinstaller"

# 4. Inno Setup -> dist\installer\*setup_$Ver.exe
Step "Installer (Inno)"
& $ISCC installer.iss
Check "ISCC"

# 5. GitHub Release with the .exe (desktop auto-update reads it)
Step "GitHub Release v$Ver"
$setup = Get-ChildItem "dist\installer" -Filter "*setup_$Ver.exe" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
if (-not $setup) { throw "setup .exe for $Ver not found in dist\installer" }
gh release create "v$Ver" $setup --title "v$Ver" --notes "$Notes"
Check "gh release"

Write-Host "`nDONE: v$Ver pushed, built, release published." -ForegroundColor Green
