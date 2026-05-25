<#
.SYNOPSIS
  End-to-end provisioning for the KN Executive AI Showcase Foundry demo.

.DESCRIPTION
  Idempotent. Re-runs safely. Provisions in Switzerland North:
    - Resource group
    - Storage account (for Function App)
    - Linux Y1 Function App (Python 3.11) with calculate_reroute deployed
    - Microsoft Foundry resource (AIServices, S0)
    - gpt-5-mini GlobalStandard deployment
    - Microsoft.BotService provider registration (for M365 publish)
    - RBAC: Cognitive Services OpenAI Contributor on Foundry,
            Storage Blob Data Contributor on storage,
            Azure Bot Service Contributor on RG.

  Run from the workspace root with the CDX tenant selected:
    az account show   # must be ME-M365CPI98544940-jschneider-1

  After this script finishes:
    1. Open the Function URL printed at the end to verify it answers.
    2. Update Demo-Files\Foundry\reroute_function\openapi.yaml
       servers[0].url with the printed FUNCTION_URL.
    3. Run build-vector-store.py to create the Sentinel vector store.
    4. In ai.azure.com, create a Project under the Foundry resource,
       create a Prompt Agent, attach File Search (vector store) + the
       OpenAPI as a custom function, publish to M365 (Just you scope).

.NOTES
  Costs: gpt-5-mini GlobalStandard is pay-per-token, Y1 Function App is
  consumption (~0 EUR idle), Storage is GRS LRS (~few cents/day).
#>

[CmdletBinding()]
param(
    [string]$ResourceGroup = "rg-kn-foundry-demo",
    [string]$Location      = "switzerlandnorth",
    [string]$Prefix        = "knfdry",
    [string]$ModelName     = "gpt-5-mini",
    [string]$ModelVersion  = "2025-08-07",
    [int]   $ModelCapacity = 50
)

$ErrorActionPreference = "Stop"

# unique-ish suffix from the subscription id to avoid global name clashes
$sub = az account show --query id -o tsv
$suffix = ($sub -replace '-','').Substring(0,6).ToLower()
$storageName  = "st${Prefix}${suffix}"      # max 24, lowercase, alnum
$functionName = "func-${Prefix}-${suffix}"
$foundryName  = "ai-${Prefix}-${suffix}"

Write-Host "============================================================"
Write-Host " KN Foundry Demo Provisioning"
Write-Host "============================================================"
Write-Host "Subscription : $(az account show --query name -o tsv)"
Write-Host "Tenant       : $(az account show --query tenantId -o tsv)"
Write-Host "Region       : $Location"
Write-Host "RG           : $ResourceGroup"
Write-Host "Storage      : $storageName"
Write-Host "Function App : $functionName"
Write-Host "Foundry      : $foundryName"
Write-Host "Model        : $ModelName ($ModelVersion), capacity $ModelCapacity"
Write-Host ""

# 1. Providers (idempotent)
Write-Host "[1/8] Registering providers (BotService, CognitiveServices, Web, Storage)..."
foreach ($ns in @("Microsoft.BotService","Microsoft.CognitiveServices","Microsoft.Web","Microsoft.Storage")) {
    az provider register --namespace $ns --consent-to-permissions --only-show-errors | Out-Null
}

# 2. Resource group
Write-Host "[2/8] Resource group..."
az group create -n $ResourceGroup -l $Location --only-show-errors | Out-Null

# 3. Storage
Write-Host "[3/8] Storage account..."
az storage account create `
    -n $storageName -g $ResourceGroup -l $Location `
    --sku Standard_LRS --kind StorageV2 `
    --allow-blob-public-access false `
    --only-show-errors | Out-Null

# 4. Function App (Linux Y1 Consumption, Python 3.11)
Write-Host "[4/8] Function app..."
az functionapp create `
    -n $functionName -g $ResourceGroup `
    --storage-account $storageName `
    --consumption-plan-location $Location `
    --runtime python --runtime-version 3.11 `
    --functions-version 4 --os-type Linux `
    --only-show-errors | Out-Null

# 5. Deploy code via ZIP
Write-Host "[5/8] Packaging and deploying calculate_reroute..."
$fnSrc = Join-Path $PSScriptRoot "reroute_function"
$zip   = Join-Path $env:TEMP "reroute_function.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $fnSrc "*") -DestinationPath $zip -Force
az functionapp deployment source config-zip `
    -g $ResourceGroup -n $functionName --src $zip `
    --only-show-errors | Out-Null

# 6. Foundry resource (Cognitive Services kind=AIServices)
Write-Host "[6/8] Foundry (AIServices) resource..."
az cognitiveservices account create `
    -n $foundryName -g $ResourceGroup -l $Location `
    --kind AIServices --sku S0 `
    --custom-domain $foundryName `
    --assign-identity `
    --yes --only-show-errors | Out-Null

# 7. Model deployment
Write-Host "[7/8] Deploying $ModelName..."
az cognitiveservices account deployment create `
    -n $foundryName -g $ResourceGroup `
    --deployment-name $ModelName `
    --model-name $ModelName --model-version $ModelVersion --model-format OpenAI `
    --sku-name GlobalStandard --sku-capacity $ModelCapacity `
    --only-show-errors | Out-Null

# 8. RBAC (current user)
Write-Host "[8/8] RBAC assignments..."
$me = az ad signed-in-user show --query id -o tsv
$rgScope      = "/subscriptions/$sub/resourceGroups/$ResourceGroup"
$foundryScope = "$rgScope/providers/Microsoft.CognitiveServices/accounts/$foundryName"
$storageScope = "$rgScope/providers/Microsoft.Storage/storageAccounts/$storageName"

$roles = @(
    @{ name = "Cognitive Services OpenAI Contributor"; scope = $foundryScope },
    @{ name = "Cognitive Services Contributor";        scope = $foundryScope },
    @{ name = "Storage Blob Data Contributor";         scope = $storageScope },
    @{ name = "Azure Bot Service Contributor Role";    scope = $rgScope }
)
foreach ($r in $roles) {
    az role assignment create --assignee $me --role $r.name --scope $r.scope --only-show-errors 2>$null | Out-Null
}

# Outputs
$functionUrl   = "https://$functionName.azurewebsites.net/api/calculate_reroute"
$functionKey   = az functionapp function keys list -g $ResourceGroup -n $functionName --function-name calculate_reroute --query default -o tsv 2>$null
$foundryEndpoint = az cognitiveservices account show -n $foundryName -g $ResourceGroup --query "properties.endpoints.AIServices" -o tsv 2>$null
if (-not $foundryEndpoint) {
    $foundryEndpoint = az cognitiveservices account show -n $foundryName -g $ResourceGroup --query "properties.endpoint" -o tsv
}

Write-Host ""
Write-Host "============================================================"
Write-Host " DONE"
Write-Host "============================================================"
Write-Host "Function URL    : $functionUrl"
Write-Host "Function Key    : $functionKey"
Write-Host "Foundry name    : $foundryName"
Write-Host "Foundry endpoint: $foundryEndpoint"
Write-Host "Model deployed  : $ModelName"
Write-Host ""
Write-Host "NEXT STEPS:"
Write-Host "  1. Update openapi.yaml servers[0].url with:"
Write-Host "       $functionUrl".Replace("/calculate_reroute","")
Write-Host "  2. python build-vector-store.py --foundry $foundryName --rg $ResourceGroup"
Write-Host "  3. Open https://ai.azure.com -> create Project -> create Prompt Agent"
Write-Host ""
