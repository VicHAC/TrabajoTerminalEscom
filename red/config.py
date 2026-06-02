"""
red/config.py
=============
Configuración de red para el programa. Permite definir si la aplicación
funciona de forma local o remota (Cliente/Servidor) en la red Wi-Fi.
"""

import os
import json

CONFIG_PATH = os.path.join(os.getcwd(), "config.json")

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

def guardar_configuracion(config):
    """Guarda la configuración en config.json."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error al guardar config.json: {e}")

# Cargar configuración global al importar el módulo
config_global = cargar_configuracion()

def es_cliente():
    return config_global.get("modo") == "cliente"

def es_servidor():
    return config_global.get("modo") == "servidor"

def obtener_ip_servidor():
    return config_global.get("ip_servidor", "localhost")

def obtener_puerto_servidor():
    return config_global.get("puerto_servidor", 5000)

def obtener_url_servidor():
    return f"http://{obtener_ip_servidor()}:{obtener_puerto_servidor()}"
