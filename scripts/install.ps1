[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [string]$Destination,
    [string]$BackupRoot,
    [string]$Python,
    [switch]$ConfigureMcp,
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
                $_.FullName -notmatch '[\\/]__pycache__[\\/]' -and
                $_.Extension -notin @('.pyc', '.pyo')
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
    & $robocopy.Source $Source $Target /E /XD __pycache__ .pytest_cache .mypy_cache /XF *.pyc *.pyo /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "robocopy failed with exit code $LASTEXITCODE"
    }
}

$repositoryRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$sourcePath = [IO.Path]::GetFullPath((Join-Path $repositoryRoot 'skill\chemdraw'))
if (-not (Test-Path -LiteralPath (Join-Path $sourcePath 'SKILL.md') -PathType Leaf)) {
    throw "Deployable Skill not found: $sourcePath"
}

if (-not $Destination) {
    if ($ConfigureMcp) {
        # This opt-in adapter configures this specific client only.
        $clientHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
    } else {
        $clientHome = Join-Path $HOME '.agents'
    }
    $Destination = Join-Path $clientHome 'skills\chemdraw'
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

if ($Python) {
    $Python = [IO.Path]::GetFullPath($Python.Trim())
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        throw "Python runtime not found: $Python"
    }
}

$sourceFingerprint = Get-TreeFingerprint -Root $sourcePath
$destinationExists = Test-Path -LiteralPath $destinationPath -PathType Container
$proposal = [ordered]@{
    apply = [bool]$Apply
    configure_mcp = [bool]$ConfigureMcp
    source = $sourcePath
    destination = $destinationPath
    source_fingerprint = $sourceFingerprint
    existing_destination = $destinationExists
    backup_root = $backupRootPath
    backup = if ($destinationExists) { (Join-Path $backupRootPath '<timestamp>-<id>') } else { $null }
    python = if ($Python) { $Python } else { '<auto-discover>' }
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

$parent = $destinationParent
New-Item -ItemType Directory -Path $parent -Force | Out-Null
$staging = Join-Path $parent ('.chemdraw-install-' + [guid]::NewGuid().ToString('N'))
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

    $mcpResult = $null
    if ($ConfigureMcp) {
        $configureScript = Join-Path $destinationPath 'scripts\configure_mcp.ps1'
        $parameters = @{
            SkillRoot = $destinationPath
            Apply = $true
        }
        if ($Python) {
            $parameters.Python = $Python
        }
        $mcpResult = (& $configureScript @parameters | Out-String).Trim()
    }

    $proposal.status = 'installed'
    $proposal.backup = $backup
    $proposal.installed_fingerprint = $installedFingerprint
    $proposal.mcp_result = $mcpResult
    $proposal | ConvertTo-Json -Depth 6
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
