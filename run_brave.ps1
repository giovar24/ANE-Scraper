# run_brave.ps1 - Relanza Brave con depuración remota (puerto 9222)
# Uso: cerrar Brave y ejecutar este script, o lanzarlo directamente (mata y relanza).
$ErrorActionPreference = "Stop"

$port = 9222
$brave = "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

# ¿Ya está escuchando el puerto?
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$port/json/version" -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -eq 200) {
        Write-Host "Brave ya está en el puerto $port. Nada que hacer."
        exit 0
    }
} catch { }

# Cerrar Brave por completo
Get-Process brave -ErrorAction SilentlyContinue | ForEach-Object {
    try { $_.CloseMainWindow() | Out-Null } catch { }
}
Start-Sleep -Seconds 2
Get-Process brave -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

# Relanzar conservando el perfil por defecto (sesión intacta)
Start-Process -FilePath $brave -ArgumentList "--remote-debugging-port=$port"
Write-Host "Brave lanzado con depuración remota en http://127.0.0.1:$port"
Write-Host "Verifica que sigues logueado en https://www.ane.cr/"
