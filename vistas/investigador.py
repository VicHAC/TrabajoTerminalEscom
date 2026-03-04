import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QMessageBox, QFrame)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

class VentanaInvestigador(QMainWindow):
    def __init__(self, id_usuario, rol):
        super().__init__()
        self.id_usuario = id_usuario
        self.rol = rol
        self.ruta_imagen_actual = None
        
        self.setWindowTitle(f"Prototipo Microglías - Panel ({self.rol})")
        self.resize(1100, 700) # Más grandecita para que quepa bien la imagen
        self.inicializar_ui()

    def inicializar_ui(self):
        # Widget y layout principal
        widget_central = QWidget()
        layout_principal = QHBoxLayout()
        
        # ==========================================
        # 1. MENÚ LATERAL (Sidebar)
        # ==========================================
        menu_lateral = QVBoxLayout()
        menu_lateral.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Etiqueta de usuario
        label_bienvenida = QLabel(f"Sesión: {self.rol}")
        label_bienvenida.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 20px;")
        menu_lateral.addWidget(label_bienvenida)

        # Botones basados en tu diagrama (Figura 8)
        self.btn_cargar = QPushButton("Cargar Imagen")
        self.btn_historial = QPushButton("Historial")
        
        label_caract = QLabel("Caracterización:")
        label_caract.setStyleSheet("font-weight: bold; margin-top: 15px;")
        
        self.btn_conteo = QPushButton("Aplicar Conteo")
        self.btn_perimetros = QPushButton("Calcular Perímetros")
        self.btn_areas = QPushButton("Calcular Áreas")
        
        label_reporte = QLabel("Reportes:")
        label_reporte.setStyleSheet("font-weight: bold; margin-top: 15px;")
        
        self.btn_reporte = QPushButton("Generar Reporte")
        self.btn_guardar_img = QPushButton("Guardar Imagen")
        self.btn_cerrar_sesion = QPushButton("Cerrar Sesión")
        self.btn_cerrar_sesion.setStyleSheet("background-color: #8b0000; color: white; margin-top: 30px;")

        # Estilo genérico para los botones del menú para que no se vean tan x
        estilo_btn = "padding: 8px; text-align: left;"
        for btn in [self.btn_cargar, self.btn_historial, self.btn_conteo, self.btn_perimetros, self.btn_areas, self.btn_reporte, self.btn_guardar_img]:
            btn.setStyleSheet(estilo_btn)

        # Agregar todo al sidebar
        menu_lateral.addWidget(self.btn_cargar)
        menu_lateral.addWidget(self.btn_historial)
        menu_lateral.addWidget(label_caract)
        menu_lateral.addWidget(self.btn_conteo)
        menu_lateral.addWidget(self.btn_perimetros)
        menu_lateral.addWidget(self.btn_areas)
        menu_lateral.addWidget(label_reporte)
        menu_lateral.addWidget(self.btn_reporte)
        menu_lateral.addWidget(self.btn_guardar_img)
        menu_lateral.addWidget(self.btn_cerrar_sesion)

        # Contenedor visual para el menú (una línea separadora a la derecha)
        frame_menu = QFrame()
        frame_menu.setFixedWidth(200)
        frame_menu.setLayout(menu_lateral)
        frame_menu.setStyleSheet("border-right: 1px solid #ccc;")

        # ==========================================
        # 2. ÁREA DE LA IMAGEN (Main Content)
        # ==========================================
        area_imagen = QVBoxLayout()
        self.visor_imagen = QLabel("Sube una imagen .tiff para empezar el análisis...")
        self.visor_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.visor_imagen.setStyleSheet("border: 2px dashed #aaa; background-color: #f0f0f0; font-size: 18px; color: #666;")
        
        area_imagen.addWidget(self.visor_imagen)

        # Juntar el menú y el área de la imagen
        layout_principal.addWidget(frame_menu)
        layout_principal.addLayout(area_imagen, stretch=1) # El stretch=1 hace que la imagen ocupe todo el espacio sobrante

        widget_central.setLayout(layout_principal)
        self.setCentralWidget(widget_central)

        # Conectar botones a sus funciones
        self.btn_cargar.clicked.connect(self.cargar_imagen)
        self.btn_cerrar_sesion.clicked.connect(self.cerrar_sesion)
        
        # Desactivar botones de análisis hasta que no haya imagen
        self.alternar_botones_analisis(False)

    def alternar_botones_analisis(self, estado):
        """Activa o desactiva los botones dependiendo si hay imagen cargada."""
        self.btn_conteo.setEnabled(estado)
        self.btn_perimetros.setEnabled(estado)
        self.btn_areas.setEnabled(estado)
        self.btn_reporte.setEnabled(estado)
        self.btn_guardar_img.setEnabled(estado)

    def cargar_imagen(self):
        """Abre el explorador de archivos para buscar el TIFF."""
        ruta_archivo, _ = QFileDialog.getOpenFileName(
            self, 
            "Seleccionar imagen de Microglías", 
            "", 
            "Imágenes TIFF (*.tiff *.tif);;Todas las imágenes (*.png *.jpg *.jpeg)"
        )
        
        if ruta_archivo:
            self.ruta_imagen_actual = ruta_archivo
            
            # Cargar y mostrar la imagen en el QLabel
            pixmap = QPixmap(ruta_archivo)
            if not pixmap.isNull():
                # Escalar la imagen para que quepa en la ventana sin deformarse
                self.visor_imagen.setPixmap(pixmap.scaled(self.visor_imagen.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.alternar_botones_analisis(True)
                QMessageBox.information(self, "Imagen cargada", "Imagen lista para meterle la IA.")
            else:
                QMessageBox.critical(self, "Error", "El archivo está corrupto o no es una imagen válida.")

    def cerrar_sesion(self):
        self.close()
        # Aquí la señal regresaría a abrir el login, pero por ahora solo cerramos.