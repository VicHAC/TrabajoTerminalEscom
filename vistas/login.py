import hashlib
import sqlite3
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt
from vistas.investigador import VentanaInvestigador

class VentanaLogin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prototipo Microglías - Inicio de Sesión")
        self.resize(350, 450)
        
        # Layout vertical
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Elementos de la UI
        titulo = QLabel("Iniciar Sesión")
        titulo.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        
        self.input_usuario = QLineEdit()
        self.input_usuario.setPlaceholderText("Usuario")
        self.input_usuario.setStyleSheet("padding: 8px; font-size: 14px;")
        
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Contraseña")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password.setStyleSheet("padding: 8px; font-size: 14px;")

        btn_ingresar = QPushButton("Ingresar")
        btn_ingresar.setStyleSheet("background-color: #003366; color: white; padding: 10px; font-weight: bold;")
        btn_ingresar.clicked.connect(self.verificar_login)

        btn_invitado = QPushButton("Ingresar como invitado")
        btn_invitado.setFlat(True)
        btn_invitado.setStyleSheet("color: #555;")
        btn_invitado.clicked.connect(self.login_invitado)

        # Agregando al layout
        layout.addWidget(titulo, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.input_usuario)
        layout.addWidget(self.input_password)
        layout.addSpacing(15)
        layout.addWidget(btn_ingresar)
        layout.addWidget(btn_invitado)

        self.setLayout(layout)

    def verificar_login(self):
        usuario = self.input_usuario.text()
        password = self.input_password.text()

        if not usuario or not password:
            QMessageBox.warning(self, "Awanta", "Llena los campos, no se llenan solos.")
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
                # Abrimos el dashboard
                self.dashboard = VentanaInvestigador(id_usuario=id_user, rol=rol)
                self.dashboard.show()
                # Cerramos el login
                self.close()
            else:
                QMessageBox.critical(self, "Error", "Usuario o contraseña incorrectos.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Falla en la Matrix (BD): {e}")

    def login_invitado(self):
        QMessageBox.information(self, "Modo Invitado", "Entraste de a grapa. No se guardará nada.")
        self.dashboard = VentanaInvestigador(id_usuario=0, rol="Invitado")
        self.dashboard.show()
        self.close()