import sqlite3
import hashlib
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QLabel, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QFrame, QDialog, QLineEdit, QComboBox,
                             QStackedWidget)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

# ==========================================
# POP-UP: CREAR USUARIO
# ==========================================
class DialogoCrearUsuario(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registrar Nuevo Usuario")
        self.resize(300, 250)
        
        from vistas.utilidades import set_app_icon
        set_app_icon(self)
        
        layout = QVBoxLayout()
        self.input_usuario = QLineEdit()
        self.input_usuario.setPlaceholderText("Nombre de Usuario")
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Contraseña")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.combo_rol = QComboBox()
        self.combo_rol.addItems(["Administrador", "Investigador", "Tesista"])
        self.combo_rol.setStyleSheet("""
            QComboBox {
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 6px 10px;
                background-color: #ffffff;
                color: #24292f;
            }
        """)
        
        btn_guardar = QPushButton("Registrar")
        btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                border: 2px solid #2da44e; 
                color: #2da44e; 
                font-weight: bold; 
                border-radius: 8px; 
                padding: 10px; 
            }
            QPushButton:hover {
                background-color: #2da44e;
                color: white;
            }
        """)
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
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Atención", "Llena todos los campos.", "warning", self).exec()
            return
            
        pass_hash = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            conexion = sqlite3.connect("bd/database.db")
            cursor = conexion.cursor()
            cursor.execute("INSERT INTO Usuario (nombre_usuario, contrasenia_hash, rol) VALUES (?, ?, ?)", 
                           (usuario, pass_hash, rol))
            conexion.commit()
            conexion.close()
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Éxito", "Usuario registrado.", "info", self).exec()
            self.accept()
        except sqlite3.IntegrityError:
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Error", "Ese usuario ya existe.", "error", self).exec()
        except Exception as e:
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Error", f"Tronó la BD: {e}", "error", self).exec()

# ==========================================
# POP-UP: EDITAR USUARIO 
# ==========================================
class DialogoEditarUsuario(QDialog):
    def __init__(self, id_usuario, nombre_actual, rol_actual, parent=None):
        super().__init__(parent)
        self.id_usuario = id_usuario
        self.setWindowTitle("Editar Usuario")
        self.resize(300, 250)
        
        from vistas.utilidades import set_app_icon
        set_app_icon(self)
        
        layout = QVBoxLayout()
        self.input_usuario = QLineEdit(nombre_actual)
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Nueva contraseña (en blanco = no cambia)")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.combo_rol = QComboBox()
        self.combo_rol.addItems(["Administrador", "Investigador", "Tesista"])
        self.combo_rol.setCurrentText(rol_actual) 
        self.combo_rol.setStyleSheet("""
            QComboBox {
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 6px 10px;
                background-color: #ffffff;
                color: #24292f;
            }
        """)
        
        btn_guardar = QPushButton("Actualizar")
        btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                border: 2px solid #0969da; 
                color: #0969da; 
                font-weight: bold; 
                border-radius: 8px; 
                padding: 10px; 
            }
            QPushButton:hover {
                background-color: #0969da;
                color: white;
            }
        """)
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
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Atención", "El nombre no puede estar vacío.", "warning", self).exec()
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
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Éxito", "Usuario actualizado.", "info", self).exec()
            self.accept()
        except sqlite3.IntegrityError:
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Error", "Ese nombre de usuario ya está ocupado.", "error", self).exec()
        except Exception as e:
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Error", f"Murio la BD: {e}", "error", self).exec()

# ==========================================
# VENTANA PRINCIPAL DEL ADMINISTRADOR
# ==========================================
class VentanaAdministrador(QMainWindow):
    def __init__(self, id_usuario):
        super().__init__()
        self.id_usuario = id_usuario
        self.setWindowTitle("Prototipo Microglías - Panel de Administración")
        self.resize(1000, 600)
        
        from vistas.utilidades import set_app_icon
        set_app_icon(self)
        
        self.setStyleSheet("""
            QToolTip {
                background-color: #24292f;
                color: #ffffff;
                border: 1px solid #24292f;
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 10px;
            }
        """)
        
        self.inicializar_ui()

    def inicializar_ui(self):
        widget_central = QWidget()
        layout_principal = QHBoxLayout()
        
        # --- MENU LATERAL ---
        menu_lateral = QVBoxLayout()
        menu_lateral.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        label_bienvenida = QLabel("Administrador(a)")
        label_bienvenida.setStyleSheet("font-weight: bold; font-size: 16px; color: #0969da; margin-bottom: 2px; padding-left: 10px;")
        
        # Obtener nombre del administrador logueado
        nombre_admin = "Administrador"
        try:
            import sqlite3
            conexion = sqlite3.connect("bd/database.db")
            cursor = conexion.cursor()
            cursor.execute("SELECT nombre_usuario FROM Usuario WHERE id_usuario = ?", (self.id_usuario,))
            res = cursor.fetchone()
            if res:
                nombre_admin = res[0]
            conexion.close()
        except Exception as e:
            print(f"Error al obtener nombre de admin: {e}")
            
        label_usuario_logueado = QLabel(nombre_admin)
        label_usuario_logueado.setStyleSheet("font-size: 11px; color: #57606a; margin-bottom: 20px; padding-left: 10px;")
        
        menu_lateral.addWidget(label_bienvenida)
        menu_lateral.addWidget(label_usuario_logueado)

        self.btn_usuarios = QPushButton("Usuarios")
        self.btn_reportes = QPushButton("Gestionar reportes")

        self.estilo_activo = """
            QPushButton {
                background-color: #ddf4ff; 
                text-align: left; 
                padding: 10px; 
                font-weight: bold;
                color: #0969da;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
        """
        self.estilo_inactivo = """
            QPushButton {
                background-color: transparent; 
                text-align: left; 
                padding: 10px; 
                font-weight: normal;
                color: #24292f;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #f6f8fa;
                border-radius: 6px;
            }
        """
        
        for btn in [self.btn_usuarios, self.btn_reportes]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        
        # Cabecera de usuarios (Título y Botones de añadir, editar y borrar)
        header_usuarios = QHBoxLayout()
        header_usuarios.setContentsMargins(0, 0, 0, 10)
        
        titulo_usuarios = QLabel("Usuarios Registrados")
        titulo_usuarios.setStyleSheet("font-size: 15px; font-weight: bold; color: #3a61a0;")
        
        self.btn_registrar_usuario = QPushButton()
        self.btn_registrar_usuario.setIcon(QIcon("assets/buttons/añadir.png"))
        self.btn_registrar_usuario.setIconSize(QSize(22, 22))
        self.btn_registrar_usuario.setFixedSize(35, 35)
        self.btn_registrar_usuario.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_registrar_usuario.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; }
            QPushButton:hover { background-color: #ddf4ff; border-radius: 17px; }
            QPushButton:disabled { opacity: 0.3; }
        """)
        self.btn_registrar_usuario.setEnabled(True)
        self.btn_registrar_usuario.setToolTip("Crear usuario")
        
        self.btn_editar_usuario = QPushButton()
        self.btn_editar_usuario.setIcon(QIcon("assets/buttons/editar.png"))
        self.btn_editar_usuario.setIconSize(QSize(22, 22))
        self.btn_editar_usuario.setFixedSize(35, 35)
        self.btn_editar_usuario.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_editar_usuario.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; }
            QPushButton:hover { background-color: #ddf4ff; border-radius: 17px; }
            QPushButton:disabled { opacity: 0.3; }
        """)
        self.btn_editar_usuario.setEnabled(False)
        self.btn_editar_usuario.setToolTip("Editar usuario")
        
        self.btn_eliminar_usuario = QPushButton()
        self.btn_eliminar_usuario.setIcon(QIcon("assets/buttons/borrar.png"))
        self.btn_eliminar_usuario.setIconSize(QSize(22, 22))
        self.btn_eliminar_usuario.setFixedSize(35, 35)
        self.btn_eliminar_usuario.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eliminar_usuario.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; }
            QPushButton:hover { background-color: #ddf4ff; border-radius: 17px; }
            QPushButton:disabled { opacity: 0.3; }
        """)
        self.btn_eliminar_usuario.setEnabled(False)
        self.btn_eliminar_usuario.setToolTip("Eliminar usuario(s)")
        
        header_usuarios.addWidget(titulo_usuarios)
        header_usuarios.addStretch()
        header_usuarios.addWidget(self.btn_registrar_usuario)
        header_usuarios.addWidget(self.btn_editar_usuario)
        header_usuarios.addWidget(self.btn_eliminar_usuario)
        self.btn_eliminar_usuario.installEventFilter(self)
        
        self.tabla_usuarios = QTableWidget()
        self.tabla_usuarios.setColumnCount(5)
        self.tabla_usuarios.setHorizontalHeaderLabels(["ID", "Nombre de Usuario", "Rol", "Fecha Creación", "Última Conexión"])
        self.tabla_usuarios.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_usuarios.verticalHeader().setVisible(False)
        self.tabla_usuarios.setCornerButtonEnabled(False)
        self.tabla_usuarios.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_usuarios.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_usuarios.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.tabla_usuarios.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #d0d7de;
                gridline-color: #f0f0f0;
                color: #24292f;
                font-size: 12px;
                border-radius: 6px;
                outline: none;
            }
            QTableWidget::item {
                padding: 6px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #ddf4ff;
                color: #0969da;
            }
            QHeaderView::section {
                background-color: #f6f8fa;
                color: #57606a;
                padding: 6px;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #d0d7de;
                border-top: none;
                border-left: none;
            }
        """)
        
        layout_usuarios.addLayout(header_usuarios)
        layout_usuarios.addWidget(self.tabla_usuarios)

        # Vista de Reportes 
        pagina_reportes = QWidget()
        layout_reportes = QVBoxLayout(pagina_reportes)
        
        # Cabecera de reportes (Título y Botón de borrar)
        header_reportes = QHBoxLayout()
        header_reportes.setContentsMargins(0, 0, 0, 10)
        
        titulo_reportes = QLabel("Reportes del Sistema")
        titulo_reportes.setStyleSheet("font-size: 15px; font-weight: bold; color: #3a61a0;")
        
        self.btn_eliminar_reporte_fisico = QPushButton()
        self.btn_eliminar_reporte_fisico.setIcon(QIcon("assets/buttons/borrar.png"))
        self.btn_eliminar_reporte_fisico.setIconSize(QSize(22, 22))
        self.btn_eliminar_reporte_fisico.setFixedSize(35, 35)
        self.btn_eliminar_reporte_fisico.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eliminar_reporte_fisico.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; }
            QPushButton:hover { background-color: #ddf4ff; border-radius: 17px; }
            QPushButton:disabled { opacity: 0.3; }
        """)
        self.btn_eliminar_reporte_fisico.setEnabled(False)
        self.btn_eliminar_reporte_fisico.setToolTip("Eliminar reporte(s)")
        
        header_reportes.addWidget(titulo_reportes)
        header_reportes.addStretch()
        header_reportes.addWidget(self.btn_eliminar_reporte_fisico)
        self.btn_eliminar_reporte_fisico.installEventFilter(self)
        
        self.tabla_reportes = QTableWidget()
        self.tabla_reportes.setColumnCount(8)
        self.tabla_reportes.setHorizontalHeaderLabels([
            "ID Reporte", 
            "ID Análisis", 
            "Nombre del\nReporte", 
            "Autor", 
            "Colaborador",
            "Estatus del analisis", 
            "Fecha de\nGeneración", 
            "Ruta Archivo"
        ])
        self.tabla_reportes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tabla_reportes.horizontalHeader().setStretchLastSection(True)
        self.tabla_reportes.horizontalHeader().setMinimumHeight(50)
        self.tabla_reportes.verticalHeader().setVisible(False)
        self.tabla_reportes.setCornerButtonEnabled(False)
        self.tabla_reportes.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_reportes.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_reportes.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.tabla_reportes.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #d0d7de;
                gridline-color: #f0f0f0;
                color: #24292f;
                font-size: 12px;
                border-radius: 6px;
                outline: none;
            }
            QTableWidget::item {
                padding: 6px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #ddf4ff;
                color: #0969da;
            }
            QHeaderView::section {
                background-color: #f6f8fa;
                color: #57606a;
                padding: 6px;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #d0d7de;
                border-top: none;
                border-left: none;
            }
        """)
        
        layout_reportes.addLayout(header_reportes)
        layout_reportes.addWidget(self.tabla_reportes)

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
        self.btn_registrar_usuario.clicked.connect(self.abrir_registro_usuario)
        self.btn_editar_usuario.clicked.connect(self.abrir_editar_usuario)
        self.btn_eliminar_usuario.clicked.connect(self.eliminar_usuario)
        self.btn_eliminar_reporte_fisico.clicked.connect(self.eliminar_reporte)
        self.tabla_usuarios.itemSelectionChanged.connect(self.actualizar_estado_botones_usuario)
        self.tabla_reportes.itemSelectionChanged.connect(self.actualizar_estado_boton_borrar)

        self.cargar_usuarios_bd()
        self.actualizar_estilo_menu()

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent, QPoint
        from PyQt6.QtWidgets import QToolTip
        if event.type() == QEvent.Type.ToolTip:
            if obj in (self.btn_eliminar_usuario, self.btn_eliminar_reporte_fisico):
                # Obtener la posición global de la esquina inferior del botón
                global_pos = obj.mapToGlobal(obj.rect().bottomLeft())
                # Mostrar el tooltip desplazado a la izquierda (por ejemplo, -95px en X) para que se vea completo
                custom_x = global_pos.x() - 95
                custom_y = global_pos.y() - 15
                QToolTip.showText(QPoint(custom_x, custom_y), obj.toolTip(), obj)
                return True
        return super().eventFilter(obj, event)

    def actualizar_estilo_menu(self):
        index = self.stack.currentIndex()
        if index == 0:
            self.btn_usuarios.setStyleSheet(self.estilo_activo)
            self.btn_reportes.setStyleSheet(self.estilo_inactivo)
        else:
            self.btn_usuarios.setStyleSheet(self.estilo_inactivo)
            self.btn_reportes.setStyleSheet(self.estilo_activo)

    def mostrar_vista_usuarios(self):
        self.stack.setCurrentIndex(0)
        self.cargar_usuarios_bd()
        self.actualizar_estilo_menu()

    def mostrar_vista_reportes(self):
        self.stack.setCurrentIndex(1)
        self.cargar_reportes_bd()
        self.actualizar_estilo_menu()

    def cargar_usuarios_bd(self):
        self.tabla_usuarios.blockSignals(True)
        self.tabla_usuarios.setRowCount(0)
        try:
            conexion = sqlite3.connect("bd/database.db")
            cursor = conexion.cursor()
            cursor.execute("SELECT id_usuario, nombre_usuario, rol, fecha_creacion FROM Usuario")
            usuarios = cursor.fetchall()

            self.tabla_usuarios.setRowCount(len(usuarios))
            for fila_idx, fila_datos in enumerate(usuarios):
                id_u, name, rol, fecha = fila_datos
                
                # Obtener última conexión de la tabla Sesion
                cursor.execute("""
                    SELECT fecha_inicio 
                    FROM Sesion 
                    WHERE id_usuario = ? 
                    ORDER BY fecha_inicio DESC 
                    LIMIT 1
                """, (id_u,))
                res_ses = cursor.fetchone()
                conexion_text = res_ses[0] if res_ses else "Sin actividad"
                
                self.tabla_usuarios.setItem(fila_idx, 0, QTableWidgetItem(str(id_u)))
                self.tabla_usuarios.setItem(fila_idx, 1, QTableWidgetItem(str(name)))
                self.tabla_usuarios.setItem(fila_idx, 2, QTableWidgetItem(str(rol)))
                self.tabla_usuarios.setItem(fila_idx, 3, QTableWidgetItem(str(fecha)))
                self.tabla_usuarios.setItem(fila_idx, 4, QTableWidgetItem(conexion_text))
                
            conexion.close()
        except Exception as e:
            print(f"Error al cargar usuarios: {e}")
        finally:
            self.tabla_usuarios.blockSignals(False)
            self.actualizar_estado_botones_usuario()

    def actualizar_estado_botones_usuario(self):
        filas_seleccionadas = self.tabla_usuarios.selectionModel().selectedRows()
        num_seleccionados = len(filas_seleccionadas)
        
        # El de editar solo se activa si hay exactamente 1 seleccionado
        self.btn_editar_usuario.setEnabled(num_seleccionados == 1)
        
        # El de borrar se activa con uno o más, siempre y cuando NO esté el usuario activo
        if num_seleccionados == 0:
            self.btn_eliminar_usuario.setEnabled(False)
        else:
            contiene_activo = False
            for index in filas_seleccionadas:
                row = index.row()
                item_id = self.tabla_usuarios.item(row, 0)
                if item_id and item_id.text() == str(self.id_usuario):
                    contiene_activo = True
                    break
            self.btn_eliminar_usuario.setEnabled(not contiene_activo)

    def abrir_registro_usuario(self):
        self.stack.setCurrentIndex(0) 
        dialogo = DialogoCrearUsuario(self)
        if dialogo.exec(): 
            self.cargar_usuarios_bd()

    def abrir_editar_usuario(self):
        self.stack.setCurrentIndex(0)
        filas_seleccionadas = self.tabla_usuarios.selectionModel().selectedRows()
        if len(filas_seleccionadas) != 1:
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Atención", "Selecciona exactamente a una persona de la tabla primero.", "warning", self).exec()
            return
            
        row = filas_seleccionadas[0].row()
        id_usuario = self.tabla_usuarios.item(row, 0).text()
        nombre = self.tabla_usuarios.item(row, 1).text()
        rol = self.tabla_usuarios.item(row, 2).text()
        
        dialogo = DialogoEditarUsuario(id_usuario, nombre, rol, self)
        if dialogo.exec():
            self.cargar_usuarios_bd()

    def eliminar_usuario(self):
        self.stack.setCurrentIndex(0)
        filas_seleccionadas = self.tabla_usuarios.selectionModel().selectedRows()
        
        if not filas_seleccionadas:
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Atención", "Selecciona a una persona de la tabla primero.", "warning", self).exec()
            return
            
        # Recopilar IDs y nombres
        ids_a_eliminar = []
        nombres_a_eliminar = []
        for index in filas_seleccionadas:
            row = index.row()
            item_id = self.tabla_usuarios.item(row, 0)
            item_nombre = self.tabla_usuarios.item(row, 1)
            if not item_id or not item_nombre:
                continue
            id_val = item_id.text()
            if id_val == str(self.id_usuario):
                from vistas.utilidades import DialogoNotificacion
                DialogoNotificacion("Error", "No te puedes borrar a ti mismo.", "error", self).exec()
                return
            ids_a_eliminar.append(id_val)
            nombres_a_eliminar.append(item_nombre.text())

        from vistas.utilidades import DialogoConfirmacion
        if len(ids_a_eliminar) == 1:
            msg = f"¿Seguro que quieres borrar a {nombres_a_eliminar[0]}?"
        else:
            msg = f"¿Seguro que quieres borrar a los {len(ids_a_eliminar)} usuarios seleccionados?"
            
        dialogo = DialogoConfirmacion("Confirmar", msg, self)
        
        if dialogo.exec() and dialogo.resultado:
            try:
                conexion = sqlite3.connect("bd/database.db")
                cursor = conexion.cursor()
                for id_val in ids_a_eliminar:
                    cursor.execute("DELETE FROM Usuario WHERE id_usuario = ?", (id_val,))
                conexion.commit()
                conexion.close()
                from vistas.utilidades import DialogoNotificacion
                DialogoNotificacion("Sobres", "Usuario(s) eliminado(s).", "info", self).exec()
                self.cargar_usuarios_bd()
            except Exception as e:
                from vistas.utilidades import DialogoNotificacion
                DialogoNotificacion("Error", f"Tronó la BD al eliminar: {e}", "error", self).exec()

    def cargar_reportes_bd(self):
        self.tabla_reportes.setRowCount(0)
        try:
            conexion = sqlite3.connect("bd/database.db")
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT 
                    R.id_reporte, 
                    COALESCE(A.id_analisis, 'Sin análisis'), 
                    COALESCE(R.nombre_reporte, 'Sin nombre'), 
                    COALESCE(U.nombre_usuario, 'Desconocido'),
                    COALESCE(
                        (SELECT U2.nombre_usuario 
                         FROM ReporteCompartido RC 
                         JOIN Usuario U2 ON RC.id_destinatario = U2.id_usuario 
                         WHERE RC.id_reporte = R.id_reporte LIMIT 1),
                        'Sin colaborador'
                    ),
                    CASE WHEN A.paso_actual >= 5 THEN 'Completado' ELSE 'Incompleto' END,
                    COALESCE(A.fecha_analisis, R.fecha_creacion),
                    COALESCE(I.ruta_archivo, 'Sin archivo')
                FROM Reporte R
                LEFT JOIN Analisis A ON R.id_reporte = A.id_reporte
                LEFT JOIN Imagen I ON A.id_imagen = I.id_imagen
                LEFT JOIN Usuario U ON R.id_usuario = U.id_usuario
            """)
            reportes = cursor.fetchall()
            conexion.close()

            self.tabla_reportes.setRowCount(len(reportes))
            for fila_idx, fila_datos in enumerate(reportes):
                for col_idx, dato in enumerate(fila_datos):
                    self.tabla_reportes.setItem(fila_idx, col_idx, QTableWidgetItem(str(dato)))
            self.tabla_reportes.resizeColumnsToContents()
        except Exception as e:
            print(f"Error al cargar reportes: {e}")
        finally:
            self.actualizar_estado_boton_borrar()

    def actualizar_estado_boton_borrar(self):
        num_seleccionados = len(self.tabla_reportes.selectionModel().selectedRows())
        self.btn_eliminar_reporte_fisico.setEnabled(num_seleccionados > 0)

    def eliminar_reporte(self):
        filas_seleccionadas = self.tabla_reportes.selectionModel().selectedRows()
        
        if not filas_seleccionadas:
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Atención", "Selecciona al menos un reporte de la tabla primero.", "warning", self).exec()
            return
            
        from vistas.utilidades import DialogoConfirmacion
        msg = f"¿Seguro que quieres borrar {len(filas_seleccionadas)} reporte(s) seleccionado(s)? Se eliminarán físicamente."
        dialogo = DialogoConfirmacion("Confirmar", msg, self)
        
        if dialogo.exec() and dialogo.resultado:
            try:
                conexion = sqlite3.connect("bd/database.db")
                cursor = conexion.cursor()
                
                for index in filas_seleccionadas:
                    row = index.row()
                    item_id = self.tabla_reportes.item(row, 0)
                    item_ruta = self.tabla_reportes.item(row, 7)
                    if not item_id:
                        continue
                    id_reporte = item_id.text()
                    ruta_archivo = item_ruta.text() if item_ruta else 'Sin archivo'
                    
                    # Borrado manual en cascada para mantener la integridad referencial en SQLite
                    cursor.execute("DELETE FROM Microglia WHERE id_analisis IN (SELECT id_analisis FROM Analisis WHERE id_reporte = ?)", (id_reporte,))
                    cursor.execute("DELETE FROM Analisis WHERE id_reporte = ?", (id_reporte,))
                    cursor.execute("DELETE FROM Reporte WHERE id_reporte = ?", (id_reporte,))
                    
                    try:
                        if ruta_archivo and ruta_archivo != 'Sin archivo' and os.path.exists(ruta_archivo):
                            os.remove(ruta_archivo)
                    except Exception as e:
                        print(f"No se pudo borrar el archivo físico: {e}")
                
                conexion.commit()
                conexion.close()
                
                from vistas.utilidades import DialogoNotificacion
                DialogoNotificacion("Listo", "Reporte(s) eliminado(s) de la BD.", "info", self).exec()
                self.cargar_reportes_bd()
            except Exception as e:
                from vistas.utilidades import DialogoNotificacion
                DialogoNotificacion("Error", f"Hubo un error al eliminar: {e}", "error", self).exec()

    def cerrar_sesion(self):
        from vistas.login import VentanaLogin
        self.ventana_login = VentanaLogin()
        self.ventana_login.setObjectName("ventana_login")
        self.ventana_login.show()
        self.close()