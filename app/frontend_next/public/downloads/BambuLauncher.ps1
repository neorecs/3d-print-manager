param(
    [Parameter(Position = 0)]
    [string]$ProtocolUrl,
    [switch]$Install,
    [string]$TrustedOrigin = "https://10.5.1.150:38503"
)

$ErrorActionPreference = "Stop"
$installDirectory = Join-Path $env:LOCALAPPDATA "3DPrintManager\BambuLauncher"
$installedScript = Join-Path $installDirectory "BambuLauncher.ps1"
$settingsKey = "HKCU:\Software\3DPrintManager\BambuLauncher"
$protocolKey = "HKCU:\Software\Classes\printmanager"

function Show-LauncherError([string]$Message) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($Message, "3D Print Manager", "OK", "Error") | Out-Null
}

function Find-BambuStudio {
    $registryPaths = @(
        "HKCU:\Software\Classes\bambustudio\shell\open\command",
        "Registry::HKEY_CLASSES_ROOT\bambustudio\shell\open\command"
    )
    foreach ($registryPath in $registryPaths) {
        if (Test-Path $registryPath) {
            $command = (Get-Item $registryPath).GetValue("")
            if ($command -match '^"([^"]+\.exe)"' -and (Test-Path $Matches[1])) { return $Matches[1] }
        }
    }

    $candidates = @(
        (Join-Path $env:ProgramFiles "Bambu Studio\bambu-studio.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Bambu Studio\bambu-studio.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Bambu Studio\bambu-studio.exe")
    )
    return $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}

if ($Install) {
    New-Item -ItemType Directory -Force -Path $installDirectory | Out-Null
    if ($PSCommandPath -ne $installedScript) {
        Copy-Item -Force -LiteralPath $PSCommandPath -Destination $installedScript
    }

    $origin = ([Uri]$TrustedOrigin).GetLeftPart([UriPartial]::Authority)
    New-Item -Force -Path $settingsKey | Out-Null
    Set-ItemProperty -Path $settingsKey -Name "TrustedOrigin" -Value $origin
    New-Item -Force -Path $protocolKey | Out-Null
    Set-Item -Path $protocolKey -Value "URL:3D Print Manager Bambu Launcher"
    New-ItemProperty -Force -Path $protocolKey -Name "URL Protocol" -Value "" | Out-Null
    New-Item -Force -Path "$protocolKey\DefaultIcon" | Out-Null
    New-Item -Force -Path "$protocolKey\shell\open\command" | Out-Null

    $powershell = Join-Path $PSHOME "powershell.exe"
    $command = '"{0}" -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{1}" "%1"' -f $powershell, $installedScript
    Set-Item -Path "$protocolKey\shell\open\command" -Value $command
    $bambuStudio = Find-BambuStudio
    if ($bambuStudio) { Set-Item -Path "$protocolKey\DefaultIcon" -Value ('"{0}",0' -f $bambuStudio) }

    Write-Host ""
    Write-Host "De koppeling is geinstalleerd." -ForegroundColor Green
    Write-Host "Je kunt dit venster sluiten en daarna op Open in Bambu Studio klikken."
    exit 0
}

try {
    if (-not $ProtocolUrl) { throw "Er is geen link ontvangen." }
    $launcherUri = [Uri]$ProtocolUrl
    if ($launcherUri.Scheme -ne "printmanager" -or $launcherUri.Host -ne "open") { throw "De ontvangen link is ongeldig." }

    $fileParameter = ($launcherUri.Query.TrimStart("?") -split "&" | Where-Object { $_ -like "file=*" } | Select-Object -First 1)
    if (-not $fileParameter) { throw "De link bevat geen printbestand." }
    $fileUri = [Uri]([Uri]::UnescapeDataString($fileParameter.Substring(5)))

    $trustedOrigin = (Get-ItemProperty -Path $settingsKey -Name "TrustedOrigin").TrustedOrigin
    if ($fileUri.Scheme -notin @("http", "https")) { throw "Alleen HTTP- of HTTPS-bestanden zijn toegestaan." }
    $receivedOrigin = $fileUri.GetLeftPart([UriPartial]::Authority)
    if ($receivedOrigin -ne $trustedOrigin) {
        throw "Het bestand komt van $receivedOrigin, maar de ingestelde 3D Print Manager is $trustedOrigin. Installeer de Windows-koppeling opnieuw vanaf de productpagina."
    }
    if (-not $fileUri.AbsolutePath.StartsWith("/api/bambu-studio/files/")) { throw "Het bestandspad is niet toegestaan." }
    if (-not $fileUri.AbsolutePath.EndsWith(".gcode.3mf", [StringComparison]::OrdinalIgnoreCase)) { throw "Alleen printklare .gcode.3mf-bestanden zijn toegestaan." }

    $downloadDirectory = Join-Path $env:LOCALAPPDATA "3DPrintManager\BambuFiles"
    New-Item -ItemType Directory -Force -Path $downloadDirectory | Out-Null
    Get-ChildItem -LiteralPath $downloadDirectory -Filter "*.gcode.3mf" -File -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } |
        Remove-Item -Force -ErrorAction SilentlyContinue

    $target = Join-Path $downloadDirectory (([Guid]::NewGuid().ToString("N")) + ".gcode.3mf")
    Invoke-WebRequest -UseBasicParsing -Uri $fileUri.AbsoluteUri -OutFile $target -TimeoutSec 120
    if ((Get-Item $target).Length -lt 100) { throw "Het gedownloade bestand is leeg of onvolledig." }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::OpenRead($target)
    try {
        $entryNames = @($archive.Entries | ForEach-Object { $_.FullName })
        if ($entryNames -notcontains "[Content_Types].xml") { throw "Het bestand is geen geldig 3MF-bestand." }
        if (-not ($entryNames | Where-Object { $_ -match '(?i)(^|/)Metadata/plate_[0-9]+\.gcode$' })) {
            throw "Het 3MF-bestand bevat geen printklare plaat. Exporteer het opnieuw vanuit Bambu Studio."
        }
    } finally {
        $archive.Dispose()
    }

    $bambuStudio = Find-BambuStudio
    if (-not $bambuStudio) { throw "Bambu Studio is niet gevonden. Installeer Bambu Studio en probeer opnieuw." }
    Start-Process -FilePath $bambuStudio -ArgumentList @('"{0}"' -f $target)
} catch {
    Show-LauncherError $_.Exception.Message
    exit 1
}
