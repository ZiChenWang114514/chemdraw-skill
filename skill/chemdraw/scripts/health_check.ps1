[CmdletBinding()]
param(
    [string]$Python,
    [string]$ReferenceRoot,
    [string]$CodexCommand = 'codex',
    [switch]$CheckCodex,
    [switch]$SkipNativeChemDraw,
    [switch]$SkipOffice,
    [ValidateRange(1, 3600)]
    [int]$CommandTimeoutSeconds = 300
)

$ErrorActionPreference = 'Stop'
$failures = [System.Collections.Generic.List[string]]::new()
$discoveryScript = Join-Path $PSScriptRoot 'runtime_discovery.py'
$diagnosticsScript = Join-Path $PSScriptRoot 'runtime_diagnostics.py'

if ($SkipNativeChemDraw) {
    Write-Warning 'Native ChemDraw checks skipped by -SkipNativeChemDraw: native PNG and Office OLE probes will not run'
} elseif ($SkipOffice) {
    Write-Warning 'Office OLE probes skipped by -SkipOffice: native ChemDraw PNG and ChemScript probes will still run'
}

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

function ConvertTo-NativeArgument {
    param([AllowEmptyString()][string]$Value)

    if ($null -eq $Value -or $Value.Length -eq 0) { return '""' }
    if ($Value -notmatch '[\s"]') { return $Value }
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}

function Join-NativeArguments {
    param([string[]]$Arguments)
    return (($Arguments | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' ')
}

function Stop-NativeProcessTree {
    param([int]$ProcessId)

    $taskkillPath = Join-Path $env:SystemRoot 'System32\taskkill.exe'
    if (Test-Path -LiteralPath $taskkillPath -PathType Leaf) {
        $info = New-Object System.Diagnostics.ProcessStartInfo
        $info.FileName = $taskkillPath
        $info.Arguments = "/PID $ProcessId /T /F"
        $info.UseShellExecute = $false
        $info.CreateNoWindow = $true
        $info.RedirectStandardOutput = $true
        $info.RedirectStandardError = $true
        $killer = New-Object System.Diagnostics.Process
        $killer.StartInfo = $info
        try {
            if ($killer.Start()) {
                if (-not $killer.WaitForExit(5000)) {
                    try { $killer.Kill() } catch { }
                }
            }
        } catch { }
        finally { $killer.Dispose() }
    }
}

function Invoke-BoundedNative {
    param(
        [Parameter(Mandatory)]
        [string]$FilePath,
        [string[]]$Arguments = @(),
        [int]$TimeoutSeconds = $CommandTimeoutSeconds
    )

    $resolved = Get-Command $FilePath -ErrorAction SilentlyContinue
    if (-not $resolved) {
        return [pscustomobject]@{
            ExitCode = -1
            StdOut = ''
            StdErr = ''
            TimedOut = $false
            LaunchError = "Command not found: $FilePath"
        }
    }
    $commandPath = if ($resolved.Path) { $resolved.Path } else { $resolved.Source }
    $extension = [IO.Path]::GetExtension($commandPath).ToLowerInvariant()
    $effectiveCommand = $commandPath
    $effectiveArguments = @($Arguments)
    if ($extension -eq '.ps1') {
        $pwshPath = Join-Path $PSHOME 'pwsh.exe'
        $windowsPowerShellPath = Join-Path $PSHOME 'powershell.exe'
        if (Test-Path -LiteralPath $pwshPath -PathType Leaf) {
            $effectiveCommand = $pwshPath
        } elseif (Test-Path -LiteralPath $windowsPowerShellPath -PathType Leaf) {
            $effectiveCommand = $windowsPowerShellPath
        } else {
            return [pscustomobject]@{
                ExitCode = -1
                StdOut = ''
                StdErr = ''
                TimedOut = $false
                LaunchError = 'No PowerShell host executable exists under PSHOME'
            }
        }
        $effectiveArguments = @(
            '-NoLogo', '-NoProfile', '-NonInteractive',
            '-ExecutionPolicy', 'Bypass', '-File', $commandPath
        ) + $effectiveArguments
    } elseif ($extension -in @('.cmd', '.bat')) {
        $innerCommand = Join-NativeArguments (@($commandPath) + $effectiveArguments)
        $effectiveCommand = $env:ComSpec
        $effectiveArguments = @('/d', '/s', '/c', $innerCommand)
    }

    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $effectiveCommand
    $info.Arguments = Join-NativeArguments $effectiveArguments
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.WorkingDirectory = $PSScriptRoot

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $info
    try {
        try {
            if (-not $process.Start()) {
                throw "Process did not start: $effectiveCommand"
            }
        } catch {
            return [pscustomobject]@{
                ExitCode = -1
                StdOut = ''
                StdErr = ''
                TimedOut = $false
                LaunchError = $_.Exception.Message
            }
        }

        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            Stop-NativeProcessTree $process.Id
            try {
                if (-not $process.HasExited) { $process.Kill() }
            } catch { }
            try { $process.WaitForExit(5000) | Out-Null } catch { }
            $stdout = if ($stdoutTask.IsCompleted) { $stdoutTask.Result } else { '' }
            $stderr = if ($stderrTask.IsCompleted) { $stderrTask.Result } else { '' }
            return [pscustomobject]@{
                ExitCode = -1
                StdOut = $stdout
                StdErr = $stderr
                TimedOut = $true
                LaunchError = $null
            }
        }
        $process.WaitForExit()
        return [pscustomobject]@{
            ExitCode = $process.ExitCode
            StdOut = $stdoutTask.Result
            StdErr = $stderrTask.Result
            TimedOut = $false
            LaunchError = $null
        }
    } finally {
        $process.Dispose()
    }
}

function Add-CommandFailure {
    param(
        [object]$Result,
        [string]$Description,
        [int]$TimeoutSeconds = $CommandTimeoutSeconds
    )

    if ($Result.TimedOut) {
        $failures.Add("$Description timed out after $TimeoutSeconds seconds")
        return
    }
    if ($Result.LaunchError) {
        $failures.Add("$Description could not start: $($Result.LaunchError)")
        return
    }
    if ($Result.ExitCode -ne 0) {
        $detail = $Result.StdErr.Trim()
        if (-not $detail) { $detail = $Result.StdOut.Trim() }
        if ($detail.Length -gt 2000) { $detail = $detail.Substring(0, 2000) }
        $suffix = if ($detail) { ": $detail" } else { '' }
        $failures.Add("$Description failed with exit code $($Result.ExitCode)$suffix")
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
    return $null
}

function Get-ManagedInventoryFiles {
    param([string]$Root)

    $files = @{}
    $indexPath = Join-Path $Root 'toolkit-public-inventory.md'
    if (Test-Path -LiteralPath $indexPath -PathType Leaf) {
        $files['toolkit-public-inventory.md'] = $indexPath
    }
    $inventoryRoot = Join-Path $Root 'inventory'
    if (Test-Path -LiteralPath $inventoryRoot -PathType Container) {
        foreach ($file in Get-ChildItem -LiteralPath $inventoryRoot -Filter '*.md' -Recurse -File) {
            $relative = $file.FullName.Substring($Root.Length).TrimStart('\', '/')
            $files[$relative.Replace('\', '/')] = $file.FullName
        }
    }
    return $files
}

function Compare-ManagedInventoryFiles {
    param(
        [string]$ExpectedRoot,
        [string]$GeneratedRoot
    )

    $expected = Get-ManagedInventoryFiles $ExpectedRoot
    $generated = Get-ManagedInventoryFiles $GeneratedRoot
    foreach ($relative in @($expected.Keys | Sort-Object)) {
        if (-not $generated.ContainsKey($relative)) {
            $failures.Add("Toolkit public interface inventory has obsolete managed file: $relative")
        }
    }
    foreach ($relative in @($generated.Keys | Sort-Object)) {
        if (-not $expected.ContainsKey($relative)) {
            $failures.Add("Toolkit public interface inventory is missing managed file: $relative")
            continue
        }
        $expectedHash = Get-Sha256Hex -LiteralPath $expected[$relative]
        $generatedHash = Get-Sha256Hex -LiteralPath $generated[$relative]
        if ($expectedHash -ne $generatedHash) {
            $failures.Add("Toolkit public interface inventory is stale: $relative")
        }
    }
}

$bootstrap = Get-DiscoveryBootstrap
$discovery = $null
if (-not $bootstrap) {
    $failures.Add('A bootstrap Python was not found for runtime discovery')
} else {
    $discoveryArguments = @($bootstrap.Arguments) + @($discoveryScript, '--json')
    if ($Python) { $discoveryArguments += @('--python', $Python) }
    $discoveryResult = Invoke-BoundedNative `
        -FilePath $bootstrap.Command `
        -Arguments $discoveryArguments
    Add-CommandFailure $discoveryResult 'Runtime discovery'
    if ($discoveryResult.ExitCode -eq 0 -and -not $discoveryResult.TimedOut) {
        try {
            $discovery = $discoveryResult.StdOut | ConvertFrom-Json
        } catch {
            $failures.Add("Runtime discovery returned invalid JSON: $($_.Exception.Message)")
        }
    }
}

if ($discovery) {
    $pythonPath = [string]$discovery.python.path
    $commands = @(
        [pscustomobject]@{
            Arguments = @('-c', "import cdxml_toolkit, mcp, rdkit, win32com.client; print('Python packages: OK')")
            Description = 'Required Python package import'
        },
        [pscustomobject]@{
            Arguments = @('-m', 'pip', 'check')
            Description = 'pip dependency check'
        }
    )
    foreach ($command in $commands) {
        $result = Invoke-BoundedNative -FilePath $pythonPath -Arguments $command.Arguments
        Add-CommandFailure $result $command.Description
    }

    $diagnosticArguments = @($diagnosticsScript, '--json')
    if (-not $SkipNativeChemDraw) {
        $diagnosticArguments += @('--native-probe')
        if (-not $SkipOffice) {
            $diagnosticArguments += @('--office-probe')
        }
    }
    $diagnosticTimeoutSeconds = 270
    $diagnosticResult = Invoke-BoundedNative `
        -FilePath $pythonPath `
        -Arguments $diagnosticArguments `
        -TimeoutSeconds $diagnosticTimeoutSeconds
    Add-CommandFailure $diagnosticResult 'Runtime capability diagnostics' `
        -TimeoutSeconds $diagnosticTimeoutSeconds
    if ($diagnosticResult.StdOut.Trim()) {
        try {
            $diagnostics = $diagnosticResult.StdOut | ConvertFrom-Json
            foreach ($property in $diagnostics.outputs.capabilities.PSObject.Properties) {
                Write-Output ("Capability {0}: {1}" -f $property.Name, $property.Value.status)
            }
            foreach ($warning in @($diagnostics.warnings)) {
                if ($warning) { Write-Warning ([string]$warning) }
            }
            if (-not $diagnostics.ok -and $diagnosticResult.ExitCode -eq 0) {
                $failures.Add('Runtime capability diagnostics reported required capabilities unavailable')
            }
        } catch {
            $failures.Add("Runtime capability diagnostics returned invalid JSON: $($_.Exception.Message)")
        }
    }

    $pythonFiles = @(
        Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.py' -File |
            Select-Object -ExpandProperty FullName
    )
    $compile = Invoke-BoundedNative `
        -FilePath $pythonPath `
        -Arguments (@('-m', 'py_compile') + $pythonFiles)
    Add-CommandFailure $compile 'ChemDraw Skill Python compilation'

    $tests = Invoke-BoundedNative `
        -FilePath $pythonPath `
        -Arguments @('-m', 'unittest', 'discover', '-s', $PSScriptRoot, '-p', 'test_*.py')
    Add-CommandFailure $tests 'ChemDraw Skill tests'

    if (-not $ReferenceRoot) {
        $ReferenceRoot = Join-Path $PSScriptRoot '..\references'
    }
    $ReferenceRoot = [IO.Path]::GetFullPath($ReferenceRoot)
    if (-not (Test-Path -LiteralPath $ReferenceRoot -PathType Container)) {
        $failures.Add("Reference root not found: $ReferenceRoot")
    } else {
        $checkRoot = [IO.Path]::GetFullPath(
            (Join-Path $env:TEMP ("chemdraw-health-check-" + [guid]::NewGuid().ToString('N')))
        )
        $tempRoot = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
        if (-not ($checkRoot + '\').StartsWith(
            $tempRoot,
            [StringComparison]::OrdinalIgnoreCase
        )) {
            throw "Health-check directory escaped TEMP: $checkRoot"
        }
        New-Item -ItemType Directory -Path $checkRoot -Force | Out-Null
        try {
            $generatedReferences = Join-Path $checkRoot 'references'
            $inventory = Invoke-BoundedNative `
                -FilePath $pythonPath `
                -Arguments @(
                    (Join-Path $PSScriptRoot 'audit_toolkit_interfaces.py'),
                    '--output-dir', $generatedReferences
                )
            Add-CommandFailure $inventory 'Toolkit interface inventory generation'
            if ($inventory.ExitCode -eq 0 -and -not $inventory.TimedOut) {
                Compare-ManagedInventoryFiles $ReferenceRoot $generatedReferences
            }

            $generatedSignatures = Join-Path $generatedReferences 'mcp-signatures.md'
            $signatures = Invoke-BoundedNative `
                -FilePath $pythonPath `
                -Arguments @(
                    (Join-Path $PSScriptRoot 'generate_tool_reference.py'),
                    '--output', $generatedSignatures
                )
            Add-CommandFailure $signatures 'MCP signature generation'
            if ($signatures.ExitCode -eq 0 -and -not $signatures.TimedOut) {
                $expectedSignatures = Join-Path $ReferenceRoot 'mcp-signatures.md'
                if (-not (Test-Path -LiteralPath $expectedSignatures -PathType Leaf)) {
                    $failures.Add('Generated MCP signatures are missing: mcp-signatures.md')
                } elseif (
                    (Get-Sha256Hex -LiteralPath $expectedSignatures) -ne
                    (Get-Sha256Hex -LiteralPath $generatedSignatures)
                ) {
                    $failures.Add('Generated MCP signatures are stale: mcp-signatures.md')
                }
            }
        } finally {
            Remove-Item -LiteralPath $checkRoot -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

if ($CheckCodex) {
    $clientRegistration = Invoke-BoundedNative `
        -FilePath $CodexCommand `
        -Arguments @('mcp', 'get', 'cdxml-toolkit')
    Add-CommandFailure $clientRegistration 'Codex MCP registration check'
}

if ($failures.Count -gt 0) {
    foreach ($failure in $failures) {
        [Console]::Error.WriteLine("ERROR: $failure")
    }
    exit 1
}

Write-Output 'ChemDraw agent integration: OK'
