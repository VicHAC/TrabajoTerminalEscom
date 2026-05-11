import sys
import os

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
        myappid = 'escom.tt.microglias.1'
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
    /* Forzar a que todo el texto base sea negro */
    QWidget {
        color: #000000;
    }
    QLabel {
        font-family: 'Segoe UI', Arial, sans-serif;
        color: #333333;
    }
    QLineEdit {
        border: 1px solid #CCCCCC;
        border-radius: 8px;
        padding: 10px;
        background-color: #FDFDFD;
        color: #000000; /* Letras negras en los inputs */
        font-size: 14px;
    }
    QLineEdit:focus {
        border: 2px solid #003366;
    }
    QPushButton {
        border-radius: 8px;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 14px;
        font-weight: bold;
        color: #333333; /* Texto de los botones visible */
    }
    QTableWidget {
        background-color: #FFFFFF;
        color: #000000; /* Letras negras en las tablas */
        border: 1px solid #E0E0E0;
        gridline-color: #CCCCCC;
    }
    QTableWidget::item {
        color: #000000;
    }
    QHeaderView::section {
        background-color: #FFFFFF;
        color: #000000; /* Letras negras en los títulos de las columnas */
        padding: 8px;
        border: none;
        border-bottom: 2px solid #003366;
        font-weight: bold;
        font-size: 14px;
    }
    QFrame#menu_lateral {
        background-color: #FFFFFF;
        border-right: 1px solid #E0E0E0;
    }
    """
    app.setStyleSheet(estilo_global)

    ventana = VentanaLogin()
    ventana.setObjectName("ventana_login")
    ventana.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
