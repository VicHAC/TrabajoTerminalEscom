import hashlib
import sqlite3
import os
import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialog)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon

class VentanaLogin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AVA Image Analytics - Inicio de Sesión")
        
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
            QPushButton:hover { background-color: #eaf2ff; border-radius: 18px; }
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
        
        # Acción para mostrar/ocultar contraseña
        from PyQt6.QtGui import QAction
        self.action_ver_pass = QAction(self)
        self.action_ver_pass.setToolTip("Mostrar contraseña")
        self.input_password.addAction(self.action_ver_pass, QLineEdit.ActionPosition.TrailingPosition)
        
        self.pass_visible = False
        self.actualizar_icono_password()
        self.action_ver_pass.triggered.connect(self.alternar_visibilidad_password)

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
            QPushButton:pressed {
                background-color: #000000;
                color: #FFFFFF;
            }
        """)
        btn_ingresar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ingresar.clicked.connect(self.verificar_login)
        
        self.input_usuario.returnPressed.connect(lambda: self.simular_click_largo(btn_ingresar))
        self.input_password.returnPressed.connect(lambda: self.simular_click_largo(btn_ingresar))

        btn_invitado = QPushButton("Continuar como invitado")
        btn_invitado.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                color: #0969da; 
                border: none; 
                font-weight: normal; 
                font-size: 13px;
            }
            QPushButton:hover {
                font-weight: bold;
            }
        """)
        btn_invitado.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_invitado.clicked.connect(self.login_invitado)
        

        
        label_ayuda = QLabel('¿No tienes una cuenta? <a href="#copy" style="color: #888888; text-decoration: underline;">Comunícate con el administrador</a>')
        label_ayuda.setStyleSheet("color: #888888; font-size: 11px; margin-top: 30px;")
        label_ayuda.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_ayuda.setOpenExternalLinks(False)
        label_ayuda.linkActivated.connect(self.copiar_correos_administrador)

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

    def simular_click_largo(self, btn):
        btn.setDown(True)
        btn.repaint()
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(350, lambda: (btn.setDown(False), btn.click()))

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
                
                from vistas.utilidades import DialogoCarga
                from PyQt6.QtWidgets import QApplication
                
                dialogo_carga = DialogoCarga("Verificando sesión...", self)
                dialogo_carga.show()
                dialogo_carga.actualizar(10, "Sesión verificada...")
                QApplication.processEvents()

                if rol == "Administrador":
                    dialogo_carga.actualizar(40, "Cargando dependencias de Administración...")
                    QApplication.processEvents()
                    from vistas.administrador import VentanaAdministrador
                    dialogo_carga.actualizar(80, "Construyendo panel de Administrador...")
                    QApplication.processEvents()
                    self.dashboard = VentanaAdministrador(id_usuario=id_user)
                elif rol == "Tesista":
                    dialogo_carga.actualizar(40, "Cargando dependencias de IA y análisis...")
                    QApplication.processEvents()
                    from vistas.tesista import VentanaTesista
                    dialogo_carga.actualizar(80, "Construyendo entorno de Tesista...")
                    QApplication.processEvents()
                    self.dashboard = VentanaTesista(id_usuario=id_user, rol=rol, nombre_usuario=usuario)
                else:
                    dialogo_carga.actualizar(40, "Cargando dependencias de revisión...")
                    QApplication.processEvents()
                    from vistas.investigador import VentanaInvestigador
                    dialogo_carga.actualizar(80, "Construyendo entorno de Investigador...")
                    QApplication.processEvents()
                    self.dashboard = VentanaInvestigador(id_usuario=id_user, rol=rol, nombre_usuario=usuario)
                
                dialogo_carga.actualizar(100, "¡Listo!")
                QApplication.processEvents()
                
                dialogo_carga.close()
                self.dashboard.showMaximized()
                self.close()
            else:
                from vistas.utilidades import DialogoNotificacion
                DialogoNotificacion("Error", "Usuario o contraseña incorrectos.", "error", self).exec()
        except Exception as e:
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Error", f"Falla en (BD): {e}", "error", self).exec()

    def login_invitado(self):
        from vistas.utilidades import DialogoCarga
        from PyQt6.QtWidgets import QApplication
        
        dialogo_carga = DialogoCarga("Inicializando modo invitado...", self)
        dialogo_carga.show()
        dialogo_carga.actualizar(20, "Limpiando sesiones previas...")
        QApplication.processEvents()

        # Limpiar cualquier dato huérfano de una sesión de invitado anterior
        from bd.database import limpiar_datos_invitado
        limpiar_datos_invitado()

        dialogo_carga.actualizar(50, "Cargando módulos de análisis...")
        QApplication.processEvents()
        from vistas.invitado import VentanaInvitado
        
        dialogo_carga.actualizar(80, "Construyendo panel de invitado...")
        QApplication.processEvents()
        self.dashboard = VentanaInvitado(id_usuario=0, rol="Invitado", nombre_usuario="Invitado")
        
        dialogo_carga.actualizar(100, "¡Listo!")
        QApplication.processEvents()
        
        dialogo_carga.close()
        self.dashboard.showMaximized()
        self.close()

    def copiar_correos_administrador(self, link):
        if link == "#copy":
            from PyQt6.QtWidgets import QApplication
            
            correos_lista = [
                "snavarreteb1900@alumno.ipn.mx",
                "amartineza1706@alumno.ipn.mx",
                "valcarazc1500@alumno.ipn.mx"
            ]
            correos = "; ".join(correos_lista)
            
            portapapeles = QApplication.clipboard()
            portapapeles.setText(correos)
            
            DialogoCorreosAdministrador(self).exec()

    def actualizar_icono_password(self):
        # Crear icono dinámico en base al estado de visibilidad
        from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QBrush, QIcon
        from PyQt6.QtCore import Qt
        
        pix = QPixmap(20, 20)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Color del ojo
        color_ojo = QColor("#57606a")
        pen = QPen(color_ojo, 1.8)
        painter.setPen(pen)
        
        # Dibujar forma de ojo (arcos superior e inferior)
        painter.drawArc(2, 3, 16, 14, 35 * 16, 110 * 16)
        painter.drawArc(2, 3, 16, 14, 215 * 16, 110 * 16)
        
        # Dibujar iris
        painter.setBrush(QBrush(QColor("#24292f")))
        painter.setPen(QPen(QColor("#24292f"), 1))
        painter.drawEllipse(7, 7, 6, 6)
        
        # Dibujar pupila (brillo blanco)
        painter.setBrush(QBrush(QColor("white")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(9, 9, 2, 2)
        
        if not self.pass_visible:
            # Dibujar la línea diagonal para el ojo tachado (oculto)
            painter.setPen(QPen(QColor("#cf222e"), 1.8))
            painter.drawLine(3, 3, 17, 17)
            
        painter.end()
        self.action_ver_pass.setIcon(QIcon(pix))

    def alternar_visibilidad_password(self):
        self.pass_visible = not self.pass_visible
        if self.pass_visible:
            self.input_password.setEchoMode(QLineEdit.EchoMode.Normal)
            self.action_ver_pass.setToolTip("Ocultar contraseña")
        else:
            self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
            self.action_ver_pass.setToolTip("Mostrar contraseña")
        self.actualizar_icono_password()


class DialogoCorreosAdministrador(QDialog):
    def __init__(self, parent=None):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton
        from PyQt6.QtCore import Qt
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        
        from vistas.utilidades import set_app_icon
        set_app_icon(self)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        frame = QFrame(self)
        frame.setStyleSheet("""
            QFrame {
                background-color: #f6f8fa; 
                border-radius: 10px; 
                border: 1px solid #d0d7de; 
            }
            QLabel { 
                color: #24292f; 
                border: none; 
                background: transparent;
            }
            QPushButton { 
                background-color: transparent; 
                color: #24292f; 
                border: 2px solid #24292f; 
                border-radius: 6px; 
                padding: 6px 16px; 
                font-weight: bold; 
                font-size: 11px; 
            }
            QPushButton:hover { 
                background-color: #24292f; 
                color: white; 
            }
        """)
        
        flayout = QVBoxLayout(frame)
        flayout.setContentsMargins(15, 15, 15, 15)
        flayout.setSpacing(10)
        
        lbl_titulo = QLabel("<b>Correos de Administradores</b>")
        lbl_titulo.setStyleSheet("font-size: 13px; font-weight: bold; color: #24292f;")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setStyleSheet("background-color: #d0d7de; border: none; max-height: 1px;")
        
        lbl_info = QLabel("Copiado al portapapeles:")
        lbl_info.setStyleSheet("font-size: 11px; color: #57606a;")
        lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        correos_layout = QVBoxLayout()
        correos_layout.setSpacing(4)
        correos_lista = [
            "snavarreteb1900@alumno.ipn.mx",
            "amartineza1706@alumno.ipn.mx",
            "valcarazc1500@alumno.ipn.mx"
        ]
        for correo in correos_lista:
            lbl_correo = QLabel(f"• {correo}")
            lbl_correo.setStyleSheet("font-size: 11px; font-family: monospace; font-weight: bold; color: #24292f;")
            lbl_correo.setAlignment(Qt.AlignmentFlag.AlignLeft)
            correos_layout.addWidget(lbl_correo)
            
        btn_layout = QHBoxLayout()
        btn_aceptar = QPushButton("Aceptar")
        btn_aceptar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_aceptar.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_aceptar)
        btn_layout.addStretch()
        
        flayout.addWidget(lbl_titulo)
        flayout.addWidget(linea)
        flayout.addWidget(lbl_info)
        flayout.addLayout(correos_layout)
        flayout.addSpacing(5)
        flayout.addLayout(btn_layout)
        
        layout.addWidget(frame)
        self.setLayout(layout)
        self.setFixedSize(360, 230)
        
    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            p_geom = self.parent().geometry()
            self.move(p_geom.x() + (p_geom.width() - self.width()) // 2, p_geom.y() + (p_geom.height() - self.height()) // 2)

    def mousePressEvent(self, event):
        from PyQt6.QtCore import Qt
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        from PyQt6.QtCore import Qt
        if hasattr(self, "_drag_pos") and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)