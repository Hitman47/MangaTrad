$ErrorActionPreference = "Stop"

Write-Host "Cleaning generated Python/GitHub-irrelevant files..."

$patterns = @(
    "__pycache__",
    ".pytest_cache",
    "*.egg-info",
    "build",
    "dist"
)

foreach ($pattern in $patterns) {
    Get-ChildItem -Path . -Recurse -Force -Filter $pattern -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "Removing $($_.FullName)"
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
    }
}

Get-ChildItem -Path . -Recurse -Force -Include *.pyc,*.pyo -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "Removing $($_.FullName)"
    Remove-Item -LiteralPath $_.FullName -Force
}

Write-Host "Done."
