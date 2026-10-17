<#
.SYNOPSIS
Install the ChemDraw Skill, and optionally its toolkit runtime, transactionally.

.DESCRIPTION
Without -Apply this prints the proposal only. With -Apply the Skill folder is
staged, verified, and swapped into place; an existing installation is moved to
a backup outside the Skill discovery directory and restored on failure.

-Runtime creates (or reuses) a `chemdraw-venv` beside the installed Skill and
installs the cdxml-toolkit revision pinned in runtime.json. `scripts/cdx.py`
finds that venv automatically, so any Python can launch the Skill's CLI.

.EXAMPLE
./scripts/install.ps1                                  # proposal for ~/.claude/skills/chemdraw
./scripts/install.ps1 -Apply -Runtime -Python py       # install Skill and runtime
./scripts/install.ps1 -Apply -Destination D:\agents\skills\chemdraw
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [string]$Destination,
    [string]$BackupRoot,
    [string]$Python,
    [switch]$Runtime,
    [ValidatePattern('^[a-z][a-z0-9_-]*$')]
    [string[]]$Extras = @('publication', 'scientific', 'office', 'analysis', 'image', 'chemscript'),
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-TreeFingerprint {
    param([Parameter(Mandatory)][string]$Root)

    $resolved = [IO.Path]::GetFullPath($Root).TrimEnd('\')
    $records = @(
        Get-ChildItem -LiteralPath $resolved -Recurse -File -Force |
            Where-Object {
                $_.FullName -notmatch '[\\/](__pycache__|\.pytest_cache|\.mypy_cache)[\\/]' -and
                $_.Extension -notin @('.pyc', '.pyo') -and
                $_.Name -ne 'manifest.json'
            } |
            Sort-Object FullName |
            ForEach-Object {
                $relative = $_.FullName.Substring($resolved.Length).TrimStart('\').Replace('\', '/')
                $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
                "$relative|$($_.Length)|$hash"
            }
    )
    $bytes = [Text.Encoding]::UTF8.GetBytes(($records -join "`n"))
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '')
    } finally {
        $sha.Dispose()
    }
}

function Copy-SkillTree {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Target
    )

    New-Item -ItemType Directory -Path $Target -Force | Out-Null
    $robocopy = Get-Command robocopy.exe -ErrorAction Stop
    & $robocopy.Source $Source $Target /E /XD __pycache__ .pytest_cache .mypy_cache /XF *.pyc *.pyo manifest.json /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "robocopy failed with exit code $LASTEXITCODE"
    }
}

function Get-PythonCandidates {
    # Executable plus prefix arguments; the `py` launcher is asked for each supported version.
    param([string]$Requested)

    if ($Requested -and (Test-Path -LiteralPath $Requested -PathType Leaf)) {
        return , @{ Exe = [IO.Path]::GetFullPath($Requested); Args = @() }
    }
    $names = if ($Requested) { @($Requested) } else { @('py', 'python') }
    $found = @()
    foreach ($name in $names) {
        $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $command) { continue }
        if ($command.Name -ieq 'py.exe') {
            foreach ($version in '3.12', '3.13', '3.11', '3.10') {
                $found += , @{ Exe = $command.Source; Args = @("-$version") }
            }
        } else {
            $found += , @{ Exe = $command.Source; Args = @() }
        }
    }
    if ($Requested -and -not $found) { throw "Python runtime not found: $Requested" }
    return $found
}

function Resolve-BasePython {
    # First candidate that runs as 64-bit Python 3.10-3.13; otherwise $null.
    param([string]$Requested)

    foreach ($candidate in Get-PythonCandidates -Requested $Requested) {
        $info = Get-PythonVersion -Base $candidate
        if ($info -and $info.Bits -eq 64 -and $info.Version -ge [version]'3.10' -and $info.Version -lt [version]'3.14') {
            return $candidate
        }
    }
    return $null
}

function Get-PythonVersion {
    param([hashtable]$Base)
    $code = 'import struct,sys;print(sys.version_info[0],sys.version_info[1],struct.calcsize(chr(80))*8)'
    $output = & $Base.Exe @($Base.Args + @('-c', $code)) 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $output) { return $null }
    $parts = ([string]$output).Trim().Split(' ')
    return @{ Version = [version]"$($parts[0]).$($parts[1])"; Bits = [int]$parts[2] }
}

$repositoryRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$sourcePath = [IO.Path]::GetFullPath((Join-Path $repositoryRoot 'skill\chemdraw'))
if (-not (Test-Path -LiteralPath (Join-Path $sourcePath 'SKILL.md') -PathType Leaf)) {
    throw "Deployable Skill not found: $sourcePath"
}

if (-not $Destination) {
    $Destination = Join-Path $HOME '.claude\skills\chemdraw'
}
$destinationPath = [IO.Path]::GetFullPath($Destination).TrimEnd('\')
if ($destinationPath -eq $sourcePath.TrimEnd('\')) {
    throw 'Destination must differ from the repository Skill source.'
}

$destinationParent = Split-Path -Parent $destinationPath
if ($BackupRoot) {
    $backupRootPath = [IO.Path]::GetFullPath($BackupRoot).TrimEnd('\')
} elseif ([IO.Path]::GetFileName($destinationParent) -ieq 'skills') {
    $agentHomeFromDestination = Split-Path -Parent $destinationParent
    $backupRootPath = [IO.Path]::GetFullPath(
        (Join-Path $agentHomeFromDestination 'backups\skills\chemdraw')
    ).TrimEnd('\')
} else {
    $backupRootPath = [IO.Path]::GetFullPath(
        (Join-Path $destinationParent '.chemdraw-backups')
    ).TrimEnd('\')
}
if ($backupRootPath.StartsWith(
    $destinationPath + '\', [StringComparison]::OrdinalIgnoreCase
)) {
    throw 'BackupRoot must not be inside the installed Skill directory.'
}

$venvPath = Join-Path $destinationParent 'chemdraw-venv'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'
$runtimeAction = if (-not $Runtime) { 'skip' } elseif (Test-Path -LiteralPath $venvPython -PathType Leaf) { 'reuse' } else { 'create' }
$basePython = $null
if ($Runtime -and $runtimeAction -eq 'create') {
    $basePython = Resolve-BasePython -Requested $Python
    if (-not $basePython) {
        throw 'The runtime needs a working 64-bit Python 3.10-3.13; none was found. Pass -Python <path-to-python.exe>.'
    }
}

# Assign through a typed variable: an `if` expression would unroll a one-item array into a string.
[object[]]$runtimeExtras = @()
if ($Runtime) { $runtimeExtras = @($Extras) }

$sourceFingerprint = Get-TreeFingerprint -Root $sourcePath
$destinationExists = Test-Path -LiteralPath $destinationPath -PathType Container
$proposal = [ordered]@{
    apply = [bool]$Apply
    source = $sourcePath
    destination = $destinationPath
    source_fingerprint = $sourceFingerprint
    existing_destination = $destinationExists
    backup_root = $backupRootPath
    backup = if ($destinationExists) { (Join-Path $backupRootPath '<timestamp>-<id>') } else { $null }
    runtime = [ordered]@{
        action = $runtimeAction
        venv = if ($Runtime) { $venvPath } else { $null }
        base_python = if ($basePython) { (@($basePython.Exe) + $basePython.Args) -join ' ' } else { $null }
        extras = $runtimeExtras
    }
    status = if ($Apply) { 'pending' } else { 'proposal' }
}

if (-not $Apply) {
    $proposal | ConvertTo-Json -Depth 4
    return
}

if (-not $PSCmdlet.ShouldProcess($destinationPath, 'Install the ChemDraw Skill')) {
    $proposal.status = 'whatif'
    $proposal | ConvertTo-Json -Depth 4
    return
}

New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
$staging = Join-Path $destinationParent ('.chemdraw-install-' + [guid]::NewGuid().ToString('N'))
$backup = $null
$published = $false

try {
    Copy-SkillTree -Source $sourcePath -Target $staging
    $stagedFingerprint = Get-TreeFingerprint -Root $staging
    if ($stagedFingerprint -ne $sourceFingerprint) {
        throw 'Staged Skill fingerprint does not match the repository source.'
    }

    if ($destinationExists) {
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmssfff'
        New-Item -ItemType Directory -Path $backupRootPath -Force | Out-Null
        $backup = Join-Path $backupRootPath "$stamp-$([guid]::NewGuid().ToString('N'))"
        Move-Item -LiteralPath $destinationPath -Destination $backup
    }
    Move-Item -LiteralPath $staging -Destination $destinationPath
    $published = $true

    $installedFingerprint = Get-TreeFingerprint -Root $destinationPath
    if ($installedFingerprint -ne $sourceFingerprint) {
        throw 'Installed Skill fingerprint does not match the repository source.'
    }
} catch {
    $failure = $_
    if ($published -and (Test-Path -LiteralPath $destinationPath)) {
        Remove-Item -LiteralPath $destinationPath -Recurse -Force
    }
    if ($backup -and (Test-Path -LiteralPath $backup)) {
        Move-Item -LiteralPath $backup -Destination $destinationPath
    }
    throw $failure
} finally {
    if (Test-Path -LiteralPath $staging) {
        Remove-Item -LiteralPath $staging -Recurse -Force
    }
}

$proposal.status = 'installed'
$proposal.backup = $backup
$proposal.installed_fingerprint = $installedFingerprint

# The runtime is installed after the Skill swap: a failed pip install leaves a
# usable Skill (portable docs, cdx.py diagnostics) and is reported, not rolled back.
$exitCode = 0
if ($Runtime) {
    try {
        # Progress goes to stderr so stdout stays a single JSON document.
        if ($runtimeAction -eq 'create') {
            & $basePython.Exe @($basePython.Args + @('-m', 'venv', $venvPath)) 2>&1 |
                ForEach-Object { [Console]::Error.WriteLine([string]$_) }
            if ($LASTEXITCODE -ne 0) { throw "venv creation failed with exit code $LASTEXITCODE" }
        }
        & $venvPython (Join-Path $destinationPath 'scripts\install_runtime.py') --extras @Extras 2>&1 |
            ForEach-Object { [Console]::Error.WriteLine([string]$_) }
        if ($LASTEXITCODE -ne 0) { throw "runtime installation failed with exit code $LASTEXITCODE" }
        $proposal.runtime.status = 'installed'
    } catch {
        $proposal.runtime.status = 'failed'
        $proposal.runtime.error = $_.Exception.Message
        $proposal.status = 'installed_runtime_failed'
        $exitCode = 1
    }
}

# Record the installed state so `check_installation.py` / `cdx.py doctor` can detect later drift.
$manifestPython = if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    @{ Exe = $venvPython; Args = @() }
} else {
    # Any working Python 3 can write the manifest (standard library only).
    Get-PythonCandidates -Requested $Python | Where-Object { Get-PythonVersion -Base $_ } | Select-Object -First 1
}
if ($manifestPython) {
    & $manifestPython.Exe @($manifestPython.Args + @((Join-Path $destinationPath 'scripts\check_installation.py'), '--write-manifest', '--installed', $destinationPath)) | Out-Null
    $proposal.manifest = if ($LASTEXITCODE -eq 0) { Join-Path $destinationPath 'manifest.json' } else { 'failed' }
} else {
    $proposal.manifest = 'skipped: no Python found'
}

$proposal | ConvertTo-Json -Depth 6
exit $exitCode
