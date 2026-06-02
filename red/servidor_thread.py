"""
red/servidor_thread.py
======================
Hilo de fondo (QThread) para arrancar y detener el servidor HTTP centralizado
desde la interfaz de usuario en la computadora que actúa como servidor.
"""

import socket
import logging
from PyQt6.QtCore import QThread
from http.server import HTTPServer
from red.servidor import ServidorMicrogliasHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class ServidorThread(QThread):
    def __init__(self, port=5000, parent=None):
        super().__init__(parent)
        self.port = port
        self.httpd = None

    def run(self):
        try:
            server_address = ('0.0.0.0', self.port)
            self.httpd = HTTPServer(server_address, ServidorMicrogliasHandler)
            
            # Detectar y mostrar la IP LAN real
            ip_lan = self._obtener_ip_lan()
            logging.info(f"=== Servidor de Microglías Iniciado ===")
            logging.info(f"    Escuchando en todas las interfaces (0.0.0.0):{self.port}")
            logging.info(f"    IP LAN para clientes: {ip_lan}:{self.port}")
            logging.info(f"    Los clientes deben configurar la IP: {ip_lan}")
            
            self.httpd.serve_forever()
        except Exception as e:
            logging.error(f"[servidor_thread] Excepción en ejecución del servidor: {e}")
        finally:
            if self.httpd:
                self.httpd.server_close()
                logging.info("[servidor_thread] Socket del servidor cerrado.")

    def stop(self):
        if self.httpd:
            logging.info("[servidor_thread] Solicitando detención del servidor HTTP...")
            self.httpd.shutdown()
            self.wait() # Esperar a que el hilo termine limpio
            logging.info("[servidor_thread] Servidor detenido exitosamente.")

    @staticmethod
    def _obtener_ip_lan():
        """Detecta la IP LAN real de esta máquina (no 127.0.0.1)."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

# Singleton para administrar la instancia del servidor activo en la aplicación
_servidor_activo = None

def iniciar_servidor_global(port=5000):
    global _servidor_activo
    if _servidor_activo and _servidor_activo.isRunning():
        logging.warning("[servidor_control] El servidor ya está corriendo.")
        return False
        
    _servidor_activo = ServidorThread(port=port)
    _servidor_activo.start()
    return True

def detener_servidor_global():
    global _servidor_activo
    if _servidor_activo and _servidor_activo.isRunning():
        _servidor_activo.stop()
        _servidor_activo = None
        return True
    return False

def esta_servidor_corriendo():
    global _servidor_activo
    return _servidor_activo is not None and _servidor_activo.isRunning()
