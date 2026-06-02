import hashlib
import sqlite3
import os
import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon

class VentanaLogin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prototipo Microglías - Inicio de Sesión")
        
        # Resolver ruta para PyInstaller
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.logo_path = os.path.join(base_path, "assets", "logo.png")
        self.icon_path = os.path.join(base_path, "assets", "logoW.png")
        self.conexion_icon_path = os.path.join(base_path, "assets", "buttons", "conexion.png")
        
        self.setWindowIcon(QIcon(self.icon_path))
        self.resize(400, 550)
        
        # Botón de configuración de red en la esquina superior izquierda
        self.btn_config_red = QPushButton(self)
        self.btn_config_red.setIcon(QIcon(self.conexion_icon_path))
        self.btn_config_red.setIconSize(QSize(22, 22))
        self.btn_config_red.setFixedSize(36, 36)
        self.btn_config_red.setToolTip("Configuración de Red")
        self.btn_config_red.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_config_red.setStyleSheet("""
            QPushButton { background-color: transparent; border: 1px solid transparent; outline: none; }
            QPushButton:hover { background-color: #ddf4ff; border-radius: 18px; }
        """)
        self.btn_config_red.clicked.connect(self.abrir_config_red)
        
        # Layout superior para posicionar el botón de red arriba a la izquierda
        layout_top = QHBoxLayout()
        layout_top.setContentsMargins(5, 5, 5, 0)
        layout_top.addWidget(self.btn_config_red)
        layout_top.addStretch()
        
        # Contenedor central de tamaño fijo para mantener la responsividad
        contenedor_login = QWidget()
        contenedor_login.setFixedWidth(320)
        
        layout_login = QVBoxLayout(contenedor_login)
        layout_login.setContentsMargins(0, 0, 0, 0)
        layout_login.setSpacing(10)

        # 1. EL LOGO
        self.logo = QLabel("Aquí va tu logo (assets/logo.png)")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        pixmap = QPixmap(self.logo_path)
        if not pixmap.isNull():
            self.logo.setFixedSize(250, 250)
            self.logo.setScaledContents(True)
            self.logo.setPixmap(pixmap)
        else:
            self.logo.setStyleSheet("border: 1px dashed #ccc; color: #999; padding: 20px;")
            
        titulo = QLabel("Bienvenido")
        titulo.setStyleSheet("font-size: 24px; font-weight: bold; color: #24292f; margin-top: 15px;")
        subtitulo = QLabel("Ingresa tus credenciales para continuar")
        subtitulo.setStyleSheet("color: #57606a; font-size: 13px; margin-bottom: 25px;")
        
        self.input_usuario = QLineEdit()
        self.input_usuario.setPlaceholderText("Usuario")
        
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Contraseña")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_usuario.returnPressed.connect(self.verificar_login)
        self.input_password.returnPressed.connect(self.verificar_login)

        btn_ingresar = QPushButton("Iniciar Sesión")
        btn_ingresar.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 2px solid #24292f;
                color: #24292f;
                padding: 10px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #24292f;
                color: #FFFFFF;
            }
        """)
        btn_ingresar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ingresar.clicked.connect(self.verificar_login)

        btn_invitado = QPushButton("Continuar como invitado")
        btn_invitado.setStyleSheet("background-color: transparent; color: #0969da; border: none; font-weight: normal; font-size: 13px;")
        btn_invitado.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_invitado.clicked.connect(self.login_invitado)
        

        
        label_ayuda = QLabel("¿No tienes una cuenta? Comunícate con el administrador")
        label_ayuda.setStyleSheet("color: #888888; font-size: 11px; margin-top: 30px;")
        label_ayuda.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout_login.addWidget(self.logo, alignment=Qt.AlignmentFlag.AlignCenter)
        layout_login.addWidget(titulo, alignment=Qt.AlignmentFlag.AlignCenter)
        layout_login.addWidget(subtitulo, alignment=Qt.AlignmentFlag.AlignCenter)
        layout_login.addWidget(self.input_usuario)
        layout_login.addWidget(self.input_password)
        layout_login.addWidget(btn_ingresar)
        layout_login.addWidget(btn_invitado)
        layout_login.addWidget(label_ayuda)

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.addLayout(layout_top)
        layout_principal.addStretch()
        layout_principal.addWidget(contenedor_login, alignment=Qt.AlignmentFlag.AlignCenter)
        layout_principal.addStretch()
        self.setLayout(layout_principal)

        # Definir orden de tabulación explícito para navegación fluida
        self.setTabOrder(self.input_usuario, self.input_password)
        self.setTabOrder(self.input_password, btn_ingresar)
        self.setTabOrder(btn_ingresar, btn_invitado)
        self.setTabOrder(btn_invitado, self.btn_config_red)

    def abrir_config_red(self):
        from red.config_gui import DialogoConfigRed
        dialogo = DialogoConfigRed(self)
        dialogo.exec()

    def verificar_login(self):
        usuario = self.input_usuario.text()
        password = self.input_password.text()

        if not usuario or not password:
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Atención", "Llena los campos.", "warning", self).exec()
            return

        pass_hash = hashlib.sha256(password.encode()).hexdigest()

        from bd.database import conectar
        try:
            conexion = conectar()
            cursor = conexion.cursor()
            cursor.execute("SELECT id_usuario, rol FROM Usuario WHERE nombre_usuario = ? AND contrasenia_hash = ?", (usuario, pass_hash))
            resultado = cursor.fetchone()
            conexion.close()

            if resultado:
                id_user, rol = resultado
                
                # Registrar sesión de usuario
                try:
                    con_ses = conectar()
                    cur_ses = con_ses.cursor()
                    cur_ses.execute("INSERT INTO Sesion (id_usuario) VALUES (?)", (id_user,))
                    con_ses.commit()
                    con_ses.close()
                except Exception as e_ses:
                    print(f"Error al registrar sesión: {e_ses}")
                
                if rol == "Administrador":
                    from vistas.administrador import VentanaAdministrador
                    self.dashboard = VentanaAdministrador(id_usuario=id_user)
                elif rol == "Tesista":
                    from vistas.tesista import VentanaTesista
                    self.dashboard = VentanaTesista(id_usuario=id_user, rol=rol, nombre_usuario=usuario)
                else:
                    from vistas.investigador import VentanaInvestigador
                    self.dashboard = VentanaInvestigador(id_usuario=id_user, rol=rol, nombre_usuario=usuario)
                
                self.dashboard.show()
                self.close()
            else:
                from vistas.utilidades import DialogoNotificacion
                DialogoNotificacion("Error", "Usuario o contraseña incorrectos.", "error", self).exec()
        except Exception as e:
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Error", f"Falla en (BD): {e}", "error", self).exec()

    def login_invitado(self):
        from vistas.invitado import VentanaInvitado
        self.dashboard = VentanaInvitado(id_usuario=0, rol="Invitado", nombre_usuario="Invitado")
        self.dashboard.show()
        self.close()