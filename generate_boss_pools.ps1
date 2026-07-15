param(
    [string] $ManifestPath
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ManifestPath) {
    $ManifestPath = Join-Path (Split-Path -Parent $projectRoot) 'bl4-reference\share\manifest\drops.json'
}
if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "Drop manifest not found: $ManifestPath. Pass -ManifestPath with a compatible drops.json file."
}
$ManifestPath = (Resolve-Path -LiteralPath $ManifestPath).Path
$outputPath = Join-Path $projectRoot 'LootTreadmill\boss_pools.py'
$drops = (Get-Content -Raw -LiteralPath $ManifestPath | ConvertFrom-Json).drops |
    Where-Object { $_.source_type -eq 'Boss' }

function Normalize-Key([string] $Value) {
    if ($null -eq $Value) { $Value = '' }
    return (($Value -replace '(?i)_true$', '') -replace '(?i)[^a-z0-9]', '').ToLowerInvariant()
}

$records = foreach ($group in ($drops | Group-Object source)) {
    $source = [string]$group.Name
    $display = [string]($group.Group.source_display | Where-Object { $_ } | Select-Object -First 1)
    $aliases = @(
        Normalize-Key $source
        Normalize-Key $display
    ) | Where-Object { $_.Length -ge 4 } | Sort-Object -Unique
    if ($aliases.Count -eq 0) { continue }

    $pools = $group.Group |
        Sort-Object pool, gear_type -Unique |
        ForEach-Object { [pscustomobject]@{ pool = [string]$_.pool; gear = [string]$_.gear_type } }
    [pscustomobject]@{ aliases = $aliases; pools = $pools }
}

$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add('"""Generated from the current monokrome/bl4 v1.8 drops manifest."""')
$lines.Add('')
$lines.Add('BOSS_POOL_RECORDS = (')
foreach ($record in $records) {
    $aliasText = ($record.aliases | ForEach-Object { "        '$($_)'," }) -join "`n"
    $poolText = ($record.pools | ForEach-Object { "        ('$($_.pool)', '$($_.gear)')," }) -join "`n"
    $lines.Add('    (')
    $lines.Add('      (')
    $lines.Add($aliasText)
    $lines.Add('      ),')
    $lines.Add('      (')
    $lines.Add($poolText)
    $lines.Add('      ),')
    $lines.Add('    ),')
}
$lines.Add(')')
$lines.Add('')
$lines.Add('CLASS_MOD_POOLS = {')
$classTypes = [ordered]@{
    'dark_siren' = 'DARK_SIREN'
    'exo_soldier' = 'EXO_SOLDIER'
    'gravitar' = 'GRAVITAR'
    'paladin' = 'PALADIN'
}
foreach ($entry in $classTypes.GetEnumerator()) {
    $lines.Add("    '$($entry.Key)': (")
    $classPools = $drops |
        Where-Object { $_.gear_type -eq $entry.Value } |
        Select-Object -ExpandProperty pool -Unique |
        Sort-Object
    foreach ($pool in $classPools) { $lines.Add("        '$pool',") }
    $lines.Add('    ),')
}
$lines.Add("    # C4SH uses the same six-pool convention as each base Vault Hunter. These")
$lines.Add("    # RoboDealer names are convention-based until the reference manifest includes them.")
$lines.Add("    'robodealer': (")
foreach ($index in 1..6) { $lines.Add(("        'itempool_classmod_robodealer_05_legendary_{0:d2}_shiny'," -f $index)) }
$lines.Add('    ),')
$lines.Add('}')
$lines.Add('')
$lines.Add('FIRMWARE_DONOR_POOLS = {')
$lines.Add("    'Shields': ('itempool_shield_05_legendary',),")
$lines.Add("    'Repkits': ('itempool_repair_kit_05_legendary',),")
$lines.Add("    'Ordnance': ('itempool_grenade_gadget_05_legendary',),")
$lines.Add('}')

Set-Content -LiteralPath $outputPath -Value $lines -Encoding utf8
