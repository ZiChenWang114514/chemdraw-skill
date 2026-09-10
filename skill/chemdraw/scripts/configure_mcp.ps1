[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$Python,
    [string]$SkillRoot,
    [string]$ConfigPath,
    [string]$CodexCommand = 'codex',
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$discoveryScript = Join-Path $scriptRoot 'runtime_discovery.py'

function Get-Sha256Hex {
    param([Parameter(Mandatory)][string]$LiteralPath)

    $stream = [IO.File]::OpenRead([IO.Path]::GetFullPath($LiteralPath))
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = $sha.ComputeHash($stream)
        return ([BitConverter]::ToString($bytes)).Replace('-', '')
    } finally {
        $sha.Dispose()
        $stream.Dispose()
    }
}

function Get-DiscoveryBootstrap {
    if ($Python -and (Test-Path -LiteralPath $Python -PathType Leaf)) {
        return [pscustomobject]@{ Command = $Python; Arguments = @() }
    }
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        return [pscustomobject]@{ Command = $launcher.Source; Arguments = @('-3') }
    }
    $interpreter = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($interpreter) {
        return [pscustomobject]@{ Command = $interpreter.Source; Arguments = @() }
    }
    throw 'A bootstrap Python is required to run runtime_discovery.py.'
}

function Invoke-RuntimeDiscovery {
    $bootstrap = Get-DiscoveryBootstrap
    $arguments = @($bootstrap.Arguments) + @($discoveryScript, '--json')
    if ($Python) { $arguments += @('--python', $Python) }
    if ($SkillRoot) { $arguments += @('--skill-root', $SkillRoot) }
    $output = & $bootstrap.Command @arguments 2>&1
    $exitCode = $LASTEXITCODE
    $text = $output | Out-String
    if ($exitCode -ne 0) {
        throw "Runtime discovery failed with exit code $exitCode`: $($text.Trim())"
    }
    try {
        return $text | ConvertFrom-Json
    } catch {
        throw "Runtime discovery returned invalid JSON: $($text.Trim())"
    }
}

function Invoke-CodexCommand {
    param([string[]]$Arguments)

    $output = & $CodexCommand @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    return [pscustomobject]@{
        ExitCode = $exitCode
        Output = ($output | Out-String).Trim()
    }
}

function Get-ConfigFingerprint {
    param([string]$ResolvedConfigPath)

    if (-not (Test-Path -LiteralPath $ResolvedConfigPath -PathType Leaf)) {
        return '<absent>'
    }
    return Get-Sha256Hex -LiteralPath $ResolvedConfigPath
}

function Test-SamePath {
    param([string]$Actual, [string]$Expected)

    if (-not $Actual -or -not $Expected) { return $false }
    try {
        $actualPath = [IO.Path]::GetFullPath($Actual)
        $expectedPath = [IO.Path]::GetFullPath($Expected)
        return [string]::Equals(
            $actualPath,
            $expectedPath,
            [StringComparison]::OrdinalIgnoreCase
        )
    } catch {
        return [string]::Equals(
            $Actual,
            $Expected,
            [StringComparison]::OrdinalIgnoreCase
        )
    }
}

function Test-CorrectRegistration {
    param(
        [object]$Registration,
        [string]$PythonPath
    )

    if (-not $Registration -or -not $Registration.transport) { return $false }
    if ($Registration.PSObject.Properties['enabled'] -and -not $Registration.enabled) {
        return $false
    }
    $transport = $Registration.transport
    if ($transport.type -ne 'stdio') { return $false }
    if (-not (Test-SamePath $transport.command $PythonPath)) { return $false }
    $registeredArguments = @($transport.args)
    $expectedArguments = @('-m', 'cdxml_toolkit.mcp_runtime', '--profile', 'codex')
    if ($registeredArguments.Count -ne $expectedArguments.Count) { return $false }
    for ($index = 0; $index -lt $expectedArguments.Count; $index++) {
        if ([string]$registeredArguments[$index] -ne $expectedArguments[$index]) {
            return $false
        }
    }

    $requiredEnvironment = [ordered]@{
        TF_CPP_MIN_LOG_LEVEL = '3'
        TF_ENABLE_ONEDNN_OPTS = '0'
    }
    if (-not $transport.env) { return $false }
    foreach ($entry in $requiredEnvironment.GetEnumerator()) {
        $property = $transport.env.PSObject.Properties[$entry.Key]
        if (-not $property -or [string]$property.Value -ne $entry.Value) {
            return $false
        }
    }
    return $true
}

function Get-CurrentRegistration {
    $result = Invoke-CodexCommand @('mcp', 'get', 'cdxml-toolkit', '--json')
    if ($result.ExitCode -ne 0) {
        if (
            $result.Output -match
            '(?i)(not\s+found|does\s+not\s+exist|unknown\s+mcp\s+server|no\s+mcp\s+server\s+named)'
        ) {
            return $null
        }
        throw "codex mcp get failed with exit code $($result.ExitCode); output was withheld to protect stored environment values."
    }
    try {
        return $result.Output | ConvertFrom-Json
    } catch {
        throw 'codex mcp get returned invalid JSON; output was withheld to protect stored environment values.'
    }
}

function Invoke-Configuration {
    $discovery = Invoke-RuntimeDiscovery
    $pythonPath = [IO.Path]::GetFullPath([string]$discovery.python.path)
    $skillPath = [IO.Path]::GetFullPath([string]$discovery.skill_root.path)
    # Windows PowerShell can turn benign native stderr into a terminating error.
    # Determine probe success from its exit code, retaining stderr for failures.
    $savedErrorPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $validationOutput = & $pythonPath -m cdxml_toolkit.mcp_runtime --help 2>&1
        $validationExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $savedErrorPreference
    }
    if ($validationExitCode -ne 0) {
        $detail = ($validationOutput | Out-String).Trim()
        throw "MCP server import validation failed with exit code $validationExitCode`: $detail"
    }

    if (-not $ConfigPath) {
        $codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
        $script:ConfigPath = Join-Path $codexHome 'config.toml'
    }
    $resolvedConfigPath = [IO.Path]::GetFullPath($ConfigPath)
    if ([IO.Path]::GetFileName($resolvedConfigPath) -ne 'config.toml') {
        throw "ConfigPath must name config.toml: $resolvedConfigPath"
    }

    $previousCodexHome = $env:CODEX_HOME
    $env:CODEX_HOME = Split-Path -Parent $resolvedConfigPath
    try {
        if (-not (Get-Command $CodexCommand -ErrorAction SilentlyContinue)) {
            throw "Codex command not found: $CodexCommand"
        }

        $current = Get-CurrentRegistration
        $isCorrect = Test-CorrectRegistration $current $pythonPath
        $proposal = [ordered]@{
            apply = [bool]$Apply
            python = $pythonPath
            skill_root = $skillPath
            server_module = 'cdxml_toolkit.mcp_runtime'
            profile = 'codex'
            config = $resolvedConfigPath
            command = "`"$pythonPath`" -m cdxml_toolkit.mcp_runtime.codex_config --config `"$resolvedConfigPath`" --python `"$pythonPath`""
            status = if ($isCorrect) { 'unchanged' } else { 'proposal' }
        }

        if ($isCorrect -or -not $Apply) {
            $proposal | ConvertTo-Json -Depth 4
            return
        }

        if (-not $PSCmdlet.ShouldProcess(
            $resolvedConfigPath,
            'Register the cdxml-toolkit MCP server'
        )) {
            $proposal.status = 'whatif'
            $proposal | ConvertTo-Json -Depth 4
            return
        }

        $hadConfig = Test-Path -LiteralPath $resolvedConfigPath -PathType Leaf
        $baselineFingerprint = Get-ConfigFingerprint $resolvedConfigPath
        $backup = $null
        if ($hadConfig) {
            $stamp = Get-Date -Format 'yyyyMMdd-HHmmssfff'
            $backup = "$resolvedConfigPath.chemdraw-$stamp-$([guid]::NewGuid().ToString('N')).bak"
            Copy-Item -LiteralPath $resolvedConfigPath -Destination $backup -Force
            if ((Get-ConfigFingerprint $resolvedConfigPath) -ne $baselineFingerprint) {
                throw 'config.toml changed while its backup was being created; no mutation was attempted.'
            }
        }

        $lastKnownFingerprint = $baselineFingerprint
        try {
            if ((Get-ConfigFingerprint $resolvedConfigPath) -ne $lastKnownFingerprint) {
                throw 'config.toml changed before MCP registration; no mutation was attempted.'
            }
            $updateArguments = @(
                '-m', 'cdxml_toolkit.mcp_runtime.codex_config',
                '--config', $resolvedConfigPath,
                '--python', $pythonPath
            )
            if ($hadConfig) {
                $updateArguments += @('--expected-sha256', $baselineFingerprint)
            }
            $updateOutput = & $pythonPath @updateArguments 2>&1
            $updateExitCode = $LASTEXITCODE
            if ($updateExitCode -ne 0) {
                $detail = ($updateOutput | Out-String).Trim()
                throw "MCP config update failed with exit code $updateExitCode`: $detail"
            }
            $lastKnownFingerprint = Get-ConfigFingerprint $resolvedConfigPath

            $verified = Get-CurrentRegistration
            if (-not (Test-CorrectRegistration $verified $pythonPath)) {
                throw 'The written MCP registration did not match the requested command.'
            }

            $proposal.backup = $backup
            $proposal.status = 'applied'
            $proposal | ConvertTo-Json -Depth 4
        } catch {
            $originalFailure = $_.Exception.Message
            try {
                $currentFingerprint = Get-ConfigFingerprint $resolvedConfigPath
                if ($currentFingerprint -ne $lastKnownFingerprint) {
                    $backupDetail = if ($backup) { " Backup remains at $backup." } else { '' }
                    throw (
                        'MCP registration failed; config.toml changed concurrently or during ' +
                        'the failed command and was not overwritten.' + $backupDetail + ' ' +
                        $originalFailure
                    )
                }
                if ($backup) {
                    Copy-Item -LiteralPath $backup -Destination $resolvedConfigPath -Force
                    throw "MCP registration failed; config was restored from $backup. $originalFailure"
                }
                if (-not $hadConfig -and (Test-Path -LiteralPath $resolvedConfigPath)) {
                    Remove-Item -LiteralPath $resolvedConfigPath -Force
                }
                throw "MCP registration failed; the absent config state was restored. $originalFailure"
            } catch {
                if (
                    $_.Exception.Message -like 'MCP registration failed;*restored*' -or
                    $_.Exception.Message -like 'MCP registration failed;*not overwritten*'
                ) {
                    throw
                }
                throw "MCP registration failed and automatic restore also failed. $originalFailure Restore error: $($_.Exception.Message)"
            }
        }
    } finally {
        if ($null -eq $previousCodexHome) {
            Remove-Item Env:CODEX_HOME -ErrorAction SilentlyContinue
        } else {
            $env:CODEX_HOME = $previousCodexHome
        }
    }
}

Invoke-Configuration
