import logging
import os
import subprocess
import uuid
from pathlib import Path

from PyQt6.QtCore import pyqtSignal, QRect, Qt, QSize
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QIcon
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
    QSlider,
    QCheckBox,
)

os.environ["QT_QPA_PLATFORM"] = "xcb"

# Import de tu analizador morfológico
from ia.morphology_analyzer import MorphologyAnalyzer

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

class DialogoCarga(QDialog):
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

class DialogoConfirmacion(QDialog):
    def __init__(self, titulo, mensaje, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        self.resultado = False

        layout = QVBoxLayout(self)
        frame = QFrame(self)
        frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 2px solid #cc0000;
            }
            QLabel {
                color: #333333;
                font-size: 15px;
                padding: 10px;
            }
            QPushButton {
                border-radius: 6px;
                font-weight: bold;
                padding: 8px 15px;
                font-size: 14px;
            }
            QPushButton#btn_eliminar {
                background-color: #cc0000;
                color: white;
            }
            QPushButton#btn_eliminar:hover {
                background-color: #aa0000;
            }
            QPushButton#btn_mantener {
                background-color: #e0e0e0;
                color: #333333;
            }
            QPushButton#btn_mantener:hover {
                background-color: #cccccc;
            }
        """)

        flayout = QVBoxLayout(frame)
        lbl_titulo = QLabel(f"<b>{titulo}</b>")
        lbl_titulo.setStyleSheet("color: #cc0000; font-size: 18px; border: none;")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_mensaje = QLabel(mensaje)
        lbl_mensaje.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_mensaje.setWordWrap(True)
        lbl_mensaje.setStyleSheet("border: none;")

        btn_layout = QHBoxLayout()
        btn_mantener = QPushButton("Mantener")
        btn_mantener.setObjectName("btn_mantener")
        btn_mantener.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_mantener.clicked.connect(self.cancelar)

        btn_eliminar = QPushButton("Eliminar")
        btn_eliminar.setObjectName("btn_eliminar")
        btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eliminar.clicked.connect(self.aceptar)

        btn_layout.addWidget(btn_mantener)
        btn_layout.addWidget(btn_eliminar)

        flayout.addWidget(lbl_titulo)
        flayout.addWidget(lbl_mensaje)
        flayout.addLayout(btn_layout)

        layout.addWidget(frame)
        self.setLayout(layout)

    def aceptar(self):
        self.resultado = True
        self.accept()

    def cancelar(self):
        self.resultado = False
        self.reject()

class InteractiveImageViewer(QLabel):
    conteo_actualizado = pyqtSignal(int)
    nueva_caja_dibujada = pyqtSignal(int, int, int, int)
    nivel_zoom_cambiado = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_pixmap = None
        self._current_pixmap = None
        self.boxes = []
        self.hovered_index = -1
        self.view_mode = "Original"

        # Herramientas: "pointer", "draw", "delete"
        self.current_tool = "pointer" 
        
        self.is_drawing = False
        self.draw_start_pos = None
        self.draw_current_pos = None
        
        # Panning (movimiento)
        self.is_panning = False
        self.pan_start_pos = None
        self.pan_x = 0
        self.pan_y = 0
        
        self.zoom_level = 100
        self.zoom_locked = False

    def set_image_and_boxes(self, pixmap, bounding_boxes):
        self.original_pixmap = pixmap
        self.boxes = bounding_boxes
        self.hovered_index = -1
        self.pan_x = 0
        self.pan_y = 0
        self.draw_current_state()
        self.conteo_actualizado.emit(len(self.boxes))

    def set_view_mode(self, mode, new_pixmap):
        self.view_mode = mode
        self.original_pixmap = new_pixmap
        self.draw_current_state()

    def map_mouse_to_original(self, mouse_pos):
        if not self.original_pixmap or self.original_pixmap.isNull():
            return None
        
        pix_w, pix_h = self.original_pixmap.width(), self.original_pixmap.height()
        zoom_factor = self.zoom_level / 100.0
        
        scaled_w = int(pix_w * zoom_factor)
        scaled_h = int(pix_h * zoom_factor)
        
        draw_x = (self.width() - scaled_w) // 2 + self.pan_x
        draw_y = (self.height() - scaled_h) // 2 + self.pan_y
        
        mx, my = mouse_pos.x(), mouse_pos.y()
        
        if draw_x <= mx <= draw_x + scaled_w and draw_y <= my <= draw_y + scaled_h:
            orig_x = (mx - draw_x) / zoom_factor
            orig_y = (my - draw_y) / zoom_factor
            return orig_x, orig_y
        return None

    def mousePressEvent(self, event):
        if not self.original_pixmap:
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if self.current_tool == "pointer":
                if self.hovered_index != -1:
                    # VER DETALLE CÉLULA
                    crop_path = self.boxes[self.hovered_index]["crop_path"]
                    if self.view_mode == "Filtrada":
                        crop_path = crop_path.replace("/crops/", "/filtradas/").replace("\\crops\\", "\\filtradas\\")
                    elif self.view_mode == "Esqueleto":
                        crop_path = crop_path.replace("/crops/", "/esqueletos/").replace("\\crops\\", "\\esqueletos\\")
                    if os.path.exists(crop_path):
                        dialogo = DialogoVistaCelular(crop_path, self.window())
                        dialogo.exec()
                else:
                    # NAVEGAR/MOVERSE EN LA IMAGEN
                    self.is_panning = True
                    self.pan_start_pos = event.pos()
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)

            elif self.current_tool == "draw":
                # INICIAR DIBUJO
                self.is_drawing = True
                self.draw_start_pos = event.pos()
                self.draw_current_pos = event.pos()

            elif self.current_tool == "delete":
                # ELIMINAR CÉLULA
                if self.hovered_index != -1:
                    dialogo = DialogoConfirmacion("Eliminar Detección", "¿Estás seguro de descartar esta célula del análisis?")
                    dialogo.exec()
                    if dialogo.resultado:
                        self.boxes.pop(self.hovered_index)
                        self.hovered_index = -1
                        self.draw_current_state()
                        self.conteo_actualizado.emit(len(self.boxes))

    def mouseMoveEvent(self, event):
        if not self.original_pixmap:
            return

        if self.is_panning:
            delta = event.pos() - self.pan_start_pos
            self.pan_x += delta.x()
            self.pan_y += delta.y()
            self.pan_start_pos = event.pos()
            self.update() 
            return

        if self.is_drawing:
            self.draw_current_pos = event.pos()
            self.draw_current_state()
            return

        if not self.boxes:
            return

        orig_coords = self.map_mouse_to_original(event.pos())
        new_hovered_index = -1
        if orig_coords:
            ox, oy = orig_coords
            for i, box in enumerate(self.boxes):
                if box["x"] <= ox <= box["x"] + box["w"] and box["y"] <= oy <= box["y"] + box["h"]:
                    new_hovered_index = i
                    break
        
        if new_hovered_index != self.hovered_index:
            self.hovered_index = new_hovered_index
            self.draw_current_state()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_panning:
                self.is_panning = False
                self.setCursor(Qt.CursorShape.ArrowCursor)
                
            elif self.is_drawing:
                self.is_drawing = False
                orig_start = self.map_mouse_to_original(self.draw_start_pos)
                orig_end = self.map_mouse_to_original(self.draw_current_pos)
                if orig_start and orig_end:
                    x1, y1 = orig_start
                    x2, y2 = orig_end
                    x = min(x1, x2)
                    y = min(y1, y2)
                    w = abs(x2 - x1)
                    h = abs(y2 - y1)
                    if w > 15 and h > 15:
                        self.nueva_caja_dibujada.emit(int(x), int(y), int(w), int(h))
                
                self.draw_start_pos = None
                self.draw_current_pos = None
                self.draw_current_state()

    def set_zoom(self, value):
        if not self.original_pixmap or self.original_pixmap.isNull():
            return
        if not self.zoom_locked:
            self.zoom_level = value
            self.draw_current_state()
            self.nivel_zoom_cambiado.emit(value)

    def lock_zoom(self, locked):
        self.zoom_locked = locked

    def draw_current_state(self):
        if not self.original_pixmap:
            return
            
        pix_w, pix_h = self.original_pixmap.width(), self.original_pixmap.height()
        zoom_factor = self.zoom_level / 100.0
        
        scaled_pix = self.original_pixmap.scaled(
            int(pix_w * zoom_factor),
            int(pix_h * zoom_factor),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        temp_pixmap = scaled_pix.copy()
        painter = QPainter(temp_pixmap)

        if self.hovered_index == -1:
            pen = QPen(QColor(0, 255, 0, 120))
            pen.setWidth(max(1, int(pix_w * 0.0015 * zoom_factor)))
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for box in self.boxes:
                rect = QRect(int(box["x"] * zoom_factor), int(box["y"] * zoom_factor), int(box["w"] * zoom_factor), int(box["h"] * zoom_factor))
                painter.drawRect(rect)
        else:
            painter.fillRect(temp_pixmap.rect(), QColor(0, 0, 0, 180))
            box = self.boxes[self.hovered_index]
            rect = QRect(int(box["x"] * zoom_factor), int(box["y"] * zoom_factor), int(box["w"] * zoom_factor), int(box["h"] * zoom_factor))
            cell_snippet = scaled_pix.copy(rect)
            painter.drawPixmap(rect.topLeft(), cell_snippet)
            
            pen = QPen(QColor(0, 255, 0)) 
            pen.setWidth(max(2, int(pix_w * 0.003 * zoom_factor)))
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

        if self.is_drawing and self.draw_start_pos and self.draw_current_pos:
            orig_start = self.map_mouse_to_original(self.draw_start_pos)
            orig_end = self.map_mouse_to_original(self.draw_current_pos)
            if orig_start and orig_end:
                ox1, oy1 = orig_start
                ox2, oy2 = orig_end
                rx = min(ox1, ox2)
                ry = min(oy1, oy2)
                rw = abs(ox2 - ox1)
                rh = abs(oy2 - oy1)
                pen_draw = QPen(QColor(0, 150, 255))
                pen_draw.setWidth(max(2, int(pix_w * 0.003 * zoom_factor)))
                painter.setPen(pen_draw)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(int(rx * zoom_factor), int(ry * zoom_factor), int(rw * zoom_factor), int(rh * zoom_factor))

        painter.end()
        self._current_pixmap = temp_pixmap
        self.update()

    def paintEvent(self, event):
        if self._current_pixmap and not self._current_pixmap.isNull():
            painter = QPainter(self)
            x = (self.width() - self._current_pixmap.width()) // 2 + self.pan_x
            y = (self.height() - self._current_pixmap.height()) // 2 + self.pan_y
            painter.drawPixmap(x, y, self._current_pixmap)
            painter.end()
        else:
            super().paintEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.original_pixmap:
            self.draw_current_state()

class VentanaInvestigador(QMainWindow):
    def __init__(self, id_usuario, rol):
        super().__init__()
        self.id_usuario = id_usuario
        self.rol = rol
        self.ruta_imagen_actual = None
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
        label_bienvenida.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 20px;")
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
            QPushButton { background-color: transparent; text-align: left; padding: 10px; font-weight: normal; color: #333333; border: none;}
            QPushButton:hover { background-color: #F0F0F0; border-radius: 5px; }
            QPushButton:disabled { color: #aaaaaa; }
        """
        for btn in [self.btn_cargar, self.btn_historial, self.btn_conteo, self.btn_filtrar, self.btn_ramas, self.btn_reporte, self.btn_guardar_img]:
            btn.setStyleSheet(estilo_btn_menu)
            menu_lateral.addWidget(btn)
            
        menu_lateral.addStretch()
        self.btn_cerrar_sesion = QPushButton("Cerrar Sesión")
        self.btn_cerrar_sesion.setStyleSheet("""
            QPushButton { background-color: transparent; border: 2px solid #cc0000; color: #cc0000; font-weight: bold; border-radius: 8px; padding: 10px; margin-top: 20px; }
            QPushButton:hover { background-color: #cc0000; color: white; }
        """)
        menu_lateral.addWidget(self.btn_cerrar_sesion)
        frame_menu = QFrame()
        frame_menu.setObjectName("menu_lateral")
        frame_menu.setFixedWidth(200)
        frame_menu.setLayout(menu_lateral)
        
        area_imagen = QVBoxLayout()
        controles_superiores = QHBoxLayout()
        
        # --- COMBO BOX (UX) ---
        self.combo_vista = QComboBox()
        self.combo_vista.addItems(["Original", "Filtrada", "Esqueleto"])
        self.combo_vista.setStyleSheet("""
    QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; padding: 4px 10px; font-weight: bold; color:#007bff;}
    QPushButton:hover { background-color: #e0e0e0; }
    QPushButton:disabled { color:#aaa; }
""")
        self.combo_vista.setEnabled(False)
        self.combo_vista.currentTextChanged.connect(self.cambiar_vista_global)

        controles_superiores.addWidget(self.combo_vista)
        controles_superiores.addStretch()
        
        # --- CONTADOR ---
        self.lbl_info_conteo = QLabel("Microglías detectadas: 0")
        self.lbl_info_conteo.setStyleSheet("font-size: 15px; font-weight: bold; color: #003366;")
        self.lbl_info_conteo.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        controles_superiores.addWidget(self.lbl_info_conteo)
        controles_superiores.addSpacing(15)

        # --- HERRAMIENTAS CON IMÁGENES ---
        estilo_herramienta = """
            QPushButton { background-color: transparent; border: none; padding: 2px; }
            QPushButton:hover { background-color: #e0e0e0; border-radius: 4px; }
            QPushButton:checked { background-color: #cce5ff; border: 1px solid #007bff; border-radius: 4px; }
            QPushButton:disabled { opacity: 0.5; }
        """
        
        self.btn_herramienta_caja = QPushButton()
        self.btn_herramienta_caja.setIcon(QIcon("assets/seleccionar.png"))
        self.btn_herramienta_caja.setIconSize(QSize(28, 28))
        self.btn_herramienta_caja.setToolTip("Crear seleccion")
        self.btn_herramienta_caja.setStyleSheet(estilo_herramienta)
        self.btn_herramienta_caja.setCheckable(True)
        self.btn_herramienta_caja.setEnabled(False)
        
        self.btn_herramienta_eliminar = QPushButton()
        self.btn_herramienta_eliminar.setIcon(QIcon("assets/borrar.png"))
        self.btn_herramienta_eliminar.setIconSize(QSize(28, 28))
        self.btn_herramienta_eliminar.setToolTip("Eliminar seleccion")
        self.btn_herramienta_eliminar.setStyleSheet(estilo_herramienta)
        self.btn_herramienta_eliminar.setCheckable(True)
        self.btn_herramienta_eliminar.setEnabled(False)
        
        self.btn_herramienta_caja.clicked.connect(self.toggle_herramienta_caja)
        self.btn_herramienta_eliminar.clicked.connect(self.toggle_herramienta_eliminar)

        controles_superiores.addWidget(self.btn_herramienta_caja)
        controles_superiores.addWidget(self.btn_herramienta_eliminar)
        controles_superiores.addSpacing(15)

        # --- ZOOM Y BLOQUEO INTERACTIVO ---
        lbl_minus = QLabel("-")
        lbl_minus.setStyleSheet("font-size: 24px; font-weight: bold; color: #555;")
        
        lbl_plus = QLabel("+")
        lbl_plus.setStyleSheet("font-size: 20px; font-weight: bold; color: #555;")
        
        self.sld_nivel_zoom = QSlider(Qt.Orientation.Horizontal)
        self.sld_nivel_zoom.setRange(50, 400)
        self.sld_nivel_zoom.setValue(100)
        self.sld_nivel_zoom.setFixedWidth(120)
        self.sld_nivel_zoom.setEnabled(False)
        
        self.btn_zoom_reset = QPushButton("Reset")
        self.btn_zoom_reset.setStyleSheet("""
            QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; padding: 4px 10px; font-weight: bold; color:#007bff;}
            QPushButton:hover { background-color: #e0e0e0; }
            QPushButton:disabled { color:#aaa; }
        """)
        self.btn_zoom_reset.setEnabled(False)

        # Botón para bloquear/desbloquear zoom interactivo
        self.btn_bloquear_zoom = QPushButton()
        self.btn_bloquear_zoom.setIcon(QIcon("assets/desbloqueado.png"))
        self.btn_bloquear_zoom.setIconSize(QSize(24, 24))
        self.btn_bloquear_zoom.setToolTip("Bloquear zoom")
        self.btn_bloquear_zoom.setStyleSheet(estilo_herramienta)
        self.btn_bloquear_zoom.setCheckable(True)
        self.btn_bloquear_zoom.setEnabled(False)
        self.btn_bloquear_zoom.toggled.connect(self.toggle_bloqueo_zoom)
        
        controles_superiores.addWidget(lbl_minus)
        controles_superiores.addWidget(self.sld_nivel_zoom)
        controles_superiores.addWidget(lbl_plus)
        controles_superiores.addSpacing(5)
        controles_superiores.addWidget(self.btn_zoom_reset)
        controles_superiores.addWidget(self.btn_bloquear_zoom)
        
        # --- VISOR IMAGEN ---
        self.visor_imagen = InteractiveImageViewer()
        self.visor_imagen.setText("Sube una imagen .tiff para empezar el análisis...")
        self.visor_imagen.setStyleSheet("border: 2px dashed #aaa; background-color: #f0f0f0; font-size: 18px; color: #666;")
        
        self.visor_imagen.conteo_actualizado.connect(self.actualizar_etiqueta_conteo)
        self.visor_imagen.nueva_caja_dibujada.connect(self.agregar_microglia_manual)
        self.visor_imagen.nivel_zoom_cambiado.connect(self.sld_nivel_zoom.setValue)
        
        self.sld_nivel_zoom.valueChanged.connect(self.visor_imagen.set_zoom)
        self.btn_zoom_reset.clicked.connect(self.reset_zoom)

        area_imagen.addLayout(controles_superiores)
        area_imagen.addWidget(self.visor_imagen, stretch=1)
        
        layout_principal.addWidget(frame_menu)
        layout_principal.addLayout(area_imagen, stretch=1)
        widget_central.setLayout(layout_principal)
        self.setCentralWidget(widget_central)
        
        self.btn_cargar.clicked.connect(self.cargar_imagen)
        self.btn_cerrar_sesion.clicked.connect(self.cerrar_sesion)
        self.btn_conteo.clicked.connect(self.execute_microglia_counting)
        self.btn_filtrar.clicked.connect(self.ejecutar_filtrado)
        self.btn_ramas.clicked.connect(self.mostrar_ramas_morfologia)
        
        self.actualizar_estado_flujo(0)
        
        if self.rol == "Invitado" or self.rol == "Guest":
            self.btn_historial.hide()
            self.btn_reporte.hide()
            self.btn_guardar_img.hide()

    def toggle_herramienta_caja(self, checked):
        if checked:
            self.btn_herramienta_eliminar.setChecked(False)
            self.visor_imagen.current_tool = "draw"
        else:
            self.visor_imagen.current_tool = "pointer"

    def toggle_herramienta_eliminar(self, checked):
        if checked:
            self.btn_herramienta_caja.setChecked(False)
            self.visor_imagen.current_tool = "delete"
        else:
            self.visor_imagen.current_tool = "pointer"

    def reset_zoom(self):
        self.sld_nivel_zoom.setValue(100)
        self.visor_imagen.pan_x = 0
        self.visor_imagen.pan_y = 0
        self.visor_imagen.update()

    def toggle_bloqueo_zoom(self, checked):
        if checked:
            self.btn_bloquear_zoom.setIcon(QIcon("assets/bloqueado.png"))
            self.btn_bloquear_zoom.setToolTip("Desbloquear zoom")
        else:
            self.btn_bloquear_zoom.setIcon(QIcon("assets/desbloqueado.png"))
            self.btn_bloquear_zoom.setToolTip("Bloquear zoom")
            
        self.sld_nivel_zoom.setEnabled(not checked)
        self.btn_zoom_reset.setEnabled(not checked)
        self.visor_imagen.lock_zoom(checked)

    def actualizar_estado_flujo(self, paso):
        if paso == 0:
            self.btn_cargar.setEnabled(True)
            self.btn_conteo.setEnabled(False)
            self.btn_filtrar.setEnabled(False)
            self.btn_ramas.setEnabled(False)
            self.btn_reporte.setEnabled(False)
            self.btn_guardar_img.setEnabled(False)
            self.combo_vista.setEnabled(False)
            self.btn_herramienta_caja.setEnabled(False)
            self.btn_herramienta_eliminar.setEnabled(False)
        elif paso == 1:
            self.btn_cargar.setEnabled(True)
            self.btn_conteo.setEnabled(True)
            self.btn_filtrar.setEnabled(False)
            self.btn_ramas.setEnabled(False)
            self.btn_reporte.setEnabled(False)
            self.btn_guardar_img.setEnabled(True)
            self.combo_vista.setEnabled(False)
            self.btn_herramienta_caja.setEnabled(False)
            self.btn_herramienta_eliminar.setEnabled(False)
        elif paso == 2:
            self.btn_cargar.setEnabled(False)
            self.btn_conteo.setEnabled(False)
            self.btn_filtrar.setEnabled(True)
            self.btn_ramas.setEnabled(False)
            self.combo_vista.setEnabled(True)
            
            # Habilitar herramientas de edición manual SOLAMENTE al contar
            self.btn_herramienta_caja.setEnabled(True)
            self.btn_herramienta_eliminar.setEnabled(True)
            
            self.sld_nivel_zoom.setEnabled(True)
            self.btn_zoom_reset.setEnabled(True)
            self.btn_bloquear_zoom.setEnabled(True)
        elif paso == 3:
            self.btn_cargar.setEnabled(False)
            self.btn_conteo.setEnabled(False)
            self.btn_filtrar.setEnabled(False)
            self.btn_ramas.setEnabled(True)
            
            # Se bloquean para no corromper el análisis posterior
            self.btn_herramienta_caja.setEnabled(False)
            self.btn_herramienta_caja.setChecked(False)
            self.btn_herramienta_eliminar.setEnabled(False)
            self.btn_herramienta_eliminar.setChecked(False)
            self.visor_imagen.current_tool = "pointer"
        elif paso == 4:
            self.btn_cargar.setEnabled(True)
            self.btn_conteo.setEnabled(False)
            self.btn_filtrar.setEnabled(False)
            self.btn_ramas.setEnabled(False)
            self.btn_reporte.setEnabled(True)
            
            self.btn_herramienta_caja.setEnabled(False)
            self.btn_herramienta_eliminar.setEnabled(False)

    def actualizar_etiqueta_conteo(self, conteo):
        self.lbl_info_conteo.setText(f"Microglías detectadas: {conteo}")

    def cargar_imagen(self):
        ruta_archivo, _ = QFileDialog.getOpenFileName(self, "Seleccionar imagen", "", "Imágenes TIFF (*.tiff *.tif);;Todas las imágenes (*.png *.jpg *.jpeg)")
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
                            cv_img = ((cv_img - cv_img.min()) / (cv_img.max() - cv_img.min()) * 255).astype(np.uint8)
                        if len(cv_img.shape) == 2:
                            h, w = cv_img.shape
                            qimg = QImage(cv_img.data, w, h, w, QImage.Format.Format_Grayscale8)
                        else:
                            cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                            h, w, ch = cv_img.shape
                            qimg = QImage(cv_img.data, w, h, ch * w, QImage.Format.Format_RGB888)
                        pixmap = QPixmap.fromImage(qimg)
                except Exception as e:
                    logging.error(f"Error al cargar imagen: {e}")
            
            if not pixmap.isNull():
                self.pixmaps_globales["Original"] = pixmap
                self.pixmaps_globales["Filtrada"] = None
                self.pixmaps_globales["Esqueleto"] = None
                
                self.btn_herramienta_caja.setChecked(False)
                self.btn_herramienta_eliminar.setChecked(False)
                self.visor_imagen.current_tool = "pointer"
                self.btn_bloquear_zoom.setChecked(False)
                self.reset_zoom()
                
                self.visor_imagen.set_image_and_boxes(pixmap, [])
                self.actualizar_estado_flujo(1)
                
                self.combo_vista.blockSignals(True)
                self.combo_vista.setCurrentText("Original")
                self.combo_vista.blockSignals(False)
                self.visor_imagen.view_mode = "Original"
                QMessageBox.information(self, "Imagen cargada", "Imagen lista para el análisis.")
            else:
                QMessageBox.critical(self, "Error", "El archivo está corrupto o no es válido.")

    def cambiar_vista_global(self, texto_vista):
        pixmap_guardado = self.pixmaps_globales.get(texto_vista)
        if pixmap_guardado:
            self.visor_imagen.set_view_mode(texto_vista, pixmap_guardado)
        else:
            QMessageBox.warning(self, "Aviso", f"Aún no has generado el paso: {texto_vista}.")
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
            QMessageBox.warning(self, "Advertencia", "Por favor, carga una imagen primero.")
            return
        
        dialogo = DialogoCarga("Cargando IA y aplicando conteo...\nPor favor, espera.", self)
        dialogo.show()
        from PyQt6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        
        try:
            from ia.modelo_yolo import MicrogliaProcessor
            model_path = os.path.join(os.getcwd(), "ia", "entrenamiento_resultados", "modelo_microglias5", "weights", "best.pt")
            output_dir = os.path.join(os.getcwd(), "analisis_resultados")
            
            processor = MicrogliaProcessor(model_path=model_path)
            resultado = processor.process_and_crop(self.ruta_imagen_actual, base_output_folder=output_dir)
            
            if len(resultado) == 3:
                crops_folder, count, boxes_data = resultado
                self.visor_imagen.set_image_and_boxes(self.pixmaps_globales["Original"], boxes_data)
            else:
                crops_folder, count = resultado
                self.visor_imagen.set_image_and_boxes(self.pixmaps_globales["Original"], [])
            
            dialogo.close()
            QApplication.restoreOverrideCursor()
            
            self.actualizar_estado_flujo(2)
            
            QMessageBox.information(
                self,
                "1. Conteo completado",
                f"Se detectaron {count} posibles microglías.\n\n"
            )
            
        except Exception as e:
            dialogo.close()
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", str(e))

    def agregar_microglia_manual(self, x, y, w, h):
        if not self.ruta_imagen_actual:
            return
            
        base_name = Path(self.ruta_imagen_actual).stem
        crops_folder = os.path.join(os.getcwd(), "analisis_resultados", base_name, "crops")
        os.makedirs(crops_folder, exist_ok=True)
        
        orig_pixmap = self.pixmaps_globales["Original"]
        if not orig_pixmap:
            return
            
        rect_recorte = QRect(x, y, w, h)
        pixmap_recorte = orig_pixmap.copy(rect_recorte)
        
        nombre_archivo = f"manual_{uuid.uuid4().hex[:6]}.png"
        ruta_guardado = os.path.join(crops_folder, nombre_archivo)
        pixmap_recorte.save(ruta_guardado, "PNG")
        
        nueva_caja = {
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "crop_path": ruta_guardado
        }
        
        self.visor_imagen.boxes.append(nueva_caja)
        self.visor_imagen.draw_current_state()
        self.visor_imagen.conteo_actualizado.emit(len(self.visor_imagen.boxes))

    def construir_imagen_global(self, carpeta_origen):
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
        qimg = QImage(lienzo.data, orig_w, orig_h, orig_w, QImage.Format.Format_Grayscale8).copy()
        return QPixmap.fromImage(qimg)

    def ejecutar_filtrado(self):
        if not self.ruta_imagen_actual or not self.visor_imagen.boxes:
            QMessageBox.warning(self, "Advertencia", "Aplica el conteo primero.")
            return
            
        base_name = Path(self.ruta_imagen_actual).stem
        filtradas_dir = os.path.join(os.getcwd(), "analisis_resultados", base_name, "filtradas")
        os.makedirs(filtradas_dir, exist_ok=True)
        import cv2
        import numpy as np
        count = 0
        from PyQt6.QtWidgets import QApplication
        
        try:
            dialogo = DialogoCarga("Aplicando filtrado a las células...\nPor favor, espera.", self)
            dialogo.show()
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents()
            
            for box in self.visor_imagen.boxes:
                crop_path = box["crop_path"]
                if os.path.exists(crop_path):
                    with open(crop_path, "rb") as f:
                        file_bytes = bytearray(f.read())
                    img_array = np.asarray(file_bytes, dtype=np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        blur = cv2.GaussianBlur(img, (5, 5), 0)
                        _, bin_img = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        nombre = os.path.basename(crop_path)
                        out_path = os.path.join(filtradas_dir, nombre)
                        is_success, im_buf_arr = cv2.imencode(".png", bin_img)
                        if is_success:
                            im_buf_arr.tofile(out_path)
                            count += 1
                            
            dialogo.close()
            QApplication.restoreOverrideCursor()
            
            if count > 0:
                pixmap_filtrada = self.construir_imagen_global("filtradas")
                self.pixmaps_globales["Filtrada"] = pixmap_filtrada
                
                self.actualizar_estado_flujo(3)
                
                self.combo_vista.setCurrentText("Filtrada")
                QMessageBox.information(self, "2. Filtrado", f"Se binarizaron {count} microglías.")
            else:
                QMessageBox.warning(self, "Error", "No se pudo procesar ninguna imagen. Las cajas de YOLO están vacías.")
        except Exception as error:
            dialogo.close()
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Falló el filtrado: {str(error)}")

    def mostrar_ramas_morfologia(self):
        if not self.ruta_imagen_actual or not self.visor_imagen.boxes:
            QMessageBox.warning(self, "Advertencia", "Aplica el conteo y filtrado primero.")
            return
            
        base_name = Path(self.ruta_imagen_actual).stem
        filtradas_dir = os.path.join(os.getcwd(), "analisis_resultados", base_name, "filtradas")
        esqueletos_dir = os.path.join(os.getcwd(), "analisis_resultados", base_name, "esqueletos")
        os.makedirs(esqueletos_dir, exist_ok=True)
        
        import cv2
        import numpy as np
        from skimage.morphology import skeletonize
        from PyQt6.QtWidgets import QApplication
        count = 0
        try:
            dialogo = DialogoCarga("Generando esqueletos topológicos...\nPor favor, espera.", self)
            dialogo.show()
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            QApplication.processEvents()
            
            for box in self.visor_imagen.boxes:
                crop_path = box["crop_path"]
                nombre = os.path.basename(crop_path)
                fil_path = os.path.join(filtradas_dir, nombre)
                
                if os.path.exists(fil_path):
                    with open(fil_path, "rb") as f:
                        file_bytes = bytearray(f.read())
                    img_array = np.asarray(file_bytes, dtype=np.uint8)
                    img_raw = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
                    
                    if img_raw is not None:
                        _, bin_img = cv2.threshold(img_raw, 127, 255, cv2.THRESH_BINARY)
                        img_bool = bin_img > 0
                        skeleton = skeletonize(img_bool)
                        skeleton_img = (skeleton * 255).astype(np.uint8)
                        out_path = os.path.join(esqueletos_dir, nombre)
                        is_success, im_buf_arr = cv2.imencode(".png", skeleton_img)
                        if is_success:
                            im_buf_arr.tofile(out_path)
                            count += 1
                            
            dialogo.close()
            QApplication.restoreOverrideCursor()
            
            if count > 0:
                pixmap_esqueleto = self.construir_imagen_global("esqueletos")
                self.pixmaps_globales["Esqueleto"] = pixmap_esqueleto
                
                self.actualizar_estado_flujo(4)
                
                self.combo_vista.setCurrentText("Esqueleto")
                QMessageBox.information(self, "3. Ramas Generadas", f"Se generaron {count} esqueletos topológicos.\n\nYa puedes avanzar a los Reportes o Cargar una imagen nueva.")
            else:
                QMessageBox.warning(self, "Advertencia", "No se generaron esqueletos. Verifica la carpeta de filtrado.")
        except Exception as error:
            dialogo.close()
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error de Procesamiento", f"Falló el cálculo:\n{str(error)}")