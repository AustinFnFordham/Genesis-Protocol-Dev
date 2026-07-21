# Genesis Protocol — Platinum Loop Runner (run on the RTX machine)
# Usage:
#   .\RUN_PLATINUM.ps1                 # platinum pass, wip mode, offline-only
#   .\RUN_PLATINUM.ps1 -PromoteToGold  # also promote passing files to gold
# Prereqs: Ollama running (store: B:\Ollama), python + jsonschema>=4.18, pyyaml, jsonpatch.

param(
    [switch]$PromoteToGold,
    [int]$MaxIterations = 10
)

$forge = 'E:\StarWars\SW5e_Data_Hub\forge_v3'
Set-Location $forge

# category -> validation profile
$targets = [ordered]@{
    'data/wip/factions'   = 'faction_core'
    'data/wip/feats'      = 'feat_core'
    'data/wip/locations'  = 'location_core'
    'data/wip/approaches' = 'approach_core'
    'data/wip/assets'     = 'asset_core'
    'data/wip/planets'    = 'planet_core'
    'data/wip/species'    = 'species_core'
}

$log = "logs\platinum_run_$(Get-Date -Format yyyyMMdd_HHmmss).log"
New-Item -ItemType Directory -Force -Path logs | Out-Null
"Platinum run started $(Get-Date)" | Tee-Object $log

foreach ($t in $targets.Keys) {
    $prof = $targets[$t]
    "=== $t (profile: $prof) ===" | Tee-Object $log -Append
    $args = @('forge.py','platinum','--path',$t,'--profile',$prof,'--mode','wip',
              '--batch','--offline-only','--max-iterations',$MaxIterations,'--json')
    if ($PromoteToGold) { $args += '--promote-to-gold' }
    python @args 2>&1 | Tee-Object $log -Append
}

"Platinum run finished $(Get-Date)" | Tee-Object $log -Append
Write-Host "`nDone. Log: $forge\$log"
Write-Host "Next: python forge.py validate --path data/wip --mode wip  (confirm blocker burn-down)"
