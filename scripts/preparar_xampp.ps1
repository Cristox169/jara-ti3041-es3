$ErrorActionPreference = 'Stop'

$xamppRoot = if ($env:XAMPP_ROOT) { $env:XAMPP_ROOT } else { 'C:\xampp' }
$mysqlExe = Join-Path $xamppRoot 'mysql\bin\mysql.exe'
$startScript = Join-Path $xamppRoot 'mysql_start.bat'
$schemaFile = Join-Path $PSScriptRoot '..\crear_bd_xampp.sql'
$rootPassword = if ($env:XAMPP_ROOT_PASSWORD) { $env:XAMPP_ROOT_PASSWORD } else { '2222' }

if (-not (Test-Path -LiteralPath $mysqlExe)) {
    throw "No se encontró MariaDB de XAMPP en $mysqlExe"
}

$listener = Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue
if (-not $listener) {
    if (-not (Test-Path -LiteralPath $startScript)) {
        throw "No se encontró el iniciador de XAMPP en $startScript"
    }
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', "`"$startScript`"" -WindowStyle Hidden
    $deadline = (Get-Date).AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 500
        $listener = Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue
    } until ($listener -or (Get-Date) -gt $deadline)
}

if (-not $listener) {
    throw 'MariaDB de XAMPP no abrió el puerto 3306.'
}

$schemaSql = Get-Content -LiteralPath $schemaFile -Raw
& $mysqlExe --protocol=TCP -h 127.0.0.1 -P 3306 -u root "--password=$rootPassword" "--execute=$schemaSql"
if ($LASTEXITCODE -ne 0) {
    throw 'No fue posible crear la base y el usuario de CrisFerreterias en XAMPP.'
}

& $mysqlExe --protocol=TCP -h 127.0.0.1 -P 3306 -u crisferreterias_app '--password=crissteel_xampp_2026' -D CrisFerreterias --execute='SELECT VERSION(), DATABASE();'
if ($LASTEXITCODE -ne 0) {
    throw 'La verificación de CrisFerreterias en XAMPP falló.'
}

Write-Host 'MariaDB de XAMPP disponible en 127.0.0.1:3306 con la base CrisFerreterias.'
