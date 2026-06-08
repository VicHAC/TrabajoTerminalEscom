import sys
import os

# Solución para el bug de cursor gigante en Linux (Ubuntu) con escalado de pantalla
if sys.platform.startswith("linux"):
    # Evitamos forzar 'xcb' para evitar errores de librerías faltantes como libxcb-cursor0
    # En su lugar, forzamos a Wayland a usar DPI estándar de 96 y definimos el tamaño de cursor de X11
    os.environ["QT_WAYLAND_FORCE_DPI"] = "96"
    os.environ["XCURSOR_SIZE"] = "24"

from bd.database import inicializar_bd
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from vistas.login import VentanaLogin

def resource_path(relative_path):
    """Obtiene la ruta absoluta a un recurso, funciona tanto en desarrollo como en PyInstaller"""
    try:
        # PyInstaller extrae los archivos en una carpeta temporal en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

def main():
    # Código necesario para que Windows muestre el icono en la barra de tareas
    # al ejecutarse como archivo compilado
    if os.name == 'nt':
        import ctypes
        myappid = 'escom.tt.ava.1'
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    inicializar_bd()

    app = QApplication(sys.argv)
    
    icon_path = resource_path(os.path.join("assets", "logo.png"))
    app.setWindowIcon(QIcon(icon_path))
    # ==========================================
    # Global QSS
    # ==========================================
    estilo_global = """
    QMainWindow, QDialog, QWidget#ventana_login {
        background-color: #FFFFFF;
    }
    QWidget {
        color: #24292f;
        font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
    }
    QLabel {
        color: #24292f;
    }
    QLineEdit {
        border: 1px solid #d0d7de;
        border-radius: 6px;
        padding: 8px 12px;
        background-color: #ffffff;
        color: #24292f;
        font-size: 13px;
    }
    QLineEdit:focus {
        border: 2px solid #0969da;
        background-color: #ffffff;
    }
    QPushButton {
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 600;
        background-color: #f6f8fa;
        border: 1px solid #d0d7de;
        color: #24292f;
    }
    QPushButton:hover {
        background-color: #f3f4f6;
        border-color: #1b1f2426;
    }
    QPushButton:pressed {
        background-color: #ebecf0;
    }
    QTableWidget {
        background-color: #FFFFFF;
        border: 1px solid #d0d7de;
        border-radius: 6px;
        gridline-color: #f0f0f0;
        font-size: 12px;
    }
    QHeaderView::section {
        background-color: #f6f8fa;
        color: #57606a;
        padding: 8px;
        border: none;
        border-bottom: 1px solid #d0d7de;
        font-weight: bold;
        font-size: 12px;
    }
    QFrame#menu_lateral {
        background-color: #ffffff;
        border-right: 1px solid #d0d7de;
    }
    """
    app.setStyleSheet(estilo_global)

    # Auto-iniciar servidor en segundo plano si la configuración está en modo servidor
    from red.config import obtener_modo_operacion, obtener_puerto_servidor
    if obtener_modo_operacion() == "servidor":
        try:
            from red.servidor_thread import iniciar_servidor_global
            puerto_cfg = obtener_puerto_servidor()
            iniciar_servidor_global(port=puerto_cfg)
        except Exception as e:
            print(f"Error al iniciar servidor en segundo plano: {e}")
            
    # Asegurar apagado del servidor al salir de la aplicación
    from red.servidor_thread import detener_servidor_global
    app.aboutToQuit.connect(detener_servidor_global)

    ventana = VentanaLogin()
    ventana.setObjectName("ventana_login")
    ventana.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
