param(
    [string]$EnvPath = ".env"
)

$resolved = Resolve-Path -LiteralPath $EnvPath -ErrorAction SilentlyContinue
if (-not $resolved) {
    Write-Error "Env file not found: $EnvPath"
    exit 2
}

Get-Content -LiteralPath $resolved.Path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
        return
    }

    $parts = $line.Split("=", 2)
    $key = $parts[0].Trim()
    $value = $parts[1].Trim().Trim('"').Trim("'")
    if ($key) {
        Set-Item -Path "Env:$key" -Value $value
    }
}

Write-Host "Loaded GitHub environment variables from $($resolved.Path)"
Write-Host "Run: python scripts/check_github_env.py --env `"$($resolved.Path)`""
