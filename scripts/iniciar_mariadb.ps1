$ErrorActionPreference = 'Stop'
$serverRoot = Join-Path $env:LOCALAPPDATA 'CrisFerreterias\mariadb-11.4.3-winx64'
$serverExe = Join-Path $serverRoot 'bin\mariadbd.exe'
$configFile = Join-Path $serverRoot 'data\my.ini'

if (-not (Test-Path -LiteralPath $serverExe)) {
    throw "MariaDB no está instalado en $serverRoot"
}

$listener = Get-NetTCPConnection -LocalPort 3307 -State Listen -ErrorAction SilentlyContinue
if (-not $listener) {
    $logDir = Join-Path $serverRoot 'logs'
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    Start-Process -FilePath $serverExe `
        -ArgumentList "--defaults-file=$configFile" `
        -WorkingDirectory $serverRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDir 'mariadb.out.log') `
        -RedirectStandardError (Join-Path $logDir 'mariadb.err.log')
    $limite = (Get-Date).AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 500
        $listener = Get-NetTCPConnection -LocalPort 3307 -State Listen -ErrorAction SilentlyContinue
    } until ($listener -or (Get-Date) -gt $limite)
}

if (-not $listener) {
    throw 'MariaDB no abrió el puerto 3307.'
}

Write-Host 'MariaDB CrisFerreterias disponible en 127.0.0.1:3307.'
