[CmdletBinding()]
param(
    [switch]$Installer
)

$ErrorActionPreference = 'Stop'
$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Python = Join-Path $RepositoryRoot '.venv\Scripts\python.exe'
$Spec = Join-Path $PSScriptRoot 'PhoneRemote.spec'
$Dist = Join-Path $RepositoryRoot 'dist'
$Work = Join-Path $RepositoryRoot 'build\pyinstaller'

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'Create the Python 3.12 .venv and install server[dev] first.'
}

& $Python -m PyInstaller --noconfirm --clean --distpath $Dist --workpath $Work $Spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

if ($Installer) {
    $CompilerCandidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
    )
    $Compiler = $CompilerCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if (-not $Compiler) { throw 'Inno Setup 6 was not found.' }
    & $Compiler (Join-Path $PSScriptRoot 'installer.iss')
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup build failed.' }
}
