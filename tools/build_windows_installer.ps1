$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

$gameVersion = python -c "import config; print(config.VERSION)"
if ($LASTEXITCODE -ne 0 -or -not $gameVersion) {
    throw "Unable to read the game version from config.py."
}

pyinstaller --noconfirm --clean RacingLinePro-portable.spec
if ($LASTEXITCODE -ne 0) {
    throw "Portable directory build failed."
}

$compilerCandidates = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)
$compiler = $compilerCandidates |
    Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1
if (-not $compiler) {
    throw "Inno Setup 6 is required. Install JRSoftware.InnoSetup with winget."
}

& $compiler "/DAppVersion=$gameVersion" "packaging\RacingLinePro.iss"
if ($LASTEXITCODE -ne 0) {
    throw "Installer compilation failed."
}

$installer = Join-Path $projectRoot "dist\RacingLinePro-v$gameVersion-Setup.exe"
$defenderPlatform = Get-ChildItem -LiteralPath "C:\ProgramData\Microsoft\Windows Defender\Platform" -Directory |
    Sort-Object Name -Descending |
    Select-Object -First 1
if (-not $defenderPlatform) {
    throw "Microsoft Defender command-line scanner was not found."
}

$scanner = Join-Path $defenderPlatform.FullName "MpCmdRun.exe"
& $scanner -Scan -ScanType 3 -File $installer -DisableRemediation
if ($LASTEXITCODE -ne 0) {
    throw "Defender did not approve the installer. Do not publish it."
}

$file = Get-Item -LiteralPath $installer
$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $installer
[pscustomobject]@{
    Version = $gameVersion
    Path = $file.FullName
    Size = $file.Length
    SHA256 = $hash.Hash
}
