from utils_rutas import get_app_data_dir
"""
red/config.py
=============
Configuración de red para el programa. Permite definir si la aplicación
funciona de forma local o remota (Cliente/Servidor) en la red Wi-Fi.
"""

import os
import json
import sys

try:
    base_path = sys._MEIPASS
except Exception:
    base_path = get_app_data_dir()

CONFIG_PATH = os.path.join(base_path, "config.json")

# Valores por defecto
DEFAULT_CONFIG = {
    "modo": "local",       # Opciones: "local", "cliente", "servidor"
    "ip_servidor": "localhost",
    "puerto_servidor": 5000
}

def cargar_configuracion():
    """Carga la configuración desde config.json. Si no existe, crea el archivo por defecto."""
    if not os.path.exists(CONFIG_PATH):
        guardar_configuracion(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            # Asegurar que todas las claves existan
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
    except Exception:
        return DEFAULT_CONFIG

def refrescar_configuracion():
    """Vuelve a cargar la configuración en memoria desde el archivo config.json."""
    global config_global
    config_global = cargar_configuracion()

def guardar_configuracion(config):
    """Guarda la configuración en config.json."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        refrescar_configuracion()
    except Exception as e:
        print(f"Error al guardar config.json: {e}")

# Cargar configuración global al importar el módulo
config_global = cargar_configuracion()

def obtener_modo_operacion():
    return config_global.get("modo", "local")

def es_cliente():
    return obtener_modo_operacion() == "cliente"

def es_servidor():
    return obtener_modo_operacion() == "servidor"

def obtener_ip_servidor():
    return config_global.get("ip_servidor") or config_global.get("servidor_ip") or "localhost"

def obtener_puerto_servidor():
    # Convertir a entero por seguridad
    p = config_global.get("puerto_servidor") or config_global.get("servidor_port") or 5000
    try:
        return int(p)
    except ValueError:
        return 5000

def obtener_url_servidor():
    return f"http://{obtener_ip_servidor()}:{obtener_puerto_servidor()}"
