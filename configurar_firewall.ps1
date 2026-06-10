<#
.SYNOPSIS
    Configura el Firewall de Windows para permitir la conexión colaborativa del Servidor de Microglías.
.DESCRIPTION
    Este script agrega una regla de entrada en el Firewall de Windows para el puerto del servidor (por defecto 5000).
    Permite conexiones en perfiles de red Dominio, Privado y Público, asegurando que otras computadoras se
    puedan conectar estando en la misma red Wi-Fi o Ethernet.
.PARAMETER Puerto
    El puerto del servidor a habilitar (por defecto 5000).
#>

param (
    [int]$Puerto = 5000
)

# 1. Verificar si el script se está ejecutando como Administrador
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Este script requiere privilegios de Administrador." -ForegroundColor Yellow
    Write-Host "Solicitando elevación de privilegios (UAC)..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Puerto $Puerto" -Verb RunAs
    exit
}

# 2. Configurar la regla de Firewall
$RuleName = "Trabajo Terminal - Servidor Microglias ($Puerto)"

Write-Host "===========================================================" -ForegroundColor Green
Write-Host "Configurando Firewall de Windows para el Servidor de Microglías" -ForegroundColor Green
Write-Host "Puerto a habilitar: $Puerto" -ForegroundColor Cyan
Write-Host "Perfiles de red: Dominio, Privado y Público" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Green

try {
    # Eliminar regla existente si ya existe
    Remove-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
    
    # Crear nueva regla de entrada
    New-NetFirewallRule -DisplayName $RuleName `
                        -Direction Inbound `
                        -Action Allow `
                        -Protocol TCP `
                        -LocalPort $Puerto `
                        -Profile Domain,Private,Public `
                        -Enabled True | Out-Null
                        
    Write-Host "¡Regla de Firewall creada con éxito!" -ForegroundColor Green
    Write-Host "Nombre de la regla: $RuleName" -ForegroundColor White
    Write-Host "Otras computadoras en la misma red ya pueden conectarse al servidor." -ForegroundColor Gray
} catch {
    Write-Error "Ocurrió un error al configurar la regla del firewall: $_"
}

Write-Host "`nPresiona cualquier tecla para salir..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
