# Connect to Microsoft Graph
$ClientId = $Env:ClientId
$TenantId = $Env:TenantId
$ClientSecret = $Env:ClientSecret

# Convert the Client Secret to a Secure String
$SecureClientSecret = ConvertTo-SecureString -String $ClientSecret -AsPlainText -Force

# Create a PSCredential Object Using the Client ID and Secure Client Secret
$ClientSecretCredential = New-Object -TypeName System.Management.Automation.PSCredential -ArgumentList $ClientId, $SecureClientSecret
# Connect to Microsoft Graph Using the Tenant ID and Client Secret Credential
Connect-MgGraph -TenantId $TenantId -ClientSecretCredential $ClientSecretCredential -NoWelcome

# Define the file paths
$scriptDir = $PSScriptRoot
$projectRoot = (Get-Item $scriptDir).Parent.Parent.FullName
$summaryPath     = Join-Path $projectRoot 'files/ms/Windows_DiscoveredApps_MultiApp.csv'

# Read and parse the JSON file
$appConfig = Join-Path $projectRoot 'app_config.json'
$json = Get-Content $appConfig | ConvertFrom-Json

# Extract product names (keys)
$discoveredApps = $json.license | Select-Object -ExpandProperty "discovered-apps"
$targetAppNames = $discoveredApps.PRODUCT_TO_LICENSE_ID.PSObject.Properties.Name

function Invoke-WithRetry {
    param (
        [scriptblock]$Script,
        [int]$MaxRetries = 5,
        [int]$DelaySeconds = 5
    )

	Start-Sleep -Seconds 1
    $attempt = 0
    while ($attempt -lt $MaxRetries) {
        try {
            return & $Script
        } catch {
            $attempt++
            Write-Warning "Attempt $attempt failed. Retrying in $DelaySeconds seconds..."
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    Write-Error "All $MaxRetries attempts failed."
    return $null
}

# Get all discovered apps
$allApps = Get-MgDeviceManagementDetectedApp -All

# Combine keywords into one regex string
$regex = ($targetAppNames -join "|")

# Filter apps based on exact match or substring (depending on prefix)
$filteredApps = $allApps | Where-Object {
    $displayName = $_.DisplayName
    foreach ($key in $targetAppNames) {
        if ($key.StartsWith("*")) {
            $substring = $key.Substring(1)
            if ($displayName.ToLower() -like "*$($substring.ToLower())*") { return $true }
        } else {
            if ($displayName.ToLower() -eq $key.ToLower()) { return $true }
        }
    }
    return $false
}


$filteredApps | Format-Table -AutoSize

# Step 3: Get device info for each matching app
$results = foreach ($app in $filteredApps) {
	Write-Host "Getting info for $($app.DisplayName) $($app.Version)"
    $appDevices = Invoke-WithRetry { Get-MgDeviceManagementDetectedAppManagedDevice -DetectedAppId $app.Id }
	if (-not $appDevices) { continue }
    foreach ($device in $appDevices) {
        if ($device.OperatingSystem -eq "Windows") {
            [PSCustomObject]@{
                Email       = $device.EmailAddress
                DeviceName  = $device.DeviceName
                AppName     = $app.DisplayName
                Version     = $app.Version
            }
        }
    }
}


# Extract the parent directory from the path
$outputDirectory = Split-Path -Parent $summaryPath

# Check if the directory exists; if not, create it
if (-not (Test-Path -Path $outputDirectory)) {
    Write-Host "Directory '$outputDirectory' not found. Creating it now..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

# Export to CSVs (using -Force to ensure overwrite if exists, and creation if not)
$results | Export-Csv -Path $summaryPath -NoTypeInformation -Force

Write-Host "Export complete."
Write-Host "Summary saved to: $summaryPath"