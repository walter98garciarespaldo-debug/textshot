<#
.SYNOPSIS
    Instala TextShot en el autoarranque de Windows y crea acceso directo en escritorio.
    Correr UNA sola vez. No necesita admin.
#>

$projectDir  = $PSScriptRoot
$vbsLauncher = "$projectDir\TextShot.vbs"
$startupKey  = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"

# ── 1. Autoarranque en registro ──────────────────────────────
$existing = Get-ItemProperty $startupKey -Name "TextShot" -EA SilentlyContinue
if ($existing) {
    Write-Host "Ya estaba en autoarranque." -ForegroundColor Cyan
} else {
    Set-ItemProperty $startupKey -Name "TextShot" -Value "wscript.exe `"$vbsLauncher`""
    Write-Host "Autoarranque configurado OK." -ForegroundColor Green
}

# ── 2. Acceso directo en escritorio ─────────────────────────
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcut = "$desktop\TextShot.lnk"

$ws  = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut($shortcut)
$lnk.TargetPath       = "wscript.exe"
$lnk.Arguments        = "`"$vbsLauncher`""
$lnk.WorkingDirectory = $projectDir
$lnk.Description      = "TextShot - OCR Screenshot (Ctrl+Alt+S)"
$lnk.IconLocation     = "$projectDir\assets\icon.png,0"
$lnk.Save()

Write-Host "Acceso directo creado en escritorio: $shortcut" -ForegroundColor Green

# ── 3. Lanzar ahora ─────────────────────────────────────────
Write-Host ""
Write-Host "Lanzando TextShot ahora..." -ForegroundColor Cyan
Start-Process "wscript.exe" -ArgumentList "`"$vbsLauncher`""
Start-Sleep -Seconds 2

$proc = Get-Process pythonw -EA SilentlyContinue
if ($proc) {
    Write-Host "TextShot corriendo (PID $($proc.Id))" -ForegroundColor Green
} else {
    Write-Host "Verificá el ícono en la bandeja del sistema (esquina inferior derecha)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Listo. TextShot arrancará automáticamente con Windows." -ForegroundColor Green
Write-Host "Para abrirlo: doble clic en TextShot.lnk del escritorio." -ForegroundColor Cyan
