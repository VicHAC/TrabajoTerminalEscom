"""
red/config_gui.py
=================
Interfaz gráfica para la configuración de red y administración del modo de operación
(Local, Cliente, Servidor). Permite configurar IPs, puertos y ver el estado del servidor.
"""

import os
import socket
import logging
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QLineEdit, QPushButton, QFrame, 
                             QGroupBox, QApplication)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

from red.config import (obtener_modo_operacion, obtener_url_servidor, 
                        guardar_configuracion, cargar_configuracion)
from red.servidor_thread import (iniciar_servidor_global, detener_servidor_global, 
                                 esta_servidor_corriendo)

def obtener_ips_locales():
    """Detecta las direcciones IP locales asignadas a esta computadora en la red Wi-Fi o local."""
    ips = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    
    # Intento alternativo conectando un socket dummy
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip not in ips and not ip.startswith("127."):
            ips.append(ip)
    except Exception:
        pass
        
    return ips if ips else ["127.0.0.1"]

class DialogoConfigRed(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Red Local")
        self.resize(420, 480)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        
        # Cargar configuración actual
        self.config = cargar_configuracion()
        
        self.inicializar_ui()
        self.actualizar_visibilidad_segun_modo()
        
    def inicializar_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Título principal
        lbl_titulo = QLabel("Modo de Operación en Red")
        lbl_titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #003366;")
        main_layout.addWidget(lbl_titulo)
        
        # ComboBox de selección de modo
        self.combo_modo = QComboBox()
        self.combo_modo.addItems([
            "Local (Solo esta computadora)", 
            "Cliente (Conectarse a servidor central)", 
            "Servidor (Esta computadora es la central)"
        ])
        # Mapear valor de config al índice del combo
        modo_actual = self.config.get("modo", "local")
        if modo_actual == "cliente":
            self.combo_modo.setCurrentIndex(1)
        elif modo_actual == "servidor":
            self.combo_modo.setCurrentIndex(2)
        else:
            self.combo_modo.setCurrentIndex(0)
            
        self.combo_modo.setStyleSheet("""
            QComboBox {
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 8px 12px;
                background-color: #ffffff;
                color: #24292f;
                font-size: 13px;
            }
            QComboBox:hover {
                background-color: #f6f8fa;
            }
        """)
        self.combo_modo.currentIndexChanged.connect(self.actualizar_visibilidad_segun_modo)
        main_layout.addWidget(self.combo_modo)
        
        # ----------------------------------------------------
        # GRUPO CLIENTE: Opciones de servidor destino
        # ----------------------------------------------------
        self.grupo_cliente = QGroupBox("Ajustes del Servidor Central")
        self.grupo_cliente.setStyleSheet("QGroupBox { font-weight: bold; color: #003366; }")
        layout_cliente = QVBoxLayout(self.grupo_cliente)
        layout_cliente.setSpacing(10)
        
        layout_cliente.addWidget(QLabel("Dirección IP del Servidor:"))
        self.input_ip = QLineEdit(self.config.get("servidor_ip") or self.config.get("ip_servidor") or "localhost")
        self.input_ip.setPlaceholderText("Ej. 192.168.1.15")
        self.input_ip.setStyleSheet("QLineEdit { border: 1px solid #d0d7de; border-radius: 6px; padding: 6px; }")
        layout_cliente.addWidget(self.input_ip)
        
        layout_cliente.addWidget(QLabel("Puerto del Servidor:"))
        self.input_puerto = QLineEdit(str(self.config.get("servidor_port") or self.config.get("puerto_servidor") or 5000))
        self.input_puerto.setPlaceholderText("Ej. 5000")
        self.input_puerto.setStyleSheet("QLineEdit { border: 1px solid #d0d7de; border-radius: 6px; padding: 6px; }")
        layout_cliente.addWidget(self.input_puerto)
        
        # Ayuda de verificación
        self.lbl_ayuda_cliente = QLabel(
            "<b>Verificación de Conexión:</b><br>"
            "Una vez guardado y habiendo reiniciado la app, puedes verificar la comunicación abriendo un navegador e ingresando a:<br>"
            "<u>http://[IP_SERVIDOR]:[PUERTO]/api/files/exists?path=bd/database.db</u><br>"
            "Si responde <i>{\"exists\":...}</i>, la conexión es correcta."
        )
        self.lbl_ayuda_cliente.setWordWrap(True)
        self.lbl_ayuda_cliente.setStyleSheet("color: #57606a; font-size: 11px; margin-top: 5px; line-height: 1.4;")
        layout_cliente.addWidget(self.lbl_ayuda_cliente)
        
        main_layout.addWidget(self.grupo_cliente)
        
        # ----------------------------------------------------
        # GRUPO SERVIDOR: Estado e IPs locales
        # ----------------------------------------------------
        self.grupo_servidor = QGroupBox("Estado del Servidor Central")
        self.grupo_servidor.setStyleSheet("QGroupBox { font-weight: bold; color: #003366; }")
        layout_servidor = QVBoxLayout(self.grupo_servidor)
        layout_servidor.setSpacing(10)
        
        # Estado actual
        self.lbl_estado = QLabel()
        layout_servidor.addWidget(self.lbl_estado)
        
        # Botones de control manual del servidor
        layout_controles_srv = QHBoxLayout()
        self.btn_iniciar_srv = QPushButton("Iniciar Servidor")
        self.btn_iniciar_srv.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_iniciar_srv.setStyleSheet("""
            QPushButton { 
                background-color: transparent; 
                border: 2px solid #2da44e; 
                color: #2da44e; 
                border-radius: 6px; 
                padding: 8px; 
                font-weight: bold; 
            }
            QPushButton:hover { 
                background-color: #2da44e; 
                color: white; 
            }
            QPushButton:disabled { 
                background-color: transparent; 
                border: 2px solid #eaeff2; 
                color: #949da3; 
            }
        """)
        self.btn_iniciar_srv.clicked.connect(self.iniciar_servidor_manual)
        
        self.btn_detener_srv = QPushButton("Detener Servidor")
        self.btn_detener_srv.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_detener_srv.setStyleSheet("""
            QPushButton { 
                background-color: transparent; 
                border: 2px solid #cf222e; 
                color: #cf222e; 
                border-radius: 6px; 
                padding: 8px; 
                font-weight: bold; 
            }
            QPushButton:hover { 
                background-color: #cf222e; 
                color: white; 
            }
            QPushButton:disabled { 
                background-color: transparent; 
                border: 2px solid #eaeff2; 
                color: #949da3; 
            }
        """)
        self.btn_detener_srv.clicked.connect(self.detener_servidor_manual)
        
        layout_controles_srv.addWidget(self.btn_iniciar_srv)
        layout_controles_srv.addWidget(self.btn_detener_srv)
        layout_servidor.addLayout(layout_controles_srv)
        
        # Actualizar estado (ahora que los botones están inicializados)
        self.actualizar_label_estado()
        
        # IPs locales para compartir
        ips = obtener_ips_locales()
        puerto_actual = self.config.get("servidor_port") or self.config.get("puerto_servidor") or 5000
        ips_text = "\n".join([f"  • {ip}:{puerto_actual}" for ip in ips])
        lbl_info_ips = QLabel(f"Otras computadoras en la red Wi-Fi se pueden conectar usando:\n{ips_text}")
        lbl_info_ips.setWordWrap(True)
        lbl_info_ips.setStyleSheet("color: #57606a; font-size: 11px; margin-top: 5px; line-height: 1.4;")
        layout_servidor.addWidget(lbl_info_ips)
        
        # Botón para configurar firewall (redes públicas/privadas)
        self.btn_config_firewall = QPushButton("Permitir Acceso en Firewall de Windows")
        self.btn_config_firewall.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_config_firewall.setStyleSheet("""
            QPushButton { 
                background-color: transparent; 
                border: 2px solid #0969da; 
                color: #0969da; 
                border-radius: 6px; 
                padding: 8px; 
                font-weight: bold; 
                margin-top: 5px;
            }
            QPushButton:hover { 
                background-color: #0969da; 
                color: white; 
            }
        """)
        self.btn_config_firewall.clicked.connect(self.configurar_firewall_windows)
        layout_servidor.addWidget(self.btn_config_firewall)

        # Nota aclaratoria sobre perfiles de red
        lbl_nota_firewall = QLabel(
            "Nota: En redes Públicas o Privadas, el Firewall de Windows suele bloquear la conexión de otras computadoras. "
            "Presiona el botón de arriba para abrir automáticamente los puertos necesarios."
        )
        lbl_nota_firewall.setWordWrap(True)
        lbl_nota_firewall.setStyleSheet("color: #cf222e; font-size: 11px; margin-top: 2px; font-weight: bold;")
        layout_servidor.addWidget(lbl_nota_firewall)
        
        main_layout.addWidget(self.grupo_servidor)
        
        main_layout.addStretch()
        
        # ----------------------------------------------------
        # BOTONES ACCIÓN INFERIOR
        # ----------------------------------------------------
        layout_botones = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancelar.setStyleSheet("""
            QPushButton { 
                background-color: transparent; 
                border: 2px solid #57606a; 
                color: #57606a; 
                border-radius: 6px; 
                padding: 8px 16px; 
                font-weight: bold; 
            }
            QPushButton:hover { 
                background-color: #57606a; 
                color: white; 
            }
        """)
        btn_cancelar.clicked.connect(self.reject)
        
        btn_guardar = QPushButton("Guardar Configuración")
        btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_guardar.setStyleSheet("""
            QPushButton { 
                background-color: transparent; 
                border: 2px solid #0969da; 
                color: #0969da; 
                border-radius: 6px; 
                padding: 8px 16px; 
                font-weight: bold; 
            }
            QPushButton:hover { 
                background-color: #0969da; 
                color: white; 
            }
        """)
        btn_guardar.clicked.connect(self.guardar_y_aplicar)
        
        layout_botones.addStretch()
        layout_botones.addWidget(btn_cancelar)
        layout_botones.addWidget(btn_guardar)
        main_layout.addLayout(layout_botones)

    def actualizar_visibilidad_segun_modo(self):
        idx = self.combo_modo.currentIndex()
        if idx == 0:  # Local
            self.grupo_cliente.hide()
            self.grupo_servidor.hide()
            self.resize(420, 220)
        elif idx == 1:  # Cliente
            self.grupo_cliente.show()
            self.grupo_servidor.hide()
            self.resize(420, 440)
        elif idx == 2:  # Servidor
            self.grupo_cliente.hide()
            self.grupo_servidor.show()
            self.actualizar_label_estado()
            self.resize(420, 480)

    def actualizar_label_estado(self):
        corriendo = esta_servidor_corriendo()
        if corriendo:
            self.lbl_estado.setText("Estatus: <font color='#2da44e'><b>ACTIVO (Corriendo en segundo plano)</b></font>")
            self.btn_iniciar_srv.setEnabled(False)
            self.btn_detener_srv.setEnabled(True)
        else:
            self.lbl_estado.setText("Estatus: <font color='#cf222e'><b>INACTIVO (Detenido)</b></font>")
            self.btn_iniciar_srv.setEnabled(True)
            self.btn_detener_srv.setEnabled(False)

    def iniciar_servidor_manual(self):
        try:
            puerto = int(self.input_puerto.text() if self.input_puerto.text() else 5000)
        except ValueError:
            puerto = 5000
            
        exito = iniciar_servidor_global(port=puerto)
        if exito:
            self.actualizar_label_estado()
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Éxito", f"Servidor iniciado en puerto {puerto}.", "info", self).exec()
        else:
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Error", "No se pudo iniciar el servidor.", "error", self).exec()

    def detener_servidor_manual(self):
        exito = detener_servidor_global()
        self.actualizar_label_estado()
        if exito:
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Listo", "Servidor detenido.", "info", self).exec()

    def configurar_firewall_windows(self):
        import sys
        from vistas.utilidades import DialogoNotificacion
        if sys.platform != "win32":
            DialogoNotificacion("Información", "La configuración del firewall solo es necesaria y compatible con Windows.", "info", self).exec()
            return
            
        try:
            puerto = int(self.input_puerto.text() if self.input_puerto.text() else 5000)
        except ValueError:
            puerto = 5000
            
        import ctypes
        # Comando para eliminar regla anterior si existe, y crear la nueva que permita Dominio, Privado y Público
        ps_command = (
            f"Remove-NetFirewallRule -DisplayName 'Trabajo Terminal - Servidor Microglias ({puerto})' -ErrorAction SilentlyContinue; "
            f"New-NetFirewallRule -DisplayName 'Trabajo Terminal - Servidor Microglias ({puerto})' -Direction Inbound -Action Allow "
            f"-Protocol TCP -LocalPort {puerto} -Profile Domain,Private,Public -Enabled True"
        )
        
        try:
            # Solicitar ejecución como Administrador (UAC prompt)
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                "powershell.exe", 
                f"-Command \"{ps_command}\"", 
                None, 
                1 # SW_SHOWNORMAL
            )
            # Si ret > 32 indica que se inició la solicitud
            if int(ret) > 32:
                DialogoNotificacion(
                    "Permiso Solicitado", 
                    "Se ha solicitado permiso de administrador para abrir el puerto en el Firewall de Windows.<br><br>"
                    "Por favor, acepta la ventana de confirmación (UAC) para permitir que otras computadoras se conecten en redes públicas o privadas.", 
                    "info", 
                    self
                ).exec()
            else:
                DialogoNotificacion("Error", "No se pudo solicitar la elevación de permisos.", "error", self).exec()
        except Exception as e:
            DialogoNotificacion("Error", f"Error al configurar firewall: {e}", "error", self).exec()

    def guardar_y_aplicar(self):
        idx = self.combo_modo.currentIndex()
        modos = ["local", "cliente", "servidor"]
        nuevo_modo = modos[idx]
        
        ip_server = self.input_ip.text().strip()
        try:
            puerto_server = int(self.input_puerto.text().strip())
        except ValueError:
            puerto_server = 5000
            
        # Validar IP
        if nuevo_modo == "cliente" and not ip_server:
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Atención", "Por favor ingresa la IP del servidor.", "warning", self).exec()
            return
            
        # Guardar en JSON
        self.config["modo"] = nuevo_modo
        self.config["servidor_ip"] = ip_server
        self.config["ip_servidor"] = ip_server
        self.config["servidor_port"] = puerto_server
        self.config["puerto_servidor"] = puerto_server
        guardar_configuracion(self.config)
        
        # Aplicar hilos según el modo guardado
        if nuevo_modo == "servidor":
            if not esta_servidor_corriendo():
                iniciar_servidor_global(port=puerto_server)
        else:
            # Si cambió a local o cliente, apagar el servidor si estaba corriendo en esta máquina
            detener_servidor_global()
            
        from vistas.utilidades import DialogoNotificacion
        DialogoNotificacion(
            "Configuración Guardada", 
            f"El modo de operación ahora es: <b>{nuevo_modo.upper()}</b>.<br><br>"
            "Por favor, reinicia la aplicación para aplicar todos los cambios de conexión.", 
            "info", 
            self
        ).exec()
        
        self.accept()
