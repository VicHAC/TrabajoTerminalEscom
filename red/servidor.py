from utils_rutas import get_app_data_dir
"""
red/servidor.py
===============
Servidor de red centralizado para la aplicación. Maneja las consultas de base de datos,
el almacenamiento de archivos (imágenes originales, crops, filtrados y esqueletos)
y ejecuta el procesamiento pesado (YOLO, filtrado, esqueletizado y métricas).
"""

import os
import json
import logging
import sqlite3
import shutil
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# Asegurar configuración de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class ServidorMicrogliasHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        # Evitar inundar la terminal con peticiones GET de imágenes
        if "GET /api/files/download" in args[0]:
            return
        logging.info("%s - - %s" % (self.address_string(), format % args))

    def send_json(self, data, status_code=200):
        try:
            response_bytes = json.dumps(data).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)
        except Exception as e:
            logging.error(f"Error al enviar JSON: {e}")

    def send_error_json(self, message, status_code=500):
        self.send_json({"error": message}, status_code)

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        # Obtener longitud del cuerpo
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b""
        except Exception as e:
            self.send_error_json(f"Error leyendo cuerpo de petición: {str(e)}", 400)
            return

        # ----------------------------------------------------
        # 1. CONSULTAS DE BASE DE DATOS PROXY
        # ----------------------------------------------------
        if path == "/api/db/execute":
            try:
                data = json.loads(body.decode("utf-8"))
                sql = data.get("sql")
                params = data.get("params", []) or []

                from bd.database import conectar
                conn = conectar()
                cur = conn.cursor()
                try:
                    cur.execute(sql, tuple(params) if params else ())
                    results = cur.fetchall()
                    lastrowid = cur.lastrowid
                    rowcount = cur.rowcount
                    conn.commit()
                    self.send_json({
                        "results": results,
                        "lastrowid": lastrowid,
                        "rowcount": rowcount
                    })
                except Exception as db_err:
                    conn.rollback()
                    logging.error(f"Error SQL: {sql} | {db_err}")
                    self.send_error_json(f"Error de base de datos: {str(db_err)}", 500)
                finally:
                    conn.close()
            except Exception as e:
                self.send_error_json(f"Error de formato JSON: {str(e)}", 400)

        # ----------------------------------------------------
        # 2. SUBIR ARCHIVOS (CLIENTE -> SERVIDOR)
        # ----------------------------------------------------
        elif path == "/api/files/upload":
            query_params = parse_qs(parsed_url.query)
            relative_path = query_params.get("path", [None])[0]

            if not relative_path:
                self.send_error_json("Falta el parámetro 'path'", 400)
                return

            # Sanitizar ruta y asegurar directorios
            relative_path = relative_path.replace("\\", "/")
            dest_path = os.path.join(get_app_data_dir(), relative_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            try:
                with open(dest_path, "wb") as f:
                    f.write(body)
                self.send_json({"success": True, "saved_path": relative_path})
                logging.info(f"Archivo subido y guardado en: {relative_path}")
            except Exception as e:
                self.send_error_json(f"Error al escribir archivo en servidor: {str(e)}")

        # ----------------------------------------------------
        # 3. PROCESAMIENTO: CONTEO IA (YOLO)
        # ----------------------------------------------------
        elif path == "/api/process/deteccion":
            try:
                data = json.loads(body.decode("utf-8"))
                ruta_imagen = data.get("ruta_imagen")
                base_output_folder = data.get("base_output_folder")
                confidence_threshold = data.get("confidence_threshold", 0.20)

                # Asegurar rutas locales del servidor
                ruta_imagen_local = os.path.join(get_app_data_dir(), ruta_imagen.replace("\\", "/"))
                base_output_local = os.path.join(get_app_data_dir(), base_output_folder.replace("\\", "/"))

                from procesamiento.deteccion import ejecutar_conteo_ia
                crops_folder, count, boxes_data = ejecutar_conteo_ia(
                    ruta_imagen_local, base_output_local, confidence_threshold
                )

                # Convertir rutas absolutas del servidor a relativas para el cliente
                rel_crops_folder = os.path.relpath(crops_folder, get_app_data_dir()).replace("\\", "/")
                for box in boxes_data:
                    if "crop_path" in box:
                        box["crop_path"] = os.path.relpath(box["crop_path"], get_app_data_dir()).replace("\\", "/")

                self.send_json({
                    "crops_folder": rel_crops_folder,
                    "count": count,
                    "boxes": boxes_data
                })
            except Exception as e:
                self.send_error_json(f"Error en detección IA en servidor: {str(e)}")

        # ----------------------------------------------------
        # 4. PROCESAMIENTO: ESQUELETIZADO
        # ----------------------------------------------------
        elif path == "/api/process/esqueletizado":
            try:
                data = json.loads(body.decode("utf-8"))
                fil_path = data.get("fil_path")
                esqueletos_dir = data.get("esqueletos_dir")
                out_name = data.get("out_name")

                fil_path_local = os.path.join(get_app_data_dir(), fil_path.replace("\\", "/"))
                esqueletos_dir_local = os.path.join(get_app_data_dir(), esqueletos_dir.replace("\\", "/"))
                os.makedirs(esqueletos_dir_local, exist_ok=True)
                out_path_local = os.path.join(esqueletos_dir_local, out_name)

                from procesamiento.esqueletizado import generar_esqueleto_de_archivo
                import cv2
                skeleton_img = generar_esqueleto_de_archivo(fil_path_local)
                if skeleton_img is not None:
                    cv2.imwrite(out_path_local, skeleton_img)
                    rel_out_path = os.path.relpath(out_path_local, get_app_data_dir()).replace("\\", "/")
                    self.send_json({"success": True, "esqueleto_path": rel_out_path})
                else:
                    self.send_error_json("No se pudo generar el esqueleto")
            except Exception as e:
                self.send_error_json(f"Error en esqueletizado en servidor: {str(e)}")

        # ----------------------------------------------------
        # 5. PROCESAMIENTO: MÉTRICAS
        # ----------------------------------------------------
        elif path == "/api/process/metricas":
            try:
                data = json.loads(body.decode("utf-8"))
                skeleton_image_path = data.get("skeleton_image_path")
                skeleton_local = os.path.join(get_app_data_dir(), skeleton_image_path.replace("\\", "/"))

                from procesamiento.metricas import extraer_metricas_esqueleto
                metrics = extraer_metricas_esqueleto(skeleton_local)
                self.send_json({"success": True, "metricas": metrics})
            except Exception as e:
                self.send_error_json(f"Error al extraer métricas en servidor: {str(e)}")

        else:
            self.send_error_json("Ruta no encontrada", 404)

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        # ----------------------------------------------------
        # DESCARGAR ARCHIVOS (SERVIDOR -> CLIENTE)
        # ----------------------------------------------------
        if path == "/api/files/download":
            query_params = parse_qs(parsed_url.query)
            relative_path = query_params.get("path", [None])[0]

            if not relative_path:
                self.send_error_json("Falta el parámetro 'path'", 400)
                return

            relative_path = relative_path.replace("\\", "/")
            full_path = os.path.join(get_app_data_dir(), relative_path)

            if not os.path.exists(full_path):
                self.send_error_json(f"Archivo no encontrado: {relative_path}", 404)
                return

            try:
                with open(full_path, "rb") as f:
                    file_data = f.read()

                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(file_data)))
                self.end_headers()
                self.wfile.write(file_data)
            except Exception as e:
                self.send_error_json(f"Error al leer archivo del servidor: {str(e)}")
        
        # ----------------------------------------------------
        # COMPROBAR ESTADO DEL ARCHIVO (EXISTENCIA)
        # ----------------------------------------------------
        elif path == "/api/files/exists":
            query_params = parse_qs(parsed_url.query)
            relative_path = query_params.get("path", [None])[0]

            if not relative_path:
                self.send_error_json("Falta el parámetro 'path'", 400)
                return

            relative_path = relative_path.replace("\\", "/")
            full_path = os.path.join(get_app_data_dir(), relative_path)
            
            self.send_json({"exists": os.path.exists(full_path)})

        else:
            self.send_error_json("Ruta no encontrada", 404)

def run_server(port=5000):
    import socket
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, ServidorMicrogliasHandler)
    
    # Detectar IP LAN
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_lan = s.getsockname()[0]
        s.close()
    except Exception:
        ip_lan = "127.0.0.1"
    
    logging.info(f"=== Servidor de Microglías Iniciado ===")
    logging.info(f"    Escuchando en: 0.0.0.0:{port}")
    logging.info(f"    IP LAN para clientes: {ip_lan}:{port}")
    logging.info("Listo para recibir conexiones de computadoras en la misma red Wi-Fi.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Servidor detenido manualmente.")
    finally:
        httpd.server_close()

if __name__ == "__main__":
    run_server()
