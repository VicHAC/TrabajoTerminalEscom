import logging
import os
import subprocess
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "xcb"
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Imports the external YOLO processing module (Deferred to execute_microglia_counting)

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


class DialogoCarga(QDialog):
    """
    Diálogo flotante estilizado para mostrar progreso
    sin bloquear la UI pero impidiendo clics adicionales.
    """
    def __init__(self, mensaje="Procesando...", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        frame = QFrame(self)
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 2px solid #003366;
            }
            QLabel {
                color: #003366;
                font-size: 16px;
                font-weight: bold;
                padding: 20px;
            }
        """)
        
        flayout = QVBoxLayout(frame)
        label = QLabel(mensaje)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        flayout.addWidget(label)
        
        layout.addWidget(frame)
        self.setLayout(layout)


class DialogoVistaCelular(QDialog):
    """
    Ventana emergente interna (dentro de la app) para visualizar
    el recorte en alta resolución de una célula específica.
    """

    def __init__(self, crop_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vista Detallada de la Célula")
        self.resize(400, 400)

        layout = QVBoxLayout()
        label_imagen = QLabel()
        label_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pixmap = QPixmap(crop_path)
        if not pixmap.isNull():
            label_imagen.setPixmap(
                pixmap.scaled(
                    380,
                    380,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            label_imagen.setText("No se pudo cargar la imagen recortada.")

        layout.addWidget(label_imagen)
        self.setLayout(layout)


class InteractiveImageViewer(QLabel):
    """
    A custom QLabel that tracks mouse movement to highlight YOLO
    bounding boxes and open cropped images upon clicking within the app.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.original_pixmap = None
        self._current_pixmap = None
        self.boxes = []
        self.hovered_index = -1
        self.view_mode = "Original"

    def set_image_and_boxes(self, pixmap, bounding_boxes):
        self.original_pixmap = pixmap
        self.boxes = bounding_boxes
        self.hovered_index = -1
        self.draw_current_state()

    def set_view_mode(self, mode, new_pixmap):
        self.view_mode = mode
        self.original_pixmap = new_pixmap
        self.draw_current_state()

    def map_mouse_to_original(self, mouse_pos):
        if not self.original_pixmap or self.original_pixmap.isNull():
            return None

        lbl_w, lbl_h = self.width(), self.height()
        pix_w, pix_h = self.original_pixmap.width(), self.original_pixmap.height()

        scaled_pix = self.original_pixmap.scaled(
            lbl_w, lbl_h, Qt.AspectRatioMode.KeepAspectRatio
        )
        sw, sh = scaled_pix.width(), scaled_pix.height()

        dx = (lbl_w - sw) / 2
        dy = (lbl_h - sh) / 2
        mx, my = mouse_pos.x(), mouse_pos.y()

        if dx <= mx <= dx + sw and dy <= my <= dy + sh:
            orig_x = (mx - dx) * (pix_w / sw)
            orig_y = (my - dy) * (pix_h / sh)
            return orig_x, orig_y

        return None

    def mouseMoveEvent(self, event):
        if not self.original_pixmap or not self.boxes:
            return

        orig_coords = self.map_mouse_to_original(event.pos())
        new_hovered_index = -1

        if orig_coords:
            ox, oy = orig_coords
            for i, box in enumerate(self.boxes):
                if (
                    box["x"] <= ox <= box["x"] + box["w"]
                    and box["y"] <= oy <= box["y"] + box["h"]
                ):
                    new_hovered_index = i
                    break

        if new_hovered_index != self.hovered_index:
            self.hovered_index = new_hovered_index
            self.draw_current_state()

    def mousePressEvent(self, event):
        if self.hovered_index != -1 and event.button() == Qt.MouseButton.LeftButton:
            crop_path = self.boxes[self.hovered_index]["crop_path"]

            # Enrutamiento dinámico de carpetas
            if self.view_mode == "Filtrada":
                crop_path = crop_path.replace("/crops/", "/filtradas/").replace(
                    "\\crops\\", "\\filtradas\\"
                )
            elif self.view_mode == "Esqueleto":
                crop_path = crop_path.replace("/crops/", "/esqueletos/").replace(
                    "\\crops\\", "\\esqueletos\\"
                )

            if os.path.exists(crop_path):
                dialogo = DialogoVistaCelular(crop_path, self.window())
                dialogo.exec()
            else:
                QMessageBox.warning(
                    self, "Error", f"Aún no se ha procesado esta imagen:\n{crop_path}"
                )

    def draw_current_state(self):
        if not self.original_pixmap:
            return

        temp_pixmap = self.original_pixmap.copy()
        painter = QPainter(temp_pixmap)

        if self.hovered_index == -1:
            # ESTADO NORMAL
            pen = QPen(QColor(0, 255, 0, 120))
            pen.setWidth(max(1, int(temp_pixmap.width() * 0.0015)))
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            for box in self.boxes:
                rect = QRect(box["x"], box["y"], box["w"], box["h"])
                painter.drawRect(rect)

            painter.end()
        else:
            # ESTADO HOVER (Oscurecer fondo)
            painter.fillRect(temp_pixmap.rect(), QColor(0, 0, 0, 180))

            box = self.boxes[self.hovered_index]
            rect = QRect(box["x"], box["y"], box["w"], box["h"])
            cell_snippet = self.original_pixmap.copy(rect)
            painter.drawPixmap(rect.topLeft(), cell_snippet)

            pen = QPen(QColor(0, 255, 0))
            pen.setWidth(max(2, int(temp_pixmap.width() * 0.003)))
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

        painter.end()
        self._current_pixmap = temp_pixmap
        self.update()

    def paintEvent(self, event):
        if self._current_pixmap and not self._current_pixmap.isNull():
            painter = QPainter(self)
            scaled_pix = self._current_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled_pix.width()) // 2
            y = (self.height() - scaled_pix.height()) // 2
            painter.drawPixmap(x, y, scaled_pix)
            painter.end()
        else:
            super().paintEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.original_pixmap:
            self.update()


class VentanaInvestigador(QMainWindow):
    def __init__(self, id_usuario, rol):
        super().__init__()
        self.id_usuario = id_usuario
        self.rol = rol
        self.ruta_imagen_actual = None

        # Almacenamiento en memoria para el cambio rápido de vistas
        self.pixmaps_globales = {"Original": None, "Filtrada": None, "Esqueleto": None}

        self.setWindowTitle(f"Prototipo Microglías - Panel ({self.rol})")
        self.resize(1100, 700)
        self.inicializar_ui()

    def inicializar_ui(self):
        widget_central = QWidget()
        layout_principal = QHBoxLayout()

        menu_lateral = QVBoxLayout()
        menu_lateral.setAlignment(Qt.AlignmentFlag.AlignTop)

        label_bienvenida = QLabel(f"Sesión: {self.rol}")
        label_bienvenida.setStyleSheet(
            "font-weight: bold; font-size: 16px; margin-bottom: 20px;"
        )
        menu_lateral.addWidget(label_bienvenida)

        self.btn_cargar = QPushButton("Cargar Imagen")
        self.btn_historial = QPushButton("Historial")

        label_caract = QLabel("Caracterización:")
        label_caract.setStyleSheet("font-weight: bold; margin-top: 15px;")

        self.btn_conteo = QPushButton("1. Aplicar Conteo")
        self.btn_filtrar = QPushButton("2. Aplicar Filtrado")
        self.btn_ramas = QPushButton("3. Mostrar Ramas (Esqueleto)")

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
        for btn in [
            self.btn_cargar,
            self.btn_historial,
            self.btn_conteo,
            self.btn_filtrar,
            self.btn_ramas,
            self.btn_reporte,
            self.btn_guardar_img,
        ]:
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

        # --- SELECTOR DE CAPAS ---
        self.combo_vista = QComboBox()
        self.combo_vista.addItems(["Original", "Filtrada", "Esqueleto"])
        self.combo_vista.setStyleSheet(
            "padding: 5px; font-size: 14px; font-weight: bold;"
        )
        self.combo_vista.setEnabled(False)
        self.combo_vista.currentTextChanged.connect(self.cambiar_vista_global)

        self.visor_imagen = InteractiveImageViewer()
        self.visor_imagen.setText("Sube una imagen .tiff para empezar el análisis...")
        self.visor_imagen.setStyleSheet(
            "border: 2px dashed #aaa; background-color: #f0f0f0; font-size: 18px; color: #666;"
        )

        area_imagen.addWidget(self.combo_vista)
        area_imagen.addWidget(self.visor_imagen, stretch=1)

        layout_principal.addWidget(frame_menu)
        layout_principal.addLayout(area_imagen, stretch=1)

        widget_central.setLayout(layout_principal)
        self.setCentralWidget(widget_central)

        # Conexiones
        self.btn_cargar.clicked.connect(self.cargar_imagen)
        self.btn_cerrar_sesion.clicked.connect(self.cerrar_sesion)

        self.btn_conteo.clicked.connect(self.execute_microglia_counting)
        self.btn_filtrar.clicked.connect(self.ejecutar_filtrado)
        self.btn_ramas.clicked.connect(self.mostrar_ramas_morfologia)

        self.alternar_botones_analisis(False)

        if self.rol == "Invitado":
            self.btn_historial.hide()
            self.btn_reporte.hide()
            self.btn_guardar_img.hide()

    def alternar_botones_analisis(self, estado):
        self.btn_conteo.setEnabled(estado)
        self.btn_filtrar.setEnabled(estado)
        self.btn_ramas.setEnabled(estado)
        self.btn_reporte.setEnabled(estado)
        self.btn_guardar_img.setEnabled(estado)

    def cargar_imagen(self):
        ruta_archivo, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar imagen de Microglías",
            "",
            "Imágenes TIFF (*.tiff *.tif);;Todas las imágenes (*.png *.jpg *.jpeg)",
        )

        if ruta_archivo:
            self.ruta_imagen_actual = ruta_archivo
            pixmap = QPixmap(ruta_archivo)

            if pixmap.isNull():
                try:
                    import cv2
                    import numpy as np

                    cv_img = cv2.imread(ruta_archivo, cv2.IMREAD_UNCHANGED)
                    if cv_img is not None:
                        if cv_img.dtype == np.uint16:
                            cv_img = (
                                (cv_img - cv_img.min())
                                / (cv_img.max() - cv_img.min())
                                * 255
                            ).astype(np.uint8)

                        if len(cv_img.shape) == 2:
                            h, w = cv_img.shape
                            qimg = QImage(
                                cv_img.data, w, h, w, QImage.Format.Format_Grayscale8
                            )
                        else:
                            cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                            h, w, ch = cv_img.shape
                            qimg = QImage(
                                cv_img.data, w, h, ch * w, QImage.Format.Format_RGB888
                            )

                        pixmap = QPixmap.fromImage(qimg)
                except Exception as e:
                    logging.error(f"Error al cargar imagen: {e}")

            if not pixmap.isNull():
                self.pixmaps_globales["Original"] = pixmap
                self.visor_imagen.set_image_and_boxes(pixmap, [])
                self.alternar_botones_analisis(True)

                # Reiniciar UI
                self.combo_vista.setEnabled(False)
                self.combo_vista.blockSignals(True)
                self.combo_vista.setCurrentText("Original")
                self.combo_vista.blockSignals(False)
                self.visor_imagen.view_mode = "Original"

                QMessageBox.information(
                    self, "Imagen cargada", "Imagen lista para el análisis."
                )
            else:
                QMessageBox.critical(
                    self, "Error", "El archivo está corrupto o no es válido."
                )

    def cambiar_vista_global(self, texto_vista):
        pixmap_guardado = self.pixmaps_globales.get(texto_vista)

        if pixmap_guardado:
            self.visor_imagen.set_view_mode(texto_vista, pixmap_guardado)
        else:
            QMessageBox.warning(
                self, "Aviso", f"Aún no has generado el paso: {texto_vista}."
            )
            self.combo_vista.blockSignals(True)
            self.combo_vista.setCurrentText(self.visor_imagen.view_mode)
            self.combo_vista.blockSignals(False)

    def cerrar_sesion(self):
        from vistas.login import VentanaLogin

        self.ventana_login = VentanaLogin()
        self.ventana_login.setObjectName("ventana_login")
        self.ventana_login.show()
        self.close()

    def execute_microglia_counting(self):
        if not self.ruta_imagen_actual:
            QMessageBox.warning(
                self, "Advertencia", "Por favor, carga una imagen primero."
            )
            return

        dialogo = DialogoCarga("Cargando IA y aplicando conteo...\nPor favor, espera.", self)
        dialogo.show()
        from PyQt6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()

        try:
            from ia.modelo_yolo import MicrogliaProcessor

            model_path = os.path.join(
                os.getcwd(),
                "ia",
                "entrenamiento_resultados",
                "modelo_microglias5",
                "weights",
                "best.pt",
            )
            output_dir = os.path.join(os.getcwd(), "analisis_resultados")

            processor = MicrogliaProcessor(model_path=model_path)
            resultado = processor.process_and_crop(
                input_image_path=self.ruta_imagen_actual,
                base_output_folder=output_dir,
            )

            if len(resultado) == 3:
                crops_folder, count, boxes_data = resultado
                self.visor_imagen.set_image_and_boxes(
                    self.pixmaps_globales["Original"], boxes_data
                )
                self.combo_vista.setEnabled(True)
            else:
                crops_folder, count = resultado
                self.visor_imagen.set_image_and_boxes(
                    self.pixmaps_globales["Original"], []
                )

            QMessageBox.information(
                self,
                "1. Conteo completado",
                f"Se detectaron {count} microglías.\n\n¡Puedes visualizar los recortes haciendo clic en los cuadros verdes!",
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            dialogo.close()
            QApplication.restoreOverrideCursor()

    def construir_imagen_global(self, carpeta_origen):
        """
        Pega matemáticamente los recortes procesados sobre un fondo negro.
        ESTA VEZ, ESTÁ BLINDADO PARA QUE NO CIERRE (CRASHEE) LA APLICACIÓN.
        """
        import cv2
        import numpy as np

        orig_pixmap = self.pixmaps_globales["Original"]
        orig_w = orig_pixmap.width()
        orig_h = orig_pixmap.height()

        lienzo = np.zeros((orig_h, orig_w), dtype=np.uint8)

        base_name = Path(self.ruta_imagen_actual).stem
        base_dir = os.path.join(os.getcwd(), "analisis_resultados", base_name)

        for box in self.visor_imagen.boxes:
            x, y, w, h = int(box["x"]), int(box["y"]), int(box["w"]), int(box["h"])
            nombre_archivo = os.path.basename(box["crop_path"])
            ruta_recorte = os.path.join(base_dir, carpeta_origen, nombre_archivo)

            if os.path.exists(ruta_recorte):
                # Lectura blindada para paths con acentos en Linux/Windows
                with open(ruta_recorte, "rb") as f:
                    file_bytes = bytearray(f.read())
                img_array = np.asarray(file_bytes, dtype=np.uint8)
                recorte = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)

                if recorte is not None:
                    rh, rw = recorte.shape
                    y_fin = min(y + rh, orig_h)
                    x_fin = min(x + rw, orig_w)
                    h_real = y_fin - y
                    w_real = x_fin - x

                    lienzo[y:y_fin, x:x_fin] = recorte[:h_real, :w_real]

        # IMPORTANTE: .copy() evita que la memoria sea eliminada (Segmentation Fault)
        qimg = QImage(
            lienzo.data, orig_w, orig_h, orig_w, QImage.Format.Format_Grayscale8
        ).copy()
        return QPixmap.fromImage(qimg)

    def ejecutar_filtrado(self):
        if not self.ruta_imagen_actual or not self.visor_imagen.boxes:
            QMessageBox.warning(self, "Advertencia", "Aplica el conteo primero.")
            return

        base_name = Path(self.ruta_imagen_actual).stem
        filtradas_dir = os.path.join(
            os.getcwd(), "analisis_resultados", base_name, "filtradas"
        )
        os.makedirs(filtradas_dir, exist_ok=True)

        import cv2
        import numpy as np

        count = 0
        try:
            dialogo = DialogoCarga("Aplicando filtrado a las células...\nPor favor, espera.", self)
            dialogo.show()
            from PyQt6.QtWidgets import QApplication
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents()

            for box in self.visor_imagen.boxes:
                crop_path = box["crop_path"]
                if os.path.exists(crop_path):
                    # Lectura segura con NumPy
                    with open(crop_path, "rb") as f:
                        file_bytes = bytearray(f.read())
                    img_array = np.asarray(file_bytes, dtype=np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)

                    if img is not None:
                        blur = cv2.GaussianBlur(img, (5, 5), 0)
                        _, bin_img = cv2.threshold(
                            blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                        )

                        nombre = os.path.basename(crop_path)
                        out_path = os.path.join(filtradas_dir, nombre)

                        # Escritura segura con NumPy
                        is_success, im_buf_arr = cv2.imencode(".png", bin_img)
                        if is_success:
                            im_buf_arr.tofile(out_path)
                            count += 1

            if count > 0:
                pixmap_filtrada = self.construir_imagen_global("filtradas")
                self.pixmaps_globales["Filtrada"] = pixmap_filtrada
                self.combo_vista.setCurrentText("Filtrada")
                QMessageBox.information(
                    self, "2. Filtrado", f"Se binarizaron {count} microglías."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "No se pudo procesar ninguna imagen. Las cajas de YOLO están vacías.",
                )
        except Exception as error:
            QMessageBox.critical(self, "Error", f"Falló el filtrado: {str(error)}")
        finally:
            dialogo.close()
            QApplication.restoreOverrideCursor()

    def mostrar_ramas_morfologia(self):
        if not self.ruta_imagen_actual or not self.visor_imagen.boxes:
            QMessageBox.warning(
                self, "Advertencia", "Aplica el conteo y filtrado primero."
            )
            return

        base_name = Path(self.ruta_imagen_actual).stem
        filtradas_dir = os.path.join(
            os.getcwd(), "analisis_resultados", base_name, "filtradas"
        )
        esqueletos_dir = os.path.join(
            os.getcwd(), "analisis_resultados", base_name, "esqueletos"
        )
        os.makedirs(esqueletos_dir, exist_ok=True)

        import cv2
        import numpy as np
        from skimage.morphology import skeletonize

        count = 0
        try:
            dialogo = DialogoCarga("Calculando morfología y ramas...\nPor favor, espera.", self)
            dialogo.show()
            from PyQt6.QtWidgets import QApplication
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents()
            for box in self.visor_imagen.boxes:
                nombre = os.path.basename(box["crop_path"])
                fil_path = os.path.join(filtradas_dir, nombre)

                if os.path.exists(fil_path):
                    with open(fil_path, "rb") as f:
                        file_bytes = bytearray(f.read())
                    img_array = np.asarray(file_bytes, dtype=np.uint8)
                    img_raw = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)

                    if img_raw is not None:
                        img_bool = img_raw > 0
                        skeleton = skeletonize(img_bool)
                        skeleton_img = (skeleton * 255).astype(np.uint8)

                        out_path = os.path.join(esqueletos_dir, nombre)
                        is_success, im_buf_arr = cv2.imencode(".png", skeleton_img)
                        if is_success:
                            im_buf_arr.tofile(out_path)
                            count += 1

            if count > 0:
                pixmap_esqueleto = self.construir_imagen_global("esqueletos")
                self.pixmaps_globales["Esqueleto"] = pixmap_esqueleto
                self.combo_vista.setCurrentText("Esqueleto")
                QMessageBox.information(
                    self,
                    "3. Ramas Generadas",
                    f"Se generaron {count} esqueletos topológicos.",
                )
            else:
                QMessageBox.warning(
                    self,
                    "Advertencia",
                    "No se generaron esqueletos. Verifica la carpeta de filtrado.",
                )
        except Exception as error:
            QMessageBox.critical(
                self, "Error de Procesamiento", f"Falló el cálculo:\n{str(error)}"
            )
        finally:
            dialogo.close()
            QApplication.restoreOverrideCursor()
