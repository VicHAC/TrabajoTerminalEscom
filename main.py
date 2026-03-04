import sys
import os
from PyQt6.QtWidgets import QApplication
from bd.database import inicializar_bd
from vistas.login import VentanaLogin

def main():
    # 1. Asegurar que la BD exista antes de levantar la interfaz
    inicializar_bd()

    # 2. Levantar la app de PyQt
    app = QApplication(sys.argv)
    
    # 3. Mostrar la ventana de login
    ventana = VentanaLogin()
    ventana.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()