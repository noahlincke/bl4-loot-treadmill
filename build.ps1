param(
    [string] $OutputPath,
    [string] $PythonPath
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $OutputPath) {
    $OutputPath = Join-Path $projectRoot 'LootTreadmill.sdkmod'
}
$OutputPath = [IO.Path]::GetFullPath($OutputPath)

if (-not $PythonPath) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { $PythonPath = $python.Source }
}
if ($PythonPath) {
    & $PythonPath -m unittest discover -s (Join-Path $projectRoot 'tests') -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
}
else {
    Write-Warning 'Python was not found; packaging without running tests.'
}

$parent = Split-Path -Parent $OutputPath
if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent | Out-Null
}
if (Test-Path -LiteralPath $OutputPath) {
    Remove-Item -LiteralPath $OutputPath -Force
}

Add-Type -AssemblyName System.IO.Compression
$stream = [IO.File]::Open($OutputPath, [IO.FileMode]::CreateNew)
$archive = [IO.Compression.ZipArchive]::new(
    $stream,
    [IO.Compression.ZipArchiveMode]::Create
)
try {
    foreach ($name in @('__init__.py', 'profiles.py', 'boss_pools.py', 'pyproject.toml')) {
        $sourcePath = Join-Path $projectRoot (Join-Path 'LootTreadmill' $name)
        $entry = $archive.CreateEntry(
            "LootTreadmill/$name",
            [IO.Compression.CompressionLevel]::Optimal
        )
        $input = [IO.File]::OpenRead($sourcePath)
        $output = $entry.Open()
        try {
            $input.CopyTo($output)
        }
        finally {
            $output.Dispose()
            $input.Dispose()
        }
    }
}
finally {
    $archive.Dispose()
    $stream.Dispose()
}

Write-Output $OutputPath
