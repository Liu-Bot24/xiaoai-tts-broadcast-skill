[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $ToolArguments
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$ToolPath = Join-Path $PSScriptRoot 'xiaoai-tts'

if (-not (Test-Path -LiteralPath $ToolPath -PathType Leaf)) {
    [Console]::Error.WriteLine("ERROR: tool not found: $ToolPath")
    exit 1
}

$Candidates = @(
    [pscustomobject]@{ Name = 'python'; Prefix = @() }
    [pscustomobject]@{ Name = 'python3'; Prefix = @() }
    [pscustomobject]@{ Name = 'py'; Prefix = @('-3') }
)

foreach ($Candidate in $Candidates) {
    $Command = Get-Command -Name $Candidate.Name -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $Command) {
        continue
    }

    [string[]] $PrefixArguments = @($Candidate.Prefix)
    try {
        & $Command.Source @PrefixArguments -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 8)' *> $null
    }
    catch {
        continue
    }
    if ($LASTEXITCODE -ne 0) {
        continue
    }

    & $Command.Source @PrefixArguments $ToolPath @ToolArguments
    $ToolExitCode = $LASTEXITCODE
    exit $ToolExitCode
}

[Console]::Error.WriteLine('ERROR: Python 3.8 or newer was not found in PATH.')
exit 1
