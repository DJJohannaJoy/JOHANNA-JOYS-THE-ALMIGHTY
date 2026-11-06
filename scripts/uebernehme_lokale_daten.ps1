$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$dest = Join-Path $here 'APP'
$desktop = [Environment]::GetFolderPath('DesktopDirectory')
$src = Join-Path $desktop 'SET SCANNER'
if (-not (Test-Path -LiteralPath $src)) {
    Write-Host "Kein bestehender Desktop-Ordner gefunden: $src" -ForegroundColor Yellow
    Write-Host 'Nichts veraendert. Falls dein Scanner woanders liegt, seine Daten spaeter manuell importieren.'
    exit 0
}
Write-Host "Kopiere nur deine eigenen Daten aus $src" -ForegroundColor Cyan
foreach ($section in @('Datenbank','Ergebnisse','Protokolle')) {
  foreach ($folder in @((Join-Path $src $section), (Join-Path $src (Join-Path 'APP' $section)))) {
    if (Test-Path -LiteralPath $folder) {
      $target = Join-Path $dest $section
      New-Item -ItemType Directory -Path $target -Force | Out-Null
      Get-ChildItem -LiteralPath $folder -File -Recurse | ForEach-Object {
        $relative = $_.FullName.Substring($folder.Length).TrimStart('\')
        $out = Join-Path $target $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $out) -Force | Out-Null
        if (-not (Test-Path -LiteralPath $out)) {Copy-Item -LiteralPath $_.FullName -Destination $out}
      }
      Write-Host "  Daten importiert: $section"
    }
  }
}
foreach ($config in @('config.json','settings.json','scanner_config.json')) {
  foreach ($from in @((Join-Path $src $config),(Join-Path $src (Join-Path 'APP' $config)))) {
    $to=Join-Path $dest $config
    if ((Test-Path -LiteralPath $from) -and -not (Test-Path -LiteralPath $to)) { Copy-Item -LiteralPath $from -Destination $to }
  }
}
Write-Host 'Import fertig. Originale sind unveraendert. Keine privaten Daten pushen!' -ForegroundColor Green
