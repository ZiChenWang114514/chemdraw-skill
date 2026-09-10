[CmdletBinding()]
param(
    [string]$Python,
    [ValidateSet('core', 'native', 'chemscript', 'office', 'decimer')]
    [string[]]$Capabilities = @('core'),
    [switch]$Json,
    [switch]$SkipCodex,
    [switch]$CheckCodex,
    [switch]$SkipChemDraw,
    [switch]$SkipPythonPackages
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$checker = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot `
    '..\skill\chemdraw\scripts\check_prerequisites.ps1'))
if (-not (Test-Path -LiteralPath $checker -PathType Leaf)) {
    throw "Deployable prerequisite checker not found: $checker"
}

& $checker @PSBoundParameters
exit $LASTEXITCODE
