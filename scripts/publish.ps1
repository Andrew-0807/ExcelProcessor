# Run on the DEV PC. Publishes app/ + scripts/ to a read-only SMB share the
# client PC pulls from. Run once with -Setup to create the share, then plain
# to publish. Client side: scripts/update.bat.
param([switch]$Setup)

$repo  = Split-Path $PSScriptRoot -Parent
$share = "C:\MomAppDist"

if ($Setup) {
    New-Item -ItemType Directory -Force $share | Out-Null
    New-SmbShare -Name MomAppDist -Path $share -ReadAccess Everyone
    Write-Host "Share created (read-only). Restrict it to the Radmin adapter in Windows Firewall."
    return
}

robocopy "$repo\app"     "$share\app"     /MIR /XD __pycache__ /NP /NFL /NDL
robocopy "$repo\scripts" "$share\scripts" /MIR /XD __pycache__ /NP /NFL /NDL
if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE)" }
Write-Host "Published. Client runs update.bat."
