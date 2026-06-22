param(
    [string]$OutputPath = "release\local-finance-clean.zip"
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("local-finance-clean-" + [System.Guid]::NewGuid().ToString("N"))
$dest = Join-Path $root $OutputPath

$excludedRelative = @(
    ".git",
    ".ai-bridge",
    "backend\.venv",
    "frontend\node_modules",
    "frontend\dist",
    "frontend\=",
    "frontend\tsconfig.tsbuildinfo",
    "frontend\tsconfig.node.tsbuildinfo",
    "frontend\vite.config.js",
    "frontend\vite.config.d.ts",
    "data\finance.sqlite3",
    "data\finance.sqlite3-wal",
    "data\finance.sqlite3-shm",
    "data\backups",
    "data\imports",
    "data\exports",
    "data\logs",
    "data\secrets",
    "release"
)

function Test-IsExcluded([string]$FullName) {
    $relative = [System.IO.Path]::GetRelativePath($root, $FullName)
    foreach ($excluded in $excludedRelative) {
        if ($relative -eq $excluded -or $relative.StartsWith($excluded + [System.IO.Path]::DirectorySeparatorChar)) {
            return $true
        }
    }
    return $false
}

New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
if (Test-Path $dest) { Remove-Item $dest -Force }
New-Item -ItemType Directory -Force $tempRoot | Out-Null

try {
    Get-ChildItem $root -Force | ForEach-Object {
        if (-not (Test-IsExcluded $_.FullName)) {
            Copy-Item $_.FullName -Destination $tempRoot -Recurse -Force
        }
    }

    Get-ChildItem $tempRoot -Recurse -Force | Where-Object {
        $_.Name -in @("__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache") -or
        $_.Name -like "*.pyc" -or
        $_.Name -like "*.sqlite3" -or
        $_.Name -like "*.sqlite3-wal" -or
        $_.Name -like "*.sqlite3-shm" -or
        $_.Name -like "*.log"
    } | Remove-Item -Recurse -Force

    Compress-Archive -Path (Join-Path $tempRoot "*") -DestinationPath $dest -CompressionLevel Optimal
    Write-Host "Created clean distributable ZIP: $dest"
}
finally {
    if (Test-Path $tempRoot) { Remove-Item $tempRoot -Recurse -Force }
}
