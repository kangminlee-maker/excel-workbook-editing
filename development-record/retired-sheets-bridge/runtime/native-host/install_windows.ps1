$ErrorActionPreference = "Stop"

$HostName = "com.day1company.sheets_bridge"
$ExtensionOrigin = "chrome-extension://jahlkdjaokmjbipfhlhnjggcgjmpeiij/"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HostPath = Join-Path $ScriptDir "bin\sheets-bridge-native-host.cmd"
$ManifestDir = Join-Path $env:LOCALAPPDATA "Day1\ChromeSheetsBridge\NativeMessagingHosts"
$ManifestPath = Join-Path $ManifestDir "$HostName.json"
$RegistryPath = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$HostName"

if (-not (Test-Path $HostPath)) {
    throw "Native host wrapper not found: $HostPath"
}

New-Item -ItemType Directory -Force -Path $ManifestDir | Out-Null

$Manifest = [ordered]@{
    name = $HostName
    description = "Chrome Sheets Bridge native host for local review package persistence."
    path = $HostPath
    type = "stdio"
    allowed_origins = @($ExtensionOrigin)
}

$Manifest | ConvertTo-Json -Depth 5 | Set-Content -Path $ManifestPath -Encoding UTF8

New-Item -Force -Path $RegistryPath | Out-Null
Set-Item -Path $RegistryPath -Value $ManifestPath

Write-Output $ManifestPath
Write-Output $RegistryPath
