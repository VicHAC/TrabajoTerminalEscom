from utils_rutas import get_app_data_dir
"""
red/cliente.py
==============
Módulo cliente de red. Traduce las llamadas locales a consultas HTTP y
descargas de archivos para comunicarse con el servidor central de la red Wi-Fi.
"""

import os
import json
import logging
import urllib.request
import urllib.parse
from red.config import obtener_url_servidor, es_cliente

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ---------------------------------------------------------------------------
# 1. TRANSPARENT DATABASE PROXY (SQLite Mock Connection and Cursor)
# ---------------------------------------------------------------------------

import socket
import urllib.error

def conmutar_a_modo_local(error_context=""):
    """
    Cambia automáticamente el modo de operación de la aplicación a LOCAL
    escribiendo en el archivo config.json para evitar bloqueos adicionales.
    """
    try:
        from red.config import cargar_configuracion, guardar_configuracion
        config = cargar_configuracion()
        if config.get("modo") == "cliente":
            config["modo"] = "local"
            guardar_configuracion(config)
            logging.warning(f"[cliente] Servidor no disponible ({error_context}). Se ha cambiado automáticamente el modo a LOCAL.")
    except Exception as e:
        logging.error(f"[cliente] Error al cambiar modo a local: {e}")

def realizar_peticion_servidor(url_or_req, data=None, timeout=5):
    """
    Realiza una petición HTTP al servidor con un timeout determinado.
    Si se detecta una desconexión o timeout, cambia la app a modo local y lanza ConnectionError.
    """
    try:
        if data is not None:
            if isinstance(data, (dict, list)):
                body = json.dumps(data).encode("utf-8")
                req = urllib.request.Request(
                    url_or_req,
                    data=body,
                    headers={"Content-Type": "application/json"}
                )
            else:
                req = urllib.request.Request(url_or_req, data=data)
        else:
            req = url_or_req
            
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as http_err:
        raise http_err
    except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError) as conn_err:
        conmutar_a_modo_local(str(conn_err))
        raise ConnectionError(
            f"No se pudo establecer conexión con el servidor: {conn_err}. "
            "El modo de operación se ha cambiado automáticamente a LOCAL. Por favor, reintente la operación."
        ) from conn_err

class ClienteDBCursor:
    def __init__(self, connection):
        self.connection = connection
        self.lastrowid = None
        self.rowcount = -1
        self._results = []
        self._idx = 0

    def execute(self, sql, params=None):
        payload = {
            "sql": sql,
            "params": list(params) if params else []
        }
        url = f"{obtener_url_servidor()}/api/db/execute"
        try:
            try:
                response_bytes = realizar_peticion_servidor(url, data=payload, timeout=5)
                res_data = json.loads(response_bytes.decode("utf-8"))
            except urllib.error.HTTPError as http_err:
                err_body = http_err.read().decode("utf-8")
                try:
                    err_json = json.loads(err_body)
                    err_msg = err_json.get("error", "")
                except Exception:
                    err_msg = err_body
                
                import sqlite3
                if "UNIQUE" in err_msg or "integrity" in err_msg.lower() or "unique constraint" in err_msg.lower():
                    raise sqlite3.IntegrityError(err_msg)
                else:
                    raise sqlite3.DatabaseError(err_msg)
                
            self._results = res_data.get("results", [])
            self.lastrowid = res_data.get("lastrowid")
            self.rowcount = res_data.get("rowcount", -1)
            self._idx = 0
        except ConnectionError as conn_err:
            logging.error(f"[cliente_db] Conexión perdida con el servidor: {conn_err}")
            import sqlite3
            raise sqlite3.OperationalError(str(conn_err)) from conn_err
        except Exception as e:
            logging.error(f"[cliente_db] Error al ejecutar consulta SQL en el servidor: {e}")
            raise
        return self

    def fetchone(self):
        if self._idx < len(self._results):
            row = self._results[self._idx]
            self._idx += 1
            return tuple(row) if row is not None else None
        return None

    def fetchall(self):
        rows = self._results[self._idx:]
        self._idx = len(self._results)
        return [tuple(r) for r in rows]

class ClienteDBConnection:
    def cursor(self):
        return ClienteDBCursor(self)

    def commit(self):
        # El servidor auto-commitea cada transacción en SQLite remota
        pass

    def rollback(self):
        pass

    def close(self):
        pass

def conectar_cliente():
    """Retorna un objeto de conexión simulado que envía consultas SQL al servidor."""
    return ClienteDBConnection()


# ---------------------------------------------------------------------------
# 2. FILE SYNC AND CACHE UTILITIES
# ---------------------------------------------------------------------------

def obtener_ruta_relativa_proyecto(ruta_completa):
    """Convierte una ruta absoluta al formato relativo del workspace del proyecto."""
    ruta_completa = ruta_completa.replace("\\", "/")
    cwd = get_app_data_dir().replace("\\", "/")
    
    if ruta_completa.startswith(cwd):
        rel = os.path.relpath(ruta_completa, cwd)
    else:
        # Si es ruta parcial, limpiarla
        rel = ruta_completa
        
    return rel.replace("\\", "/")

def cliente_existe_archivo_en_servidor(ruta_relativa):
    """Pregunta al servidor si un archivo existe."""
    try:
        ruta_rel_limpia = obtener_ruta_relativa_proyecto(ruta_relativa)
        url = f"{obtener_url_servidor()}/api/files/exists?path={urllib.parse.quote(ruta_rel_limpia)}"
        response_bytes = realizar_peticion_servidor(url, timeout=5)
        res_data = json.loads(response_bytes.decode("utf-8"))
        return res_data.get("exists", False)
    except Exception as e:
        logging.error(f"[cliente_files] Error al comprobar existencia en servidor ({ruta_relativa}): {e}")
        return False

def cliente_descargar_archivo(ruta_relativa):
    """Descarga un archivo desde el servidor y lo guarda localmente en el cliente."""
    ruta_rel_limpia = obtener_ruta_relativa_proyecto(ruta_relativa)
    local_path = os.path.join(get_app_data_dir(), ruta_rel_limpia)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    url = f"{obtener_url_servidor()}/api/files/download?path={urllib.parse.quote(ruta_rel_limpia)}"
    try:
        logging.info(f"[cliente_files] Descargando {ruta_rel_limpia}...")
        file_bytes = realizar_peticion_servidor(url, timeout=10)
        with open(local_path, "wb") as f:
            f.write(file_bytes)
        return True
    except Exception as e:
        logging.error(f"[cliente_files] Error al descargar archivo del servidor ({ruta_rel_limpia}): {e}")
        return False

def cliente_subir_archivo(ruta_relativa):
    """Sube un archivo local del cliente hacia el servidor central."""
    ruta_rel_limpia = obtener_ruta_relativa_proyecto(ruta_relativa)
    local_path = os.path.join(get_app_data_dir(), ruta_rel_limpia)
    
    if not os.path.exists(local_path):
        logging.error(f"[cliente_files] No se pudo subir, archivo no existe localmente: {local_path}")
        return False
        
    url = f"{obtener_url_servidor()}/api/files/upload?path={urllib.parse.quote(ruta_rel_limpia)}"
    try:
        logging.info(f"[cliente_files] Subiendo {ruta_rel_limpia} al servidor...")
        with open(local_path, "rb") as f:
            file_data = f.read()
            
        response_bytes = realizar_peticion_servidor(url, data=file_data, timeout=10)
        res_data = json.loads(response_bytes.decode("utf-8"))
        return res_data.get("success", False)
    except Exception as e:
        logging.error(f"[cliente_files] Error al subir archivo al servidor ({ruta_rel_limpia}): {e}")
        return False

def asegurar_archivo_local(ruta):
    """
    Función CLAVE para compatibilidad en cliente:
    Si la ruta de un recurso (como un crop, filtrado o esqueleto) no existe localmente
    en esta computadora cliente, lo descarga automáticamente del servidor central.
    Devuelve la ruta absoluta local final.
    """
    if not ruta:
        return ruta
        
    ruta_rel = obtener_ruta_relativa_proyecto(ruta)
    ruta_local_abs = os.path.join(get_app_data_dir(), ruta_rel)
    
    if es_cliente():
        # Si no existe localmente, descargarlo del servidor
        if not os.path.exists(ruta_local_abs):
            exito = cliente_descargar_archivo(ruta_rel)
            if not exito:
                # Si falló, devolver la ruta tal cual
                return ruta_local_abs
    return ruta_local_abs


# ---------------------------------------------------------------------------
# 3. REMOTE PROCESSING PROXY FUNCTIONS
# ---------------------------------------------------------------------------

def cliente_ejecutar_conteo_ia(ruta_imagen, base_output_folder, confidence_threshold=0.20):
    """Envía la imagen al servidor para ejecutar la detección YOLO y descarga los crops resultantes."""
    ruta_imagen_rel = obtener_ruta_relativa_proyecto(ruta_imagen)
    base_output_rel = obtener_ruta_relativa_proyecto(base_output_folder)
    
    # Primero: Asegurar que el servidor tiene la imagen original
    # Si la ruta_imagen es del cliente local, la subimos
    if os.path.exists(ruta_imagen):
        cliente_subir_archivo(ruta_imagen_rel)
        
    payload = {
        "ruta_imagen": ruta_imagen_rel,
        "base_output_folder": base_output_rel,
        "confidence_threshold": confidence_threshold
    }
    
    url = f"{obtener_url_servidor()}/api/process/deteccion"
    try:
        # Usar timeout más largo (25s) para el procesamiento pesado de IA
        response_bytes = realizar_peticion_servidor(url, data=payload, timeout=25)
        res = json.loads(response_bytes.decode("utf-8"))
            
        crops_folder_rel = res.get("crops_folder")
        count = res.get("count")
        boxes = res.get("boxes", [])
        
        # Como los crops fueron generados en el servidor, los descargaremos bajo demanda o pre-descargamos
        # Para que el cliente los visualice de inmediato, descargamos los crops ahora mismo
        for box in boxes:
            c_path = box.get("crop_path")
            if c_path:
                cliente_descargar_archivo(c_path)
                
        crops_folder_local = os.path.join(get_app_data_dir(), crops_folder_rel)
        return crops_folder_local, count, boxes
    except Exception as e:
        logging.error(f"[cliente_process] Error al ejecutar conteo IA remoto: {e}")
        raise

def cliente_generar_esqueleto_de_archivo(fil_path, esqueletos_dir, out_name):
    """Pide al servidor esqueletizar una imagen filtrada y devuelve la ruta del esqueleto descargado."""
    fil_path_rel = obtener_ruta_relativa_proyecto(fil_path)
    esqueletos_dir_rel = obtener_ruta_relativa_proyecto(esqueletos_dir)
    
    # Subir imagen filtrada local (si es que se modificó o generó en el cliente)
    if os.path.exists(fil_path):
        cliente_subir_archivo(fil_path_rel)
        
    payload = {
        "fil_path": fil_path_rel,
        "esqueletos_dir": esqueletos_dir_rel,
        "out_name": out_name
    }
    
    url = f"{obtener_url_servidor()}/api/process/esqueletizado"
    try:
        response_bytes = realizar_peticion_servidor(url, data=payload, timeout=15)
        res = json.loads(response_bytes.decode("utf-8"))
            
        esqueleto_path_rel = res.get("esqueleto_path")
        
        # Descargar el esqueleto resultante
        cliente_descargar_archivo(esqueleto_path_rel)
        
        return os.path.join(get_app_data_dir(), esqueleto_path_rel)
    except Exception as e:
        logging.error(f"[cliente_process] Error al ejecutar esqueletizado remoto: {e}")
        raise

def cliente_extraer_metricas_esqueleto(skeleton_image_path):
    """Pide al servidor extraer métricas de un esqueleto."""
    skeleton_path_rel = obtener_ruta_relativa_proyecto(skeleton_image_path)
    
    # Subir el esqueleto local si existe y se modificó en el cliente
    if os.path.exists(skeleton_image_path):
        cliente_subir_archivo(skeleton_path_rel)
        
    payload = {
        "skeleton_image_path": skeleton_path_rel
    }
    
    url = f"{obtener_url_servidor()}/api/process/metricas"
    try:
        response_bytes = realizar_peticion_servidor(url, data=payload, timeout=15)
        res = json.loads(response_bytes.decode("utf-8"))
            
        return res.get("metricas")
    except Exception as e:
        logging.error(f"[cliente_process] Error al extraer métricas remotas: {e}")
        raise
