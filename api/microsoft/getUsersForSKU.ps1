# Connect to Microsoft Graph
$ClientId = $Env:ClientId.Trim()
$TenantId = $Env:TenantId.Trim()
$ClientSecret = $Env:ClientSecret.Trim()

# Convert the Client Secret to a Secure String
$SecureClientSecret = ConvertTo-SecureString -String $ClientSecret -AsPlainText -Force

# Create a PSCredential Object Using the Client ID and Secure Client Secret
$CSC = New-Object -TypeName System.Management.Automation.PSCredential -ArgumentList $ClientId, $SecureClientSecret
# Connect to Microsoft Graph Using the Tenant ID and Client Secret Credential
Connect-MgGraph -TenantId $TenantId -ClientSecretCredential $CSC -NoWelcome

# Get all license SKUs in the tenant
$skus = Get-MgSubscribedSku

# Initialize arrays for results
$licenseSummary = @()
$licenseAssignments = @()

# Process each SKU
foreach ($sku in $skus) {
    $skuId = $sku.SkuId
    $skuPartNumber = $sku.SkuPartNumber
    $skuName = $sku.SkuPartNumber
    $totalUnits = $sku.PrepaidUnits.Enabled
    $assignedUnits = $sku.ConsumedUnits
    $availableUnits = $totalUnits - $assignedUnits

    # Add to license summary output
    $licenseSummary += [PSCustomObject]@{
        SKU              = $skuName
        SkuId            = $skuId
        TotalLicenses    = $totalUnits
        AssignedLicenses = $assignedUnits
        UnassignedLicenses = $availableUnits
    }

    # Get users assigned to this SKU
    $users = Get-MgUser -All -Filter "assignedLicenses/any(x:x/skuId eq $skuId)" -Property UserPrincipalName

    foreach ($user in $users) {
        $licenseAssignments += [PSCustomObject]@{
            SKU               = $skuName
            SkuId             = $skuId
            UserPrincipalName = $user.UserPrincipalName
        }
    }
}

$scriptDir = $PSScriptRoot
$projectRoot = (Get-Item $scriptDir).Parent.Parent.FullName

# Build output paths
$summaryPath     = Join-Path $projectRoot 'files/ms/LicenseSummary.csv'
$assignmentsPath = Join-Path $projectRoot 'files/ms/LicenseAssignments.csv'

# Extract the parent directory from the path
$outputDirectory = Split-Path -Parent $summaryPath

# Check if the directory exists; if not, create it
if (-not (Test-Path -Path $outputDirectory)) {
    Write-Host "Directory '$outputDirectory' not found. Creating it now..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

# Export to CSVs (using -Force to ensure overwrite if exists, and creation if not)
$licenseSummary | Export-Csv -Path $summaryPath -NoTypeInformation -Force
$licenseAssignments | Export-Csv -Path $assignmentsPath -NoTypeInformation -Force

Write-Host "Export complete."
Write-Host "Summary saved to: $summaryPath"
Write-Host "Assignments saved to: $assignmentsPath"