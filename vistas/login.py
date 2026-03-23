import hashlib
import sqlite3
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

class VentanaLogin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prototipo Microglías - Inicio de Sesión")
        self.resize(400, 550)
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(40, 20, 40, 20)

        # 1. EL LOGO
        self.logo = QLabel("Aquí va tu logo (assets/logo.png)")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap("assets/logo.png")
        if not pixmap.isNull():
            self.logo.setPixmap(pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.logo.setStyleSheet("border: 1px dashed #ccc; color: #999; padding: 20px;")
            
        titulo = QLabel("Iniciar Sesión")
        titulo.setStyleSheet("font-size: 22px; font-weight: bold; color: #000000; margin-top: 10px;")
        subtitulo = QLabel("Ingresa nombre de usuario y contraseña")
        subtitulo.setStyleSheet("color: #666666; margin-bottom: 20px;")
        
        self.input_usuario = QLineEdit()
        self.input_usuario.setPlaceholderText("Usuario")
        
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Contraseña")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)

        btn_ingresar = QPushButton("Ingresar")
        btn_ingresar.setStyleSheet("background-color: #000000; color: #FFFFFF; padding: 12px; margin-top: 10px;")
        btn_ingresar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ingresar.clicked.connect(self.verificar_login)

        btn_invitado = QPushButton("Ingresar como invitado")
        btn_invitado.setStyleSheet("background-color: transparent; color: #555555; text-decoration: underline;")
        btn_invitado.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_invitado.clicked.connect(self.login_invitado)
        
        label_ayuda = QLabel("¿No tienes una cuenta? Comunícate con el administrador")
        label_ayuda.setStyleSheet("color: #888888; font-size: 11px; margin-top: 30px;")
        label_ayuda.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.logo)
        layout.addWidget(titulo, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitulo, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.input_usuario)
        layout.addWidget(self.input_password)
        layout.addWidget(btn_ingresar)
        layout.addWidget(btn_invitado)
        layout.addWidget(label_ayuda)

        self.setLayout(layout)

    def verificar_login(self):
        usuario = self.input_usuario.text()
        password = self.input_password.text()

        if not usuario or not password:
            QMessageBox.warning(self, "Aguanta", "Llena los campos, no se llenan solos.")
            return

        pass_hash = hashlib.sha256(password.encode()).hexdigest()

        try:
            conexion = sqlite3.connect("bd/database.db")
            cursor = conexion.cursor()
            cursor.execute("SELECT id_usuario, rol FROM Usuario WHERE nombre_usuario = ? AND contrasenia_hash = ?", (usuario, pass_hash))
            resultado = cursor.fetchone()
            conexion.close()

            if resultado:
                id_user, rol = resultado
                
                if rol == "Administrador":
                    from vistas.administrador import VentanaAdministrador
                    self.dashboard = VentanaAdministrador(id_usuario=id_user)
                else:
                    from vistas.investigador import VentanaInvestigador
                    self.dashboard = VentanaInvestigador(id_usuario=id_user, rol=rol)
                
                self.dashboard.show()
                self.close()
            else:
                QMessageBox.critical(self, "Error", "Usuario o contraseña incorrectos.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Falla en (BD): {e}")

    def login_invitado(self):
        QMessageBox.information(self, "Modo Invitado", "No se guardará nada.")
        from vistas.investigador import VentanaInvestigador
        self.dashboard = VentanaInvestigador(id_usuario=0, rol="Invitado")
        self.dashboard.show()
        self.close()