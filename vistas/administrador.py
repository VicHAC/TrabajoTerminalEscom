import sqlite3
import hashlib
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QLabel, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QFrame, QDialog, QLineEdit, QComboBox, QMessageBox,
                             QStackedWidget)
from PyQt6.QtCore import Qt

# ==========================================
# POP-UP: CREAR USUARIO
# ==========================================
class DialogoCrearUsuario(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registrar Nuevo Usuario")
        self.resize(300, 250)
        
        layout = QVBoxLayout()
        self.input_usuario = QLineEdit()
        self.input_usuario.setPlaceholderText("Nombre de Usuario")
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Contraseña")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.combo_rol = QComboBox()
        self.combo_rol.addItems(["Investigador", "Administrador"])
        
        btn_guardar = QPushButton("Registrar")
        btn_guardar.setStyleSheet("background-color: #003366; color: white; padding: 8px;")
        btn_guardar.clicked.connect(self.guardar_en_bd)
        
        layout.addWidget(QLabel("Datos del nuevo usuario:"))
        layout.addWidget(self.input_usuario)
        layout.addWidget(self.input_password)
        layout.addWidget(QLabel("Rol:"))
        layout.addWidget(self.combo_rol)
        layout.addSpacing(15)
        layout.addWidget(btn_guardar)
        self.setLayout(layout)

    def guardar_en_bd(self):
        usuario = self.input_usuario.text()
        password = self.input_password.text()
        rol = self.combo_rol.currentText()
        
        if not usuario or not password:
            QMessageBox.warning(self, "Llena todos los campos.")
            return
            
        pass_hash = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            conexion = sqlite3.connect("bd/database.db")
            cursor = conexion.cursor()
            cursor.execute("INSERT INTO Usuario (nombre_usuario, contrasenia_hash, rol) VALUES (?, ?, ?)", 
                           (usuario, pass_hash, rol))
            conexion.commit()
            conexion.close()
            QMessageBox.information(self, "Éxito", "Usuario registrado.")
            self.accept()
        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "Error", "Ese usuario ya existe.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Tronó la BD: {e}")

# ==========================================
# POP-UP: EDITAR USUARIO 
# ==========================================
class DialogoEditarUsuario(QDialog):
    def __init__(self, id_usuario, nombre_actual, rol_actual, parent=None):
        super().__init__(parent)
        self.id_usuario = id_usuario
        self.setWindowTitle("Editar Usuario")
        self.resize(300, 250)
        
        layout = QVBoxLayout()
        self.input_usuario = QLineEdit(nombre_actual)
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Nueva contraseña (en blanco = no cambia)")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.combo_rol = QComboBox()
        self.combo_rol.addItems(["Investigador", "Administrador"])
        self.combo_rol.setCurrentText(rol_actual) 
        
        btn_guardar = QPushButton("Actualizar")
        btn_guardar.setStyleSheet("background-color: #003366; color: white; padding: 8px;")
        btn_guardar.clicked.connect(self.actualizar_en_bd)
        
        layout.addWidget(QLabel("Modificar datos:"))
        layout.addWidget(self.input_usuario)
        layout.addWidget(self.input_password)
        layout.addWidget(QLabel("Rol:"))
        layout.addWidget(self.combo_rol)
        layout.addSpacing(15)
        layout.addWidget(btn_guardar)
        self.setLayout(layout)

    def actualizar_en_bd(self):
        nuevo_nombre = self.input_usuario.text()
        nueva_pass = self.input_password.text()
        nuevo_rol = self.combo_rol.currentText()
        
        if not nuevo_nombre:
            QMessageBox.warning(self, "El nombre no puede estar vacío.")
            return
            
        try:
            conexion = sqlite3.connect("bd/database.db")
            cursor = conexion.cursor()
            
            if nueva_pass: 
                pass_hash = hashlib.sha256(nueva_pass.encode()).hexdigest()
                cursor.execute("UPDATE Usuario SET nombre_usuario=?, contrasenia_hash=?, rol=? WHERE id_usuario=?", 
                               (nuevo_nombre, pass_hash, nuevo_rol, self.id_usuario))
            else: 
                cursor.execute("UPDATE Usuario SET nombre_usuario=?, rol=? WHERE id_usuario=?", 
                               (nuevo_nombre, nuevo_rol, self.id_usuario))
                               
            conexion.commit()
            conexion.close()
            QMessageBox.information(self, "Éxito", "Usuario actualizado.")
            self.accept()
        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "Error", "Ese nombre de usuario ya está ocupado.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Murio la BD: {e}")

# ==========================================
# VENTANA PRINCIPAL DEL ADMINISTRADOR
# ==========================================
class VentanaAdministrador(QMainWindow):
    def __init__(self, id_usuario):
        super().__init__()
        self.id_usuario = id_usuario
        self.setWindowTitle("Prototipo Microglías - Panel de Administración")
        self.resize(1000, 600)
        self.inicializar_ui()

    def inicializar_ui(self):
        widget_central = QWidget()
        layout_principal = QHBoxLayout()
        
        # --- MENU LATERAL ---
        menu_lateral = QVBoxLayout()
        menu_lateral.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        label_bienvenida = QLabel("Panel Admin")
        label_bienvenida.setStyleSheet("font-weight: bold; font-size: 18px; margin-bottom: 20px;")
        menu_lateral.addWidget(label_bienvenida)

        self.btn_usuarios = QPushButton("Ver Usuarios")
        self.btn_registrar = QPushButton("Registrar Usuario")
        self.btn_editar = QPushButton("Editar Usuario")
        self.btn_eliminar = QPushButton("Eliminar Usuario")
        self.btn_reportes = QPushButton("Gestionar Reportes")

        estilo_btn_menu = """
            QPushButton {
                background-color: transparent; 
                text-align: left; 
                padding: 10px; 
                font-weight: normal;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
                border-radius: 5px;
            }
        """
        for btn in [self.btn_usuarios, self.btn_registrar, self.btn_editar, self.btn_eliminar, self.btn_reportes]:
            btn.setStyleSheet(estilo_btn_menu)
            menu_lateral.addWidget(btn)

        # Boton de cerrar sesión
        menu_lateral.addStretch() # Empuja el botón al fondo
        self.btn_cerrar_sesion = QPushButton("Cerrar Sesión")
        self.btn_cerrar_sesion.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                border: 2px solid #cc0000; 
                color: #cc0000; 
                font-weight: bold; 
                border-radius: 8px; 
                padding: 10px; 
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #cc0000;
                color: white;
            }
        """)
        menu_lateral.addWidget(self.btn_cerrar_sesion)

        frame_menu = QFrame()
        frame_menu.setObjectName("menu_lateral")
        frame_menu.setFixedWidth(200)
        frame_menu.setLayout(menu_lateral)

        # --- AREA CENTRAL ---
        self.stack = QStackedWidget()

        # Vista de Usuarios 
        pagina_usuarios = QWidget()
        layout_usuarios = QVBoxLayout(pagina_usuarios)
        titulo_usuarios = QLabel("Usuarios Registrados")
        titulo_usuarios.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        
        self.tabla_usuarios = QTableWidget()
        self.tabla_usuarios.setColumnCount(4)
        self.tabla_usuarios.setHorizontalHeaderLabels(["ID", "Nombre de Usuario", "Rol", "Fecha Creación"])
        self.tabla_usuarios.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_usuarios.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_usuarios.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout_usuarios.addWidget(titulo_usuarios)
        layout_usuarios.addWidget(self.tabla_usuarios)

        # Vista de Reportes 
        pagina_reportes = QWidget()
        layout_reportes = QVBoxLayout(pagina_reportes)
        titulo_reportes = QLabel("Reportes del Sistema")
        titulo_reportes.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        
        self.tabla_reportes = QTableWidget()
        self.tabla_reportes.setColumnCount(4)
        self.tabla_reportes.setHorizontalHeaderLabels(["ID Reporte", "ID Análisis", "Ruta Archivo", "Fecha Generación"])
        self.tabla_reportes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_reportes.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_reportes.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        self.btn_eliminar_reporte_fisico = QPushButton("Eliminar Reporte Seleccionado")
        self.btn_eliminar_reporte_fisico.setStyleSheet("background-color: darkred; color: white; padding: 10px;")
        
        layout_reportes.addWidget(titulo_reportes)
        layout_reportes.addWidget(self.tabla_reportes)
        layout_reportes.addWidget(self.btn_eliminar_reporte_fisico)

        self.stack.addWidget(pagina_usuarios)
        self.stack.addWidget(pagina_reportes)

        layout_principal.addWidget(frame_menu)
        layout_principal.addWidget(self.stack)

        widget_central.setLayout(layout_principal)
        self.setCentralWidget(widget_central)

        # --- CONEXIONES ---
        self.btn_cerrar_sesion.clicked.connect(self.cerrar_sesion)
        self.btn_usuarios.clicked.connect(self.mostrar_vista_usuarios)
        self.btn_reportes.clicked.connect(self.mostrar_vista_reportes)
        self.btn_registrar.clicked.connect(self.abrir_registro_usuario)
        self.btn_editar.clicked.connect(self.abrir_editar_usuario)
        self.btn_eliminar.clicked.connect(self.eliminar_usuario)
        self.btn_eliminar_reporte_fisico.clicked.connect(self.eliminar_reporte)

        self.cargar_usuarios_bd()

    def mostrar_vista_usuarios(self):
        self.stack.setCurrentIndex(0)
        self.cargar_usuarios_bd()

    def mostrar_vista_reportes(self):
        self.stack.setCurrentIndex(1)
        self.cargar_reportes_bd()

    def cargar_usuarios_bd(self):
        self.tabla_usuarios.setRowCount(0)
        try:
            conexion = sqlite3.connect("bd/database.db")
            cursor = conexion.cursor()
            cursor.execute("SELECT id_usuario, nombre_usuario, rol, fecha_creacion FROM Usuario")
            usuarios = cursor.fetchall()
            conexion.close()

            self.tabla_usuarios.setRowCount(len(usuarios))
            for fila_idx, fila_datos in enumerate(usuarios):
                for col_idx, dato in enumerate(fila_datos):
                    self.tabla_usuarios.setItem(fila_idx, col_idx, QTableWidgetItem(str(dato)))
        except Exception as e:
            print(f"Error al cargar usuarios: {e}")

    def abrir_registro_usuario(self):
        self.stack.setCurrentIndex(0) 
        dialogo = DialogoCrearUsuario(self)
        if dialogo.exec(): 
            self.cargar_usuarios_bd()

    def abrir_editar_usuario(self):
        self.stack.setCurrentIndex(0)
        fila_seleccionada = self.tabla_usuarios.currentRow()
        
        if fila_seleccionada < 0:
            QMessageBox.warning(self, "Ey", "Selecciona a una persona de la tabla primero.")
            return
            
        id_usuario = self.tabla_usuarios.item(fila_seleccionada, 0).text()
        nombre = self.tabla_usuarios.item(fila_seleccionada, 1).text()
        rol = self.tabla_usuarios.item(fila_seleccionada, 2).text()
        
        dialogo = DialogoEditarUsuario(id_usuario, nombre, rol, self)
        if dialogo.exec():
            self.cargar_usuarios_bd()

    def eliminar_usuario(self):
        self.stack.setCurrentIndex(0)
        fila_seleccionada = self.tabla_usuarios.currentRow()
        
        if fila_seleccionada < 0:
            QMessageBox.warning(self, "Ey", "Selecciona a una persona de la tabla primero para darle cuello.")
            return
            
        id_usuario_eliminar = self.tabla_usuarios.item(fila_seleccionada, 0).text()
        nombre_usuario = self.tabla_usuarios.item(fila_seleccionada, 1).text()
        
        if str(self.id_usuario) == id_usuario_eliminar:
            QMessageBox.critical(self, "Error", "No te puedes borrar a ti mismo.")
            return

        respuesta = QMessageBox.question(self, "Confirmar", f"¿Seguro que quieres borrar a {nombre_usuario}?", 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                conexion = sqlite3.connect("bd/database.db")
                cursor = conexion.cursor()
                cursor.execute("DELETE FROM Usuario WHERE id_usuario = ?", (id_usuario_eliminar,))
                conexion.commit()
                conexion.close()
                QMessageBox.information(self, "Sobres", "Usuario eliminado.")
                self.cargar_usuarios_bd()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Tronó la BD al eliminar: {e}")

    def cargar_reportes_bd(self):
        self.tabla_reportes.setRowCount(0)
        try:
            conexion = sqlite3.connect("bd/database.db")
            cursor = conexion.cursor()
            cursor.execute("SELECT id_reporte, id_analisis, ruta_archivo, fecha_generacion FROM Reporte")
            reportes = cursor.fetchall()
            conexion.close()

            self.tabla_reportes.setRowCount(len(reportes))
            for fila_idx, fila_datos in enumerate(reportes):
                for col_idx, dato in enumerate(fila_datos):
                    self.tabla_reportes.setItem(fila_idx, col_idx, QTableWidgetItem(str(dato)))
        except Exception as e:
            print(f"Error al cargar reportes: {e}")

    def eliminar_reporte(self):
        fila_seleccionada = self.tabla_reportes.currentRow()
        
        if fila_seleccionada < 0:
            QMessageBox.warning(self, "Ey", "Selecciona un reporte de la tabla primero.")
            return
            
        id_reporte = self.tabla_reportes.item(fila_seleccionada, 0).text()
        ruta_archivo = self.tabla_reportes.item(fila_seleccionada, 2).text()

        respuesta = QMessageBox.question(self, "Confirmar", "¿Seguro que quieres borrar este reporte? Se eliminará físicamente.", 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                conexion = sqlite3.connect("bd/database.db")
                cursor = conexion.cursor()
                cursor.execute("DELETE FROM Reporte WHERE id_reporte = ?", (id_reporte,))
                conexion.commit()
                conexion.close()

                if os.path.exists(ruta_archivo):
                    os.remove(ruta_archivo)
                
                QMessageBox.information(self, "Listo", "Reporte eliminado de la BD y del disco.")
                self.cargar_reportes_bd()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Hubo un pedo al eliminar: {e}")

    def cerrar_sesion(self):
        from vistas.login import VentanaLogin
        self.ventana_login = VentanaLogin()
        self.ventana_login.setObjectName("ventana_login")
        self.ventana_login.show()
        self.close()