import os
import logging

os.environ["QT_QPA_PLATFORM"] = "xcb"
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QMessageBox, QFrame)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt
# Imports the external YOLO processing module
from ia.modelo_yolo import MicrogliaProcessor

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class VentanaInvestigador(QMainWindow):
    def __init__(self, id_usuario, rol):
        super().__init__()
        self.id_usuario = id_usuario
        self.rol = rol
        self.ruta_imagen_actual = None
        
        self.setWindowTitle(f"Prototipo Microglías - Panel ({self.rol})")
        self.resize(1100, 700)
        self.inicializar_ui()

    def inicializar_ui(self):
        widget_central = QWidget()
        layout_principal = QHBoxLayout()
        
        menu_lateral = QVBoxLayout()
        menu_lateral.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        label_bienvenida = QLabel(f"Sesión: {self.rol}")
        label_bienvenida.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 20px;")
        menu_lateral.addWidget(label_bienvenida)

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
        for btn in [self.btn_cargar, self.btn_historial, self.btn_conteo, self.btn_perimetros, self.btn_areas, self.btn_reporte, self.btn_guardar_img]:
            btn.setStyleSheet(estilo_btn_menu)
            menu_lateral.addWidget(btn)

        menu_lateral.addStretch()
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

        area_imagen = QVBoxLayout()
        self.visor_imagen = QLabel("Sube una imagen .tiff para empezar el análisis...")
        self.visor_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.visor_imagen.setStyleSheet("border: 2px dashed #aaa; background-color: #f0f0f0; font-size: 18px; color: #666;")
        
        area_imagen.addWidget(self.visor_imagen)

        layout_principal.addWidget(frame_menu)
        layout_principal.addLayout(area_imagen, stretch=1) 

        widget_central.setLayout(layout_principal)
        self.setCentralWidget(widget_central)

        self.btn_cargar.clicked.connect(self.cargar_imagen)
        self.btn_cerrar_sesion.clicked.connect(self.cerrar_sesion)
        
        # Connects the UI button to the YOLO processing logic
        self.btn_conteo.clicked.connect(self.execute_microglia_counting)
        
        self.alternar_botones_analisis(False)

        if self.rol == "Invitado":
            self.btn_historial.hide()
            self.btn_reporte.hide()
            self.btn_guardar_img.hide()

    def alternar_botones_analisis(self, estado):
        self.btn_conteo.setEnabled(estado)
        self.btn_perimetros.setEnabled(estado)
        self.btn_areas.setEnabled(estado)
        self.btn_reporte.setEnabled(estado)
        self.btn_guardar_img.setEnabled(estado)

    def cargar_imagen(self):
        ruta_archivo, _ = QFileDialog.getOpenFileName(
            self, 
            "Seleccionar imagen de Microglías", 
            "", 
            "Imágenes TIFF (*.tiff *.tif);;Todas las imágenes (*.png *.jpg *.jpeg)"
        )
        
        if ruta_archivo:
            self.ruta_imagen_actual = ruta_archivo
            pixmap = QPixmap(ruta_archivo)
            
            if pixmap.isNull():
                # Logs the error to identify unsupported formats by the default Qt parser
                logging.error(f"QPixmap failed to parse the image natively: {ruta_archivo}")
                
                try:
                    import cv2
                    import numpy as np
                    
                    # Reads the image array directly via OpenCV to bypass QPixmap limitations
                    cv_img = cv2.imread(ruta_archivo, cv2.IMREAD_UNCHANGED)
                    if cv_img is not None:
                        if cv_img.dtype == np.uint16:
                            cv_img = ((cv_img - cv_img.min()) / (cv_img.max() - cv_img.min()) * 255).astype(np.uint8)
                            
                        if len(cv_img.shape) == 2:
                            h, w = cv_img.shape
                            qimg = QImage(cv_img.data, w, h, w, QImage.Format.Format_Grayscale8)
                        else:
                            cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                            h, w, ch = cv_img.shape
                            qimg = QImage(cv_img.data, w, h, ch * w, QImage.Format.Format_RGB888)
                            
                        pixmap = QPixmap.fromImage(qimg)
                        logging.info("Image successfully loaded and converted via OpenCV.")
                except Exception as e:
                    logging.error(f"Alternative OpenCV loading method also failed: {e}")

            if not pixmap.isNull():
                self.visor_imagen.setPixmap(pixmap.scaled(self.visor_imagen.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.alternar_botones_analisis(True)
                QMessageBox.information(self, "Imagen cargada", "Imagen lista para meterle la IA.")
            else:
                QMessageBox.critical(self, "Error", "El archivo está corrupto o no es válido.")
    def cerrar_sesion(self):
        from vistas.login import VentanaLogin
        self.ventana_login = VentanaLogin()
        self.ventana_login.setObjectName("ventana_login")
        self.ventana_login.show()
        self.close()

    def execute_microglia_counting(self):
        # Executes the object detection model on the loaded image and displays the results
        if not self.ruta_imagen_actual:
            QMessageBox.warning(self, "Warning", "Please load an image first.")
            return

        try:
            model_weights_path = os.path.join(os.getcwd(), "ia", "entrenamiento_resultados", "modelo_microglias5", "weights", "best.pt")
            output_directory = os.path.join(os.getcwd(), "analisis_resultados")

            processor = MicrogliaProcessor(model_path=model_weights_path, confidence_threshold=0.45)
            
            crops_folder, detection_count = processor.process_and_crop(
                input_image_path=self.ruta_imagen_actual, 
                base_output_folder=output_directory
            )

            QMessageBox.information(
                self, 
                "Analysis Complete", 
                f"Successfully detected {detection_count} microglia cells.\n\nIndividual crops saved at:\n{crops_folder}"
            )

        except Exception as error:
            QMessageBox.critical(self, "Processing Error", f"An error occurred during AI analysis:\n{str(error)}")