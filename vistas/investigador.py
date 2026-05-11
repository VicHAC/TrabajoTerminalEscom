import logging
import os
import subprocess
import uuid
from pathlib import Path

from ia.modelo_yolo import MIN_MICROGLIA_SIZE

from PyQt6.QtCore import pyqtSignal, QRect, Qt, QSize, QEvent, QPoint
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QIcon, QIntValidator
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QSlider,
    QCheckBox,
    QLineEdit,
    QToolTip,
)
from PyQt6.QtCore import QTimer

# os.environ["QT_QPA_PLATFORM"] = "xcb"


from ia.morphology_analyzer import MorphologyAnalyzer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
# Silence chatty libraries
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("fpdf").setLevel(logging.WARNING)

# =========================================================
# BOTÓN PERSONALIZADO PARA TOOLTIPS SEGUROS (ANTI-CORTES)
# =========================================================
class SafeToolTipButton(QPushButton):
    """
    Un botón que fuerza al ToolTip a mostrarse desplazado hacia la izquierda.
    Garantiza que el texto nunca se corte en el borde derecho de la pantalla (WSL/Pantalla Completa).
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_tooltip = ""

    def setCustomToolTip(self, text):
        self.custom_tooltip = text
        self.setToolTip(text)

    def event(self, e):
        if e.type() == QEvent.Type.ToolTip:
            if self.custom_tooltip:
                global_pos = self.mapToGlobal(QPoint(0, self.height() + 2))
                global_pos.setX(global_pos.x() - 80)
                QToolTip.showText(global_pos, self.custom_tooltip, self)
            return True
        return super().event(e)


# =========================================================
# ZONA DE ARRASTRAR Y SOLTAR (DRAG & DROP)
# =========================================================
class DropZone(QFrame):
    file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.setObjectName("DropZoneObj")
        
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.setContentsMargins(10, 10, 10, 15) 
        
        self.lbl_icono = QLabel()
        self.lbl_icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icono.setStyleSheet("border: none; background: transparent;")
        self.lbl_icono.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self.lbl_texto = QLabel("Haz clic para cargar una imagen o arrástrala aquí")
        self.lbl_texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_texto.setWordWrap(True)
        self.lbl_texto.setStyleSheet("color: #888888; font-size: 12px; font-weight: normal; border: none; background: transparent;")
        self.lbl_texto.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self.layout.addWidget(self.lbl_icono, stretch=1)
        self.layout.addWidget(self.lbl_texto)
        
        self.pixmap_original = None
        self.is_preview = False
        
        self.mostrar_placeholder()

    def mostrar_placeholder(self):
        self.is_preview = False
        self.pixmap_original = QPixmap("assets/cargar.png")
        
        self.lbl_texto.setText("Haz clic para cargar una imagen o arrástrala aquí")
        self.lbl_texto.setStyleSheet("color: #888888; font-size: 12px; font-weight: normal; border: none; background: transparent;")
        
        self.setStyleSheet("""
            #DropZoneObj {
                border: 2px dashed #007bff;
                border-radius: 8px;
                background-color: #ffffff;
            }
            #DropZoneObj:hover {
                background-color: #f4f8fb;
                border: 2px dashed #0056b3;
            }
        """)
        self.actualizar_imagen()

    def mostrar_imagen(self, pixmap, nombre_archivo):
        self.is_preview = True
        self.pixmap_original = pixmap
        
        self.lbl_texto.setText(f"Archivo seleccionado: <b>{nombre_archivo}</b>")
        self.lbl_texto.setStyleSheet("color: #333333; font-size: 12px; border: none; background: transparent;")
        
        self.setStyleSheet("""
            #DropZoneObj {
                border: 2px solid #28a745;
                border-radius: 8px;
                background-color: #ffffff;
            }
        """)
        self.actualizar_imagen()

    def actualizar_imagen(self):
        if self.pixmap_original and not self.pixmap_original.isNull():
            w = self.width() - 20
            h = self.height() - 60 
            
            if w > 0 and h > 0:
                self.lbl_icono.setPixmap(self.pixmap_original.scaled(
                    w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                ))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.actualizar_imagen()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                file_path = urls[0].toLocalFile()
                ext = Path(file_path).suffix.lower()
                if ext in [".tif", ".tiff", ".png", ".jpg", ".jpeg"]:
                    self.file_selected.emit(file_path)
        else:
            event.ignore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            ruta_archivo, _ = QFileDialog.getOpenFileName(
                self, "Seleccionar imagen", "", "Imágenes TIFF (*.tiff *.tif);;Todas las imágenes (*.png *.jpg *.jpeg)"
            )
            if ruta_archivo:
                self.file_selected.emit(ruta_archivo)


# =========================================================
# DIÁLOGO INTERMEDIO PARA CARGA DE DATOS
# =========================================================
class DialogoCargarImagen(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detalles del Campo")
        self.setFixedSize(580, 520) 
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        
        from vistas.utilidades import set_app_icon
        set_app_icon(self)
        
        self.ruta_seleccionada = None
        self.campo_val = ""
        self.tiempo_val = ""

        main_layout = QVBoxLayout(self)
        frame = QFrame(self)
        frame.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 12px; border: 2px solid #003366; } QLabel { border: none; }")
        layout = QVBoxLayout(frame)
        
        lbl_titulo = QLabel("Detalles del Campo")
        lbl_titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #003366;")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_titulo)
        layout.addSpacing(10)

        layout_campos = QHBoxLayout()
        
        layout_campo = QVBoxLayout()
        lbl_campo = QLabel("Campo:")
        lbl_campo.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.input_campo = QLineEdit()
        self.input_campo.setPlaceholderText("Ej. Campo A, Campo B, 1...")
        self.input_campo.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px;")
        layout_campo.addWidget(lbl_campo)
        layout_campo.addWidget(self.input_campo)

        layout_tiempo = QVBoxLayout()
        lbl_tiempo = QLabel("Tiempo de la muestra:")
        lbl_tiempo.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.input_tiempo = QLineEdit()
        self.input_tiempo.setPlaceholderText("Ej. 1hr, 2hrs, 1 semana...")
        self.input_tiempo.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px;")
        layout_tiempo.addWidget(lbl_tiempo)
        layout_tiempo.addWidget(self.input_tiempo)

        layout_campos.addLayout(layout_campo)
        layout_campos.addSpacing(15)
        layout_campos.addLayout(layout_tiempo)
        
        layout.addLayout(layout_campos)
        layout.addSpacing(15)

        self.drop_zone = DropZone(self)
        self.drop_zone.file_selected.connect(self.procesar_archivo)
        layout.addWidget(self.drop_zone, stretch=1)
        layout.addSpacing(10)

        layout_botones = QHBoxLayout()
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancelar.setStyleSheet("""
            QPushButton { padding: 8px; background-color: #e0e0e0; border-radius: 4px; font-weight: bold; color: #333;}
            QPushButton:hover { background-color: #cccccc; }
        """)
        btn_cancelar.clicked.connect(self.reject)
        
        btn_continuar = QPushButton("Continuar")
        btn_continuar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_continuar.setStyleSheet("""
            QPushButton { padding: 8px; background-color: #007bff; border-radius: 4px; font-weight: bold; color: white;}
            QPushButton:hover { background-color: #0056b3; }
        """)
        btn_continuar.clicked.connect(self.validar_y_continuar)
        
        layout_botones.addWidget(btn_cancelar)
        layout_botones.addWidget(btn_continuar)
        
        layout.addLayout(layout_botones)
        main_layout.addWidget(frame)

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            p_geom = self.parent().geometry()
            self.move(p_geom.x() + (p_geom.width() - self.width()) // 2, p_geom.y() + (p_geom.height() - self.height()) // 2)
        else:
            screen = QApplication.primaryScreen().geometry()
            self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def procesar_archivo(self, ruta):
        self.ruta_seleccionada = ruta
        nombre_archivo = os.path.basename(ruta)
        
        try:
            import cv2
            import numpy as np
            cv_img = cv2.imread(ruta, cv2.IMREAD_UNCHANGED)
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
                pixmap_preview = QPixmap.fromImage(qimg)
            else:
                pixmap_preview = QPixmap(ruta)
        except Exception as e:
            logging.error(f"Error al previsualizar: {e}")
            pixmap_preview = QPixmap(ruta)

        if not pixmap_preview.isNull():
            self.drop_zone.mostrar_imagen(pixmap_preview, nombre_archivo)

    def validar_y_continuar(self):
        if not self.input_campo.text().strip() or not self.input_tiempo.text().strip() or not self.ruta_seleccionada:
            from vistas.utilidades import DialogoNotificacion
            DialogoNotificacion("Error", "Campos incompletos", "warning", self).exec()
            return
        
        self.campo_val = self.input_campo.text().strip()
        self.tiempo_val = self.input_tiempo.text().strip()
        self.accept()


# =========================================================
# CLASES AUXILIARES Y VISOR INTERACTIVO
# =========================================================
class DialogoCarga(QDialog):
    def __init__(self, mensaje="Procesando...", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        
        from vistas.utilidades import set_app_icon
        set_app_icon(self)
        
        layout = QVBoxLayout(self)
        frame = QFrame(self)
        frame.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border-radius: 12px; border: 2px solid #003366; }
            QLabel { color: #003366; font-size: 16px; font-weight: bold; padding: 20px; }
        """)
        flayout = QVBoxLayout(frame)
        label = QLabel(mensaje)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        flayout.addWidget(label)
        layout.addWidget(frame)
        self.setLayout(layout)

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            p_geom = self.parent().geometry()
            self.move(p_geom.x() + (p_geom.width() - self.width()) // 2, p_geom.y() + (p_geom.height() - self.height()) // 2)
        else:
            screen = QApplication.primaryScreen().geometry()
            self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)


class DialogoComparativo(QDialog):
    """
    Muestra las 3 fases del proceso lado a lado para una microglía,
    o una versión sobrepuesta (esqueleto sobre original).
    """
    def __init__(self, fases, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Proceso de la Microglía")
        self.setFixedSize(950, 500) 
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        from vistas.utilidades import set_app_icon
        set_app_icon(self)
        
        self.fases = fases
        self.modo_sobrepuesto = False
        
        main_layout = QVBoxLayout(self)
        self.frame = QFrame(self)
        self.frame.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 12px; border: 2px solid #003366; } QLabel { border: none; }")
        self.layout_principal = QVBoxLayout(self.frame)
        
        self.lbl_titulo = QLabel("<b>Comparativa del Proceso de la Microglía</b>")
        self.lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_titulo.setStyleSheet("font-size: 18px; color: #003366; margin-bottom: 10px;")
        self.layout_principal.addWidget(self.lbl_titulo)

        # Widget para vista lado a lado
        self.widget_lado_lado = QWidget()
        self.layout_lado_lado = QHBoxLayout(self.widget_lado_lado)
        for fase in self.fases:
            v_layout = QVBoxLayout()
            lbl_nombre_fase = QLabel(fase["nombre"])
            lbl_nombre_fase.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_nombre_fase.setStyleSheet("font-weight: bold; color: #555; margin-bottom: 5px;")
            
            lbl_img = QLabel()
            lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = fase["pixmap"] if fase["pixmap"] else QPixmap(fase["path"])
            if pixmap and not pixmap.isNull():
                lbl_img.setPixmap(pixmap.scaled(280, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                lbl_img.setText("N/D")
            v_layout.addWidget(lbl_nombre_fase)
            v_layout.addWidget(lbl_img)
            self.layout_lado_lado.addLayout(v_layout)
        
        # Widget para vista sobrepuesta
        self.widget_sobrepuesto = QWidget()
        self.widget_sobrepuesto.hide()
        layout_s = QVBoxLayout(self.widget_sobrepuesto)
        self.lbl_img_sobrepuesto = QLabel()
        self.lbl_img_sobrepuesto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_s.addWidget(self.lbl_img_sobrepuesto)
        
        self.layout_principal.addWidget(self.widget_lado_lado)
        self.layout_principal.addWidget(self.widget_sobrepuesto)
        
        self.layout_principal.addSpacing(15)
        
        layout_botones = QHBoxLayout()
        
        self.btn_toggle = QPushButton("Ver Sobrepuesto")
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setStyleSheet("""
            QPushButton { padding: 8px 20px; background-color: #007bff; border-radius: 6px; font-weight: bold; color: white; font-size: 13px;}
            QPushButton:hover { background-color: #0069d9; }
        """)
        self.btn_toggle.clicked.connect(self.toggle_modo)
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cerrar.setStyleSheet("""
            QPushButton { padding: 8px 20px; background-color: #dc3545; border-radius: 6px; font-weight: bold; color: white; font-size: 14px;}
            QPushButton:hover { background-color: #c82333; }
        """)
        btn_cerrar.clicked.connect(self.accept)
        
        layout_botones.addStretch()
        layout_botones.addWidget(self.btn_toggle)
        layout_botones.addSpacing(15)
        layout_botones.addWidget(btn_cerrar)
        layout_botones.addStretch()
        
        self.layout_principal.addLayout(layout_botones)
        main_layout.addWidget(self.frame)
        self.setLayout(main_layout)

    def toggle_modo(self):
        self.modo_sobrepuesto = not self.modo_sobrepuesto
        if self.modo_sobrepuesto:
            self.lbl_titulo.setText("<b>Esqueleto Sobrepuesto en Original</b>")
            self.btn_toggle.setText("Ver Proceso Completo")
            self.widget_lado_lado.hide()
            self.widget_sobrepuesto.show()
            self.setFixedSize(500, 500)
            self.generar_sobrepuesto()
        else:
            self.lbl_titulo.setText("<b>Comparativa del Proceso de la Microglía</b>")
            self.btn_toggle.setText("Ver Sobrepuesto")
            self.widget_sobrepuesto.hide()
            self.widget_lado_lado.show()
            self.setFixedSize(950, 500)
            
        # Recentrar ventana
        self.ajustar_posicion()

    def ajustar_posicion(self):
        if self.parent():
            p_geom = self.parent().geometry()
            self.move(p_geom.x() + (p_geom.width() - self.width()) // 2, p_geom.y() + (p_geom.height() - self.height()) // 2)

    def generar_sobrepuesto(self):
        # Original (Fase 0)
        pix_orig = self.fases[0]["pixmap"] if self.fases[0]["pixmap"] else QPixmap(self.fases[0]["path"])
        # Esqueleto (Fase 2)
        pix_esq = self.fases[2]["pixmap"] if self.fases[2]["pixmap"] else QPixmap(self.fases[2]["path"])
        
        if pix_orig and pix_esq and not pix_orig.isNull() and not pix_esq.isNull():
            final_pix = pix_orig.copy()
            painter = QPainter(final_pix)
            
            # Usamos modo 'Screen' que es ideal para sobreponer blanco sobre fondos oscuros
            # Ignora el negro (0) y resalta el blanco (1).
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
            painter.setOpacity(0.9) # Alta opacidad para que las líneas blancas sean nítidas
            
            painter.drawPixmap(0, 0, pix_esq)
            painter.end()
            self.lbl_img_sobrepuesto.setPixmap(final_pix.scaled(380, 380, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def showEvent(self, event):
        super().showEvent(event)
        self.ajustar_posicion()


class DialogoVistaCelular(QDialog):
    """
    Ventana detallada que permite navegar entre las fases de procesamiento
    de una microglía específica (Original < Filtrado > Esqueletizado).
    """
    def __init__(self, crop_path, pixmap_mem=None, modo_inicial="Original", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vista Detallada de la Célula")
        self.resize(450, 520) 
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        from vistas.utilidades import set_app_icon
        set_app_icon(self)
        
        self.crop_path = crop_path
        self.pixmap_mem_filtrado = pixmap_mem
        self.fases_disponibles = []
        self.preparar_fases()
        
        # Establecer índice inicial basado en el modo de la ventana principal
        self.indice_fase = 0
        mapping = {"Original": "ORIGINAL", "Filtrada": "FILTRADO", "Esqueleto": "ESQUELETIZADO", "Previsualización": "FILTRADO"}
        nombre_buscado = mapping.get(modo_inicial, "ORIGINAL")
        for i, f in enumerate(self.fases_disponibles):
            if f["nombre"] == nombre_buscado:
                self.indice_fase = i
                break
        
        main_layout = QVBoxLayout(self)
        frame = QFrame(self)
        frame.setStyleSheet("QFrame { background-color: #FFFFFF; border-radius: 12px; border: 2px solid #003366; } QLabel { border: none; }")
        layout = QVBoxLayout(frame)
        
        nombre_archivo = os.path.basename(crop_path)
        lbl_nombre = QLabel(f"Identificador: <b>{nombre_archivo}</b>")
        lbl_nombre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_nombre.setStyleSheet("font-size: 15px; color: #003366; margin-bottom: 5px;")
        layout.addWidget(lbl_nombre)

        # Nombre de la fase actual
        self.lbl_fase = QLabel("FASE: ORIGINAL")
        self.lbl_fase.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_fase.setStyleSheet("font-size: 13px; font-weight: bold; color: #555; margin-bottom: 5px;")
        layout.addWidget(self.lbl_fase)

        # Contenedor de imagen con botones de navegación lateral
        layout_imagen_nav = QHBoxLayout()
        
        self.btn_ant = QPushButton("<")
        self.btn_ant.setFixedSize(30, 60)
        self.btn_ant.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ant.setStyleSheet("QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; font-size: 18px; font-weight: bold; color: #003366; } QPushButton:hover { background-color: #e0e0e0; } QPushButton:disabled { color: #ccc; }")
        self.btn_ant.clicked.connect(self.mostrar_anterior)
        
        self.label_imagen = QLabel()
        self.label_imagen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_imagen.setFixedSize(380, 380)
        
        self.btn_sig = QPushButton(">")
        self.btn_sig.setFixedSize(30, 60)
        self.btn_sig.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sig.setStyleSheet("QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; font-size: 18px; font-weight: bold; color: #003366; } QPushButton:hover { background-color: #e0e0e0; } QPushButton:disabled { color: #ccc; }")
        self.btn_sig.clicked.connect(self.mostrar_siguiente)
        
        layout_imagen_nav.addWidget(self.btn_ant)
        layout_imagen_nav.addWidget(self.label_imagen, stretch=1)
        layout_imagen_nav.addWidget(self.btn_sig)
        
        layout.addLayout(layout_imagen_nav)
        layout.addSpacing(10)
        
        # Botones inferiores
        layout_inferior = QHBoxLayout()
        
        self.btn_comparativa = QPushButton("Ver Proceso Completo")
        self.btn_comparativa.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_comparativa.setStyleSheet("""
            QPushButton { padding: 8px 15px; background-color: #28a745; border-radius: 6px; font-weight: bold; color: white; font-size: 13px;}
            QPushButton:hover { background-color: #218838; }
            QPushButton:disabled { background-color: #ccc; }
        """)
        self.btn_comparativa.clicked.connect(self.mostrar_comparativa)
        # Solo habilitar si el proceso está terminado (las 3 fases existen)
        self.btn_comparativa.setEnabled(len(self.fases_disponibles) == 3)
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cerrar.setStyleSheet("""
            QPushButton { padding: 8px 20px; background-color: #dc3545; border-radius: 6px; font-weight: bold; color: white; font-size: 14px;}
            QPushButton:hover { background-color: #c82333; }
        """)
        btn_cerrar.clicked.connect(self.accept)
        
        layout_inferior.addStretch()
        layout_inferior.addWidget(self.btn_comparativa)
        layout_inferior.addSpacing(10)
        layout_inferior.addWidget(btn_cerrar)
        layout_inferior.addStretch()
        
        layout.addLayout(layout_inferior)
        main_layout.addWidget(frame)
        self.setLayout(main_layout)
        
        self.actualizar_vista()

    def preparar_fases(self):
        # Fase 0: Original
        self.fases_disponibles.append({"nombre": "ORIGINAL", "path": self.crop_path, "pixmap": None})
        
        # Fase 1: Filtrado
        path_filtrado = self.crop_path.replace("/crops/", "/filtradas/").replace("\\crops\\", "\\filtradas\\")

        if self.pixmap_mem_filtrado:
            self.fases_disponibles.append({"nombre": "FILTRADO", "path": path_filtrado, "pixmap": self.pixmap_mem_filtrado})
        elif os.path.exists(path_filtrado):
            self.fases_disponibles.append({"nombre": "FILTRADO", "path": path_filtrado, "pixmap": None})
            
        # Fase 2: Esqueletizado
        path_esqueleto = self.crop_path.replace("/crops/", "/esqueletos/").replace("\\crops\\", "\\esqueletos\\")

        if os.path.exists(path_esqueleto):
            self.fases_disponibles.append({"nombre": "ESQUELETIZADO", "path": path_esqueleto, "pixmap": None})

    def actualizar_vista(self):
        fase = self.fases_disponibles[self.indice_fase]
        self.lbl_fase.setText(f"FASE: {fase['nombre']}")
        
        pixmap = fase["pixmap"]
        if not pixmap:
            pixmap = QPixmap(fase["path"])
            
        if pixmap and not pixmap.isNull():
            self.label_imagen.setPixmap(pixmap.scaled(380, 380, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.label_imagen.setText(f"No se pudo cargar la imagen de {fase['nombre']}.")
            
        # Unicamente en las imagenes detalladas quiero que los botones no se oculten, que se deshabiliten
        self.btn_ant.setEnabled(self.indice_fase > 0)
        self.btn_sig.setEnabled(self.indice_fase < len(self.fases_disponibles) - 1)
        self.btn_ant.show()
        self.btn_sig.show()

    def mostrar_anterior(self):
        if self.indice_fase > 0:
            self.indice_fase -= 1
            self.actualizar_vista()

    def mostrar_siguiente(self):
        if self.indice_fase < len(self.fases_disponibles) - 1:
            self.indice_fase += 1
            self.actualizar_vista()

    def mostrar_comparativa(self):
        diag = DialogoComparativo(self.fases_disponibles, self.parent())
        diag.exec()

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            p_geom = self.parent().geometry()
            self.move(p_geom.x() + (p_geom.width() - self.width()) // 2, p_geom.y() + (p_geom.height() - self.height()) // 2)
        else:
            screen = QApplication.primaryScreen().geometry()
            self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)


class DialogoConfirmacion(QDialog):
    def __init__(self, titulo, mensaje, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.resultado = False
        
        from vistas.utilidades import set_app_icon
        set_app_icon(self)

        layout = QVBoxLayout(self)
        frame = QFrame(self)
        frame.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border-radius: 12px; border: 2px solid #cc0000; }
            QLabel { color: #333333; font-size: 15px; padding: 10px; border: none;}
            QPushButton { border-radius: 6px; font-weight: bold; padding: 8px 15px; font-size: 14px; }
            QPushButton#btn_eliminar { background-color: #cc0000; color: white; }
            QPushButton#btn_eliminar:hover { background-color: #aa0000; }
            QPushButton#btn_mantener { background-color: #e0e0e0; color: #333333; }
        """)

        flayout = QVBoxLayout(frame)
        lbl_titulo = QLabel(f"<b>{titulo}</b>")
        lbl_titulo.setStyleSheet("color: #cc0000; font-size: 18px; border: none;")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_mensaje = QLabel(mensaje)
        lbl_mensaje.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_mensaje.setWordWrap(True)

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

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            p_geom = self.parent().geometry()
            self.move(p_geom.x() + (p_geom.width() - self.width()) // 2, p_geom.y() + (p_geom.height() - self.height()) // 2)
        else:
            screen = QApplication.primaryScreen().geometry()
            self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def aceptar(self): self.resultado = True; self.accept()
    def cancelar(self): self.resultado = False; self.reject()

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
        self.current_tool = "pointer" 
        self.is_drawing = False
        self.draw_start_pos = None
        self.draw_current_pos = None
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
        if not self.original_pixmap or self.original_pixmap.isNull(): return None
        pix_w, pix_h = self.original_pixmap.width(), self.original_pixmap.height()
        lbl_w, lbl_h = self.width(), self.height()
        if lbl_w == 0 or lbl_h == 0: return None
        
        base_scale = min(lbl_w / pix_w, lbl_h / pix_h)
        actual_scale = base_scale * (self.zoom_level / 100.0)
        scaled_w = int(pix_w * actual_scale)
        scaled_h = int(pix_h * actual_scale)
        
        draw_x = (lbl_w - scaled_w) // 2 + self.pan_x
        draw_y = (lbl_h - scaled_h) // 2 + self.pan_y
        mx, my = mouse_pos.x(), mouse_pos.y()
        
        if draw_x <= mx <= draw_x + scaled_w and draw_y <= my <= draw_y + scaled_h:
            orig_x = (mx - draw_x) / actual_scale
            orig_y = (my - draw_y) / actual_scale
            return orig_x, orig_y
        return None

    def wheelEvent(self, event):
        if not self.original_pixmap or self.zoom_locked: return
        delta = event.angleDelta().y()
        if delta > 0: new_zoom = min(400, self.zoom_level + 15)
        else: new_zoom = max(50, self.zoom_level - 15)
        if new_zoom != self.zoom_level: self.set_zoom(new_zoom)

    def mousePressEvent(self, event):
        if not self.original_pixmap: return
        if event.button() == Qt.MouseButton.LeftButton:
            if self.current_tool == "pointer":
                if self.hovered_index != -1:
                    crop_path_base = self.boxes[self.hovered_index]["crop_path"]
                    crop_path = crop_path_base
                    pixmap_mem = None
                    if hasattr(self.window(), 'crops_filtrados_temp'):
                        nombre_base = os.path.basename(crop_path)
                        if self.view_mode == "Filtrada" or self.view_mode == "Previsualización":
                            arr = self.window().crops_filtrados_temp.get(nombre_base)
                            if arr is not None:
                                h, w = arr.shape
                                qimg = QImage(arr.data, w, h, w, QImage.Format.Format_Grayscale8)
                                pixmap_mem = QPixmap.fromImage(qimg)
                    
                    if self.view_mode == "Filtrada": crop_path = crop_path.replace("/crops/", "/filtradas/").replace("\\crops\\", "\\filtradas\\")
                    elif self.view_mode == "Esqueleto": crop_path = crop_path.replace("/crops/", "/esqueletos/").replace("\\crops\\", "\\esqueletos\\")

                    if os.path.exists(crop_path) or pixmap_mem:
                        DialogoVistaCelular(crop_path_base, pixmap_mem, self.view_mode, self.window()).exec()
                else:
                    self.is_panning = True
                    self.pan_start_pos = event.pos()
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
            elif self.current_tool == "draw":
                self.is_drawing = True
                self.draw_start_pos = event.pos()
                self.draw_current_pos = event.pos()
            elif self.current_tool == "delete":
                if self.hovered_index != -1:
                    index_to_delete = self.hovered_index
                    diag = DialogoConfirmacion("Eliminar Detección", "¿Estás seguro de descartar esta célula?")
                    diag.exec()
                    if diag.resultado:
                        if index_to_delete < len(self.boxes):
                            self.boxes.pop(index_to_delete)
                            self.hovered_index = -1
                            self.draw_current_state()
                            self.conteo_actualizado.emit(len(self.boxes))

    def mouseMoveEvent(self, event):
        if not self.original_pixmap: return
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
        if self.current_tool == "draw":
            if self.hovered_index != -1:
                self.hovered_index = -1
                self.draw_current_state()
            return
        if not self.boxes: return
        orig_coords = self.map_mouse_to_original(event.pos())
        new_hovered_index = -1
        if orig_coords:
            ox, oy = orig_coords
            for i in range(len(self.boxes)-1, -1, -1):
                box = self.boxes[i]
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
                    x1, y1 = orig_start; x2, y2 = orig_end
                    x = min(x1, x2); y = min(y1, y2)
                    w = abs(x2 - x1); h = abs(y2 - y1)
                    if w >= MIN_MICROGLIA_SIZE and h >= MIN_MICROGLIA_SIZE: self.nueva_caja_dibujada.emit(int(x), int(y), int(w), int(h))
                self.draw_start_pos = None; self.draw_current_pos = None
                self.draw_current_state()

    def leaveEvent(self, event):
        if self.hovered_index != -1:
            self.hovered_index = -1
            self.draw_current_state()
        super().leaveEvent(event)

    def set_zoom(self, value):
        if not self.original_pixmap or self.original_pixmap.isNull(): return
        if not self.zoom_locked: self.zoom_level = value; self.draw_current_state(); self.nivel_zoom_cambiado.emit(value)

    def lock_zoom(self, locked): self.zoom_locked = locked

    def draw_current_state(self):
        """Dibuja la imagen, las cajas normales y la caja resaltada."""
        if not self.original_pixmap or self.original_pixmap.isNull():
            self._current_pixmap = None
            self.update()
            return
        pix_w, pix_h = self.original_pixmap.width(), self.original_pixmap.height()
        lbl_w, lbl_h = self.width(), self.height()
        if lbl_w == 0 or lbl_h == 0: return
        
        base_scale = min(lbl_w / pix_w, lbl_h / pix_h)
        actual_scale = base_scale * (self.zoom_level / 100.0)
        scaled_w = int(pix_w * actual_scale)
        scaled_h = int(pix_h * actual_scale)
        if scaled_w == 0 or scaled_h == 0: return
        
        scaled_pix = self.original_pixmap.scaled(scaled_w, scaled_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        temp_pixmap = scaled_pix.copy()
        painter = QPainter(temp_pixmap)
        
        for i, box in enumerate(self.boxes):
            rect = QRect(int(box["x"] * actual_scale), int(box["y"] * actual_scale), int(box["w"] * actual_scale), int(box["h"] * actual_scale))
            if i == self.hovered_index and self.current_tool != "draw":
                pen = QPen(QColor(0, 255, 0)) 
                pen.setWidth(max(2, int(pix_w * 0.003 * actual_scale)))
            else:
                pen = QPen(QColor(0, 255, 0, 120))
                pen.setWidth(max(1, int(pix_w * 0.0015 * actual_scale)))
                
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            
        if self.is_drawing and self.draw_start_pos and self.draw_current_pos:
            orig_start = self.map_mouse_to_original(self.draw_start_pos); orig_end = self.map_mouse_to_original(self.draw_current_pos)
            if orig_start and orig_end:
                ox1, oy1 = orig_start; ox2, oy2 = orig_end
                rx = min(ox1, ox2); ry = min(oy1, oy2); rw = abs(ox2 - ox1); rh = abs(oy2 - oy1)
                pen_draw = QPen(QColor(0, 150, 255)); pen_draw.setWidth(max(2, int(pix_w * 0.003 * actual_scale))); painter.setPen(pen_draw); painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(int(rx * actual_scale), int(ry * actual_scale), int(rw * actual_scale), int(rh * actual_scale))
                
        painter.end()
        self._current_pixmap = temp_pixmap; self.update()

    def paintEvent(self, event):
        if self._current_pixmap and not self._current_pixmap.isNull():
            painter = QPainter(self)
            x = (self.width() - self._current_pixmap.width()) // 2 + self.pan_x
            y = (self.height() - self._current_pixmap.height()) // 2 + self.pan_y
            painter.drawPixmap(x, y, self._current_pixmap); painter.end()
        else: super().paintEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.original_pixmap: self.draw_current_state()

class DialogoOpcionesReporte(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.resultado = None
        
        from vistas.utilidades import set_app_icon
        set_app_icon(self)

        layout = QVBoxLayout(self)
        frame = QFrame(self)
        frame.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border-radius: 12px; border: 2px solid #003366; }
            QLabel { color: #333333; font-size: 15px; padding: 10px; border: none;}
            QPushButton { border-radius: 6px; font-weight: bold; padding: 8px 15px; font-size: 14px; }
            QPushButton#btn_agregar { background-color: #28a745; color: white; }
            QPushButton#btn_agregar:hover { background-color: #218838; }
            QPushButton#btn_finalizar { background-color: #007bff; color: white; }
            QPushButton#btn_finalizar:hover { background-color: #0069d9; }
            QPushButton#btn_cancelar { background-color: #e0e0e0; color: #333333; }
        """)

        flayout = QVBoxLayout(frame)
        lbl_titulo = QLabel("<b>Métricas Extraídas</b>")
        lbl_titulo.setStyleSheet("color: #003366; font-size: 18px; border: none;")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_mensaje = QLabel("Métricas extraídas exitosamente y añadidas al reporte actual.\n¿Qué deseas hacer a continuación?")
        lbl_mensaje.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_mensaje.setWordWrap(True)

        btn_layout = QHBoxLayout()
        btn_agregar = QPushButton("Agregar otra imagen")
        btn_agregar.setObjectName("btn_agregar")
        btn_agregar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_agregar.clicked.connect(self.agregar)

        btn_finalizar = QPushButton("Finalizar reporte")
        btn_finalizar.setObjectName("btn_finalizar")
        btn_finalizar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_finalizar.clicked.connect(self.finalizar)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btn_cancelar")
        btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancelar.clicked.connect(self.cancelar)

        btn_layout.addWidget(btn_agregar)
        btn_layout.addWidget(btn_finalizar)
        btn_layout.addWidget(btn_cancelar)

        flayout.addWidget(lbl_titulo)
        flayout.addWidget(lbl_mensaje)
        flayout.addLayout(btn_layout)
        layout.addWidget(frame)
        self.setLayout(layout)

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            p_geom = self.parent().geometry()
            self.move(p_geom.x() + (p_geom.width() - self.width()) // 2, p_geom.y() + (p_geom.height() - self.height()) // 2)
        else:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().geometry()
            self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def agregar(self): self.resultado = "agregar"; self.accept()
    def finalizar(self): self.resultado = "finalizar"; self.accept()
    def cancelar(self): self.resultado = "cancelar"; self.reject()


class VentanaInvestigador(QMainWindow):
    def mostrar_notificacion(self, titulo, mensaje, tipo="info"):
        from vistas.utilidades import DialogoNotificacion
        DialogoNotificacion(titulo, mensaje, tipo, self).exec()

    def __init__(self, id_usuario, rol):
        super().__init__()
        self.id_usuario = id_usuario; self.rol = rol
        self.ruta_imagen_actual = None
        self.pixmaps_globales = {"Original": None, "Filtrada": None, "Esqueleto": None}
        self.crops_en_memoria = {}
        self.crops_filtrados_temp = {}
        self.metadatos_imagen = {"campo": "", "tiempo": ""}
        self.metricas_reporte = []
        self.setWindowTitle(f"Prototipo Microglías - Panel ({self.rol})")
        
        from vistas.utilidades import set_app_icon
        set_app_icon(self)
        
        screen_geom = QApplication.primaryScreen().geometry()
        self.resize(int(screen_geom.width() * 0.8), int(screen_geom.height() * 0.8))
        self.setMinimumSize(1050, 700)
        self.inicializar_ui()

    def inicializar_ui(self):
        widget_central = QWidget(); layout_principal = QHBoxLayout()
        menu_lateral = QVBoxLayout(); menu_lateral.setAlignment(Qt.AlignmentFlag.AlignTop)
        label_bienvenida = QLabel(f"Sesión: {self.rol}"); label_bienvenida.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 20px;"); menu_lateral.addWidget(label_bienvenida)
        self.btn_cargar = QPushButton("Cargar Imagen"); self.btn_historial = QPushButton("Historial"); label_caract = QLabel("Caracterización:"); label_caract.setStyleSheet("font-weight: bold; margin-top: 15px;")
        self.btn_conteo = QPushButton("1. Aplicar Conteo"); self.btn_filtrar = QPushButton("2. Aplicar Filtrado"); self.btn_ramas = QPushButton("3. Mostrar Ramas"); label_reporte = QLabel("Reportes:"); label_reporte.setStyleSheet("font-weight: bold; margin-top: 15px;")
        self.btn_reporte = QPushButton("Generar Reporte"); self.btn_guardar_img = QPushButton("Guardar Imagen")
        estilo_btn_menu = "QPushButton { background-color: transparent; text-align: left; padding: 10px; font-weight: normal; color: #333333; border: none;} QPushButton:hover { background-color: #F0F0F0; border-radius: 5px; } QPushButton:disabled { color: #aaaaaa; }"
        for btn in [self.btn_cargar, self.btn_historial, self.btn_conteo, self.btn_filtrar, self.btn_ramas, self.btn_reporte, self.btn_guardar_img]: btn.setStyleSheet(estilo_btn_menu); menu_lateral.addWidget(btn)
        
        self.frame_filtros = QFrame()
        self.frame_filtros.hide()
        layout_filtros = QVBoxLayout(self.frame_filtros)
        layout_filtros.setContentsMargins(0, 10, 0, 10)
        lbl_f_titulo = QLabel("Ajuste de Filtros"); lbl_f_titulo.setStyleSheet("font-weight: bold; color: #003366;")
        layout_filtros.addWidget(lbl_f_titulo)
        lbl_clahe = QLabel("Contraste (CLAHE):")
        self.sld_clahe = QSlider(Qt.Orientation.Horizontal); self.sld_clahe.setRange(0, 10); self.sld_clahe.setValue(2)
        layout_filtros.addWidget(lbl_clahe); layout_filtros.addWidget(self.sld_clahe)
        lbl_gauss = QLabel("Suavizado Gaussiano:")
        self.sld_gauss = QSlider(Qt.Orientation.Horizontal); self.sld_gauss.setRange(1, 15); self.sld_gauss.setSingleStep(2); self.sld_gauss.setValue(5)
        layout_filtros.addWidget(lbl_gauss); layout_filtros.addWidget(self.sld_gauss)
        lbl_otsu = QLabel("Umbral Binarización:")
        self.sld_otsu = QSlider(Qt.Orientation.Horizontal); self.sld_otsu.setRange(-50, 50); self.sld_otsu.setValue(0)
        layout_filtros.addWidget(lbl_otsu); layout_filtros.addWidget(self.sld_otsu)
        btn_aceptar_filtro = QPushButton("Aceptar"); btn_aceptar_filtro.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 5px;")
        btn_cancelar_filtro = QPushButton("Cancelar"); btn_cancelar_filtro.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 5px;")
        layout_filtros.addWidget(btn_aceptar_filtro); layout_filtros.addWidget(btn_cancelar_filtro)
        menu_lateral.addWidget(self.frame_filtros)
        
        self.sld_clahe.valueChanged.connect(self.previsualizar_filtrado)
        self.sld_gauss.valueChanged.connect(self.previsualizar_filtrado)
        self.sld_otsu.valueChanged.connect(self.previsualizar_filtrado)
        btn_aceptar_filtro.clicked.connect(self.confirmar_filtrado)
        btn_cancelar_filtro.clicked.connect(self.cancelar_filtrado)

        menu_lateral.addStretch()
        self.btn_cerrar_sesion = QPushButton("Cerrar Sesión"); self.btn_cerrar_sesion.setStyleSheet("QPushButton { background-color: transparent; border: 2px solid #cc0000; color: #cc0000; font-weight: bold; border-radius: 8px; padding: 10px; margin-top: 20px; } QPushButton:hover { background-color: #cc0000; color: white; }"); menu_lateral.addWidget(self.btn_cerrar_sesion)
        frame_menu = QFrame(); frame_menu.setObjectName("menu_lateral"); frame_menu.setFixedWidth(200); frame_menu.setLayout(menu_lateral)
        
        area_imagen = QVBoxLayout(); controles_superiores = QHBoxLayout()
        self.combo_vista = QComboBox(); self.combo_vista.addItem("Original"); self.combo_vista.setMinimumWidth(160); self.combo_vista.setStyleSheet("padding: 5px; font-size: 13px; font-weight: bold; min-width: 160px;"); self.combo_vista.setEnabled(False); self.combo_vista.currentTextChanged.connect(self.cambiar_vista_global)
        
        # Botones de navegación global
        self.btn_ant_global = QPushButton("<")
        self.btn_ant_global.setFixedSize(30, 30)
        self.btn_ant_global.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ant_global.setStyleSheet("QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; font-weight: bold; color: #003366; } QPushButton:hover { background-color: #e0e0e0; } QPushButton:disabled { color: #ccc; }")
        self.btn_ant_global.clicked.connect(self.anterior_vista_global)
        self.btn_ant_global.hide()
        
        self.btn_sig_global = QPushButton(">")
        self.btn_sig_global.setFixedSize(30, 30)
        self.btn_sig_global.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sig_global.setStyleSheet("QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; font-weight: bold; color: #003366; } QPushButton:hover { background-color: #e0e0e0; } QPushButton:disabled { color: #ccc; }")
        self.btn_sig_global.clicked.connect(self.siguiente_vista_global)
        self.btn_sig_global.hide()
        
        controles_superiores.addWidget(self.btn_ant_global)
        controles_superiores.addWidget(self.combo_vista)
        controles_superiores.addWidget(self.btn_sig_global)
        controles_superiores.addStretch()
        
        self.lbl_info_conteo = QLabel("Microglías detectadas: 0"); self.lbl_info_conteo.setStyleSheet("font-size: 15px; font-weight: bold; color: #003366;"); self.lbl_info_conteo.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter); controles_superiores.addWidget(self.lbl_info_conteo); controles_superiores.addSpacing(15)
        
        estilo_herramienta = "QPushButton { background-color: transparent; border: none; padding: 2px; } QPushButton:hover { background-color: #e0e0e0; border-radius: 4px; } QPushButton:checked { background-color: #cce5ff; border: 1px solid #007bff; border-radius: 4px; } QPushButton:disabled { opacity: 0.5; }"
        
        self.btn_herramienta_caja = SafeToolTipButton()
        self.btn_herramienta_caja.setIcon(QIcon("assets/seleccionar.png"))
        self.btn_herramienta_caja.setIconSize(QSize(28, 28))
        self.btn_herramienta_caja.setCustomToolTip("Crear seleccion")
        self.btn_herramienta_caja.setStyleSheet(estilo_herramienta)
        self.btn_herramienta_caja.setCheckable(True)
        self.btn_herramienta_caja.setEnabled(False)
        self.btn_herramienta_caja.hide() 
        
        self.btn_herramienta_eliminar = SafeToolTipButton()
        self.btn_herramienta_eliminar.setIcon(QIcon("assets/borrar.png"))
        self.btn_herramienta_eliminar.setIconSize(QSize(28, 28))
        self.btn_herramienta_eliminar.setCustomToolTip("Eliminar seleccion")
        self.btn_herramienta_eliminar.setStyleSheet(estilo_herramienta)
        self.btn_herramienta_eliminar.setCheckable(True)
        self.btn_herramienta_eliminar.setEnabled(False)
        self.btn_herramienta_eliminar.hide()
        
        self.btn_herramienta_caja.clicked.connect(self.toggle_herramienta_caja)
        self.btn_herramienta_eliminar.clicked.connect(self.toggle_herramienta_eliminar)

        controles_superiores.addWidget(self.btn_herramienta_caja); controles_superiores.addWidget(self.btn_herramienta_eliminar); controles_superiores.addSpacing(15)
        
        lbl_minus = QLabel("-"); lbl_minus.setStyleSheet("font-size: 24px; font-weight: bold; color: #555;"); lbl_plus = QLabel("+"); lbl_plus.setStyleSheet("font-size: 20px; font-weight: bold; color: #555;")
        self.sld_nivel_zoom = QSlider(Qt.Orientation.Horizontal); self.sld_nivel_zoom.setRange(50, 400); self.sld_nivel_zoom.setValue(100); self.sld_nivel_zoom.setFixedWidth(120); self.sld_nivel_zoom.setEnabled(False)
        
        self.btn_zoom_reset = QPushButton("Reset")
        self.btn_zoom_reset.setStyleSheet("QPushButton { background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 4px; padding: 4px 10px; font-weight: bold; color:#007bff;} QPushButton:hover { background-color: #e0e0e0; } QPushButton:disabled { color:#aaa; }")
        self.btn_zoom_reset.setEnabled(False)
        
        self.btn_bloquear_zoom = SafeToolTipButton()
        self.btn_bloquear_zoom.setIcon(QIcon("assets/desbloqueado.png"))
        self.btn_bloquear_zoom.setIconSize(QSize(24, 24))
        self.btn_bloquear_zoom.setCustomToolTip("Bloquear zoom")
        self.btn_bloquear_zoom.setStyleSheet(estilo_herramienta)
        self.btn_bloquear_zoom.setCheckable(True)
        self.btn_bloquear_zoom.setEnabled(False)
        self.btn_bloquear_zoom.toggled.connect(self.toggle_bloqueo_zoom)
        
        controles_superiores.addWidget(lbl_minus); controles_superiores.addWidget(self.sld_nivel_zoom); controles_superiores.addWidget(lbl_plus); controles_superiores.addSpacing(5); controles_superiores.addWidget(self.btn_zoom_reset); controles_superiores.addWidget(self.btn_bloquear_zoom)
        
        self.visor_imagen = InteractiveImageViewer(); self.visor_imagen.setText("Sube una imagen .tiff para empezar el análisis..."); self.visor_imagen.setStyleSheet("border: 2px dashed #aaa; background-color: #f0f0f0; font-size: 18px; color: #666;")
        self.visor_imagen.conteo_actualizado.connect(self.actualizar_etiqueta_conteo); self.visor_imagen.nueva_caja_dibujada.connect(self.agregar_microglia_manual); self.visor_imagen.nivel_zoom_cambiado.connect(self.sld_nivel_zoom.setValue)
        self.sld_nivel_zoom.valueChanged.connect(self.visor_imagen.set_zoom); self.btn_zoom_reset.clicked.connect(self.reset_zoom)
        
        area_imagen.addLayout(controles_superiores); area_imagen.addWidget(self.visor_imagen, stretch=1)
        layout_principal.addWidget(frame_menu); layout_principal.addLayout(area_imagen, stretch=1); widget_central.setLayout(layout_principal); self.setCentralWidget(widget_central)
        
        self.btn_cargar.clicked.connect(self.cargar_imagen); self.btn_cerrar_sesion.clicked.connect(self.cerrar_sesion); self.btn_conteo.clicked.connect(self.execute_microglia_counting); self.btn_filtrar.clicked.connect(self.ejecutar_filtrado); self.btn_ramas.clicked.connect(self.mostrar_ramas_morfologia); self.btn_reporte.clicked.connect(self.generar_reporte)
        self.actualizar_estado_flujo(0)
        
        if self.rol == "Invitado" or self.rol == "Guest": self.btn_historial.hide(); self.btn_guardar_img.hide()

    def toggle_herramienta_caja(self, checked):
        if checked: self.btn_herramienta_eliminar.setChecked(False); self.visor_imagen.current_tool = "draw"; self.visor_imagen.hovered_index = -1; self.visor_imagen.draw_current_state()
        else: self.visor_imagen.current_tool = "pointer"

    def toggle_herramienta_eliminar(self, checked):
        if checked: self.btn_herramienta_caja.setChecked(False); self.visor_imagen.current_tool = "delete"
        else: self.visor_imagen.current_tool = "pointer"

    def reset_zoom(self): self.sld_nivel_zoom.setValue(100); self.visor_imagen.pan_x = 0; self.visor_imagen.pan_y = 0; self.visor_imagen.update()

    def toggle_bloqueo_zoom(self, checked):
        if checked:
            self.btn_bloquear_zoom.setIcon(QIcon("assets/bloqueado.png"))
            self.btn_bloquear_zoom.setCustomToolTip("Desbloquear zoom")
        else:
            self.btn_bloquear_zoom.setIcon(QIcon("assets/desbloqueado.png"))
            self.btn_bloquear_zoom.setCustomToolTip("Bloquear zoom")
            
        self.sld_nivel_zoom.setEnabled(not checked); self.btn_zoom_reset.setEnabled(not checked); self.visor_imagen.lock_zoom(checked)

    def actualizar_estado_flujo(self, paso):
        if paso == 0:
            self.btn_cargar.setEnabled(True); self.btn_conteo.setEnabled(False); self.btn_filtrar.setEnabled(False); self.btn_ramas.setEnabled(False); self.btn_reporte.setEnabled(False); self.btn_guardar_img.setEnabled(False); self.combo_vista.setEnabled(False)
            self.btn_herramienta_caja.hide(); self.btn_herramienta_eliminar.hide()
        elif paso == 1:
            self.btn_cargar.setEnabled(True); self.btn_conteo.setEnabled(True); self.btn_filtrar.setEnabled(False); self.btn_ramas.setEnabled(False); self.btn_reporte.setEnabled(False); self.btn_guardar_img.setEnabled(True); self.combo_vista.setEnabled(False)
            self.btn_herramienta_caja.hide(); self.btn_herramienta_eliminar.hide()
        elif paso == 2:
            self.btn_cargar.setEnabled(False); self.btn_conteo.setEnabled(False); self.btn_filtrar.setEnabled(True); self.btn_ramas.setEnabled(False); self.combo_vista.setEnabled(True)
            self.btn_herramienta_caja.show(); self.btn_herramienta_eliminar.show()
            self.btn_herramienta_caja.setEnabled(True); self.btn_herramienta_eliminar.setEnabled(True)
            self.sld_nivel_zoom.setEnabled(True); self.btn_zoom_reset.setEnabled(True); self.btn_bloquear_zoom.setEnabled(True)
        elif paso == 3:
            self.btn_cargar.setEnabled(False); self.btn_conteo.setEnabled(False); self.btn_filtrar.setEnabled(False); self.btn_ramas.setEnabled(True)
            self.btn_herramienta_caja.hide(); self.btn_herramienta_caja.setChecked(False)
            self.btn_herramienta_eliminar.hide(); self.btn_herramienta_eliminar.setChecked(False)
            self.visor_imagen.current_tool = "pointer"
        elif paso == 4:
            self.btn_cargar.setEnabled(True); self.btn_conteo.setEnabled(False); self.btn_filtrar.setEnabled(False); self.btn_ramas.setEnabled(False); self.btn_reporte.setEnabled(True)
            self.btn_herramienta_caja.hide(); self.btn_herramienta_eliminar.hide()

    def actualizar_etiqueta_conteo(self, conteo): self.lbl_info_conteo.setText(f"Microglías detectadas: {conteo}")

    def cargar_imagen(self):
        dialogo_intermedio = DialogoCargarImagen(self)
        if dialogo_intermedio.exec():
            ruta_archivo = dialogo_intermedio.ruta_seleccionada
            campo = dialogo_intermedio.campo_val
            tiempo = dialogo_intermedio.tiempo_val
            
            # Check for duplicates in current session report
            for item in self.metricas_reporte:
                if item["campo"] == campo and item["tiempo"] == tiempo:
                    from vistas.utilidades import DialogoConfirmacion
                    diag = DialogoConfirmacion("Advertencia de Duplicado", f"Ya existen métricas guardadas para el Campo '{campo}' y Tiempo '{tiempo}'.\n\n¿Deseas continuar de todos modos?")
                    if not diag.exec():
                        return # User cancelled
                    break
                    
            self.metadatos_imagen["campo"] = campo; self.metadatos_imagen["tiempo"] = tiempo
            if ruta_archivo:
                self.ruta_imagen_actual = ruta_archivo; pixmap = QPixmap(ruta_archivo)
                if pixmap.isNull():
                    try:
                        import cv2; import numpy as np
                        cv_img = cv2.imread(ruta_archivo, cv2.IMREAD_UNCHANGED)
                        if cv_img is not None:
                            if cv_img.dtype == np.uint16: cv_img = ((cv_img - cv_img.min()) / (cv_img.max() - cv_img.min()) * 255).astype(np.uint8)
                            if len(cv_img.shape) == 2: h, w = cv_img.shape; qimg = QImage(cv_img.data, w, h, w, QImage.Format.Format_Grayscale8)
                            else: cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB); h, w, ch = cv_img.shape; qimg = QImage(cv_img.data, w, h, ch * w, QImage.Format.Format_RGB888)
                            pixmap = QPixmap.fromImage(qimg)
                    except Exception as e: logging.error(f"Error al cargar imagen: {e}")
                if not pixmap.isNull():
                    self.pixmaps_globales["Original"] = pixmap; self.pixmaps_globales["Filtrada"] = None; self.pixmaps_globales["Esqueleto"] = None; self.btn_herramienta_caja.setChecked(False); self.btn_herramienta_eliminar.setChecked(False); self.visor_imagen.current_tool = "pointer"; self.btn_bloquear_zoom.setChecked(False); self.reset_zoom(); self.visor_imagen.set_image_and_boxes(pixmap, []); self.actualizar_estado_flujo(1); self.combo_vista.blockSignals(True); self.combo_vista.clear(); self.combo_vista.addItem("Original"); self.combo_vista.setCurrentText("Original"); self.combo_vista.blockSignals(False); self.visor_imagen.view_mode = "Original"; self.mostrar_notificacion("Imagen cargada", "Imagen lista para el análisis.", "info")
                else: self.mostrar_notificacion("Error", "El archivo está corrupto o no es válido.", "error")

    def cambiar_vista_global(self, texto_vista):
        pixmap_guardado = self.pixmaps_globales.get(texto_vista)
        if pixmap_guardado:
            self.visor_imagen.set_view_mode(texto_vista, pixmap_guardado)
            # Actualizar botones de navegación global (ocultar si no hay a donde ir)
            idx = self.combo_vista.currentIndex()
            if idx > 0: self.btn_ant_global.show()
            else: self.btn_ant_global.hide()
            
            if idx < self.combo_vista.count() - 1: self.btn_sig_global.show()
            else: self.btn_sig_global.hide()
        else:
            self.mostrar_notificacion("Aviso", f"Aún no has generado el paso: {texto_vista}.", "warning")
            self.combo_vista.blockSignals(True)
            self.combo_vista.setCurrentText(self.visor_imagen.view_mode)
            self.combo_vista.blockSignals(False)

    def anterior_vista_global(self):
        idx = self.combo_vista.currentIndex()
        if idx > 0:
            self.combo_vista.setCurrentIndex(idx - 1)

    def siguiente_vista_global(self):
        idx = self.combo_vista.currentIndex()
        if idx < self.combo_vista.count() - 1:
            self.combo_vista.setCurrentIndex(idx + 1)

    def cerrar_sesion(self):
        from vistas.login import VentanaLogin
        self.ventana_login = VentanaLogin(); self.ventana_login.setObjectName("ventana_login"); self.ventana_login.show(); self.close()

    def execute_microglia_counting(self):
        if not self.ruta_imagen_actual: self.mostrar_notificacion("Advertencia", "Por favor, carga una imagen primero.", "warning"); return
        dialogo = DialogoCarga("Cargando IA y aplicando conteo...\nPor favor, espera.", self); dialogo.show()
        from PyQt6.QtWidgets import QApplication; QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor); QApplication.processEvents()
        try:
            from ia.modelo_yolo import MicrogliaProcessor
            model_path = os.path.join(os.getcwd(), "ia", "entrenamiento_resultados", "modelo_microglias5", "weights", "best.pt"); output_dir = os.path.join(os.getcwd(), "analisis_resultados")
            processor = MicrogliaProcessor(model_path=model_path); resultado = processor.process_and_crop(self.ruta_imagen_actual, base_output_folder=output_dir)
            if len(resultado) == 3: crops_folder, count, boxes_data = resultado; self.visor_imagen.set_image_and_boxes(self.pixmaps_globales["Original"], boxes_data)
            else: crops_folder, count = resultado; self.visor_imagen.set_image_and_boxes(self.pixmaps_globales["Original"], [])
            dialogo.close(); QApplication.restoreOverrideCursor(); self.actualizar_estado_flujo(2); self.mostrar_notificacion("1. Conteo completado", f"Se detectaron {count} posibles microglías.\n\nUsa las herramientas superiores si necesitas agregar o eliminar selecciones.", "info")
        except Exception as e: dialogo.close(); QApplication.restoreOverrideCursor(); self.mostrar_notificacion("Error", str(e), "error")

    def agregar_microglia_manual(self, x, y, w, h):
        if not self.ruta_imagen_actual: return
        area_nueva = w * h
        for box in self.visor_imagen.boxes:
            bx, by, bw, bh = box["x"], box["y"], box["w"], box["h"]; ix1 = max(x, bx); iy1 = max(y, by); ix2 = min(x + w, bx + bw); iy2 = min(y + h, by + bh); iw_inter = max(0, ix2 - ix1); ih_inter = max(0, iy2 - iy1); inter_area = iw_inter * ih_inter
            if inter_area > 0:
                ioa_nueva = inter_area / area_nueva; ioa_existente = inter_area / (bw * bh)
                if ioa_nueva >= 0.40 or ioa_existente >= 0.40: self.mostrar_notificacion("Acción bloqueada", "No puedes crear una microglía que esté contenida dentro de otra existente o que se superponga fuertemente.", "warning"); return
        base_name = Path(self.ruta_imagen_actual).stem; crops_folder = os.path.join(os.getcwd(), "analisis_resultados", base_name, "crops"); os.makedirs(crops_folder, exist_ok=True)
        orig_pixmap = self.pixmaps_globales["Original"]
        if not orig_pixmap: return
        rect_recorte = QRect(x, y, w, h); pixmap_recorte = orig_pixmap.copy(rect_recorte); nombre_archivo = f"manual_{uuid.uuid4().hex[:6]}.png"; ruta_guardado = os.path.join(crops_folder, nombre_archivo); pixmap_recorte.save(ruta_guardado, "PNG")
        nueva_caja = {"x": x, "y": y, "w": w, "h": h, "crop_path": ruta_guardado}; self.visor_imagen.boxes.append(nueva_caja); self.visor_imagen.draw_current_state(); self.actualizar_etiqueta_conteo(len(self.visor_imagen.boxes))

    def construir_imagen_global(self, carpeta_origen):
        import cv2; import numpy as np
        orig_pixmap = self.pixmaps_globales["Original"]; orig_w = orig_pixmap.width(); orig_h = orig_pixmap.height(); lienzo = np.zeros((orig_h, orig_w), dtype=np.uint8); base_name = Path(self.ruta_imagen_actual).stem; base_dir = os.path.join(os.getcwd(), "analisis_resultados", base_name)
        for box in self.visor_imagen.boxes:
            x, y, w, h = int(box["x"]), int(box["y"]), int(box["w"]), int(box["h"]); nombre_archivo = os.path.basename(box["crop_path"]); ruta_recorte = os.path.join(base_dir, carpeta_origen, nombre_archivo)
            if os.path.exists(ruta_recorte):
                with open(ruta_recorte, "rb") as f: file_bytes = bytearray(f.read())
                img_array = np.asarray(file_bytes, dtype=np.uint8); recorte = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
                if recorte is not None: rh, rw = recorte.shape; y_fin = min(y + rh, orig_h); x_fin = min(x + rw, orig_w); h_real = y_fin - y; w_real = x_fin - x; lienzo[y:y_fin, x:x_fin] = recorte[:h_real, :w_real]
        qimg = QImage(lienzo.data, orig_w, orig_h, orig_w, QImage.Format.Format_Grayscale8).copy()
        return QPixmap.fromImage(qimg)

    def construir_imagen_global_memoria(self):
        import numpy as np
        orig_pixmap = self.pixmaps_globales["Original"]; orig_w = orig_pixmap.width(); orig_h = orig_pixmap.height(); lienzo = np.zeros((orig_h, orig_w), dtype=np.uint8)
        for box in self.visor_imagen.boxes:
            x, y, w, h = int(box["x"]), int(box["y"]), int(box["w"]), int(box["h"])
            nombre_archivo = os.path.basename(box["crop_path"])
            recorte = self.crops_filtrados_temp.get(nombre_archivo)
            if recorte is not None:
                rh, rw = recorte.shape; y_fin = min(y + rh, orig_h); x_fin = min(x + rw, orig_w); h_real = y_fin - y; w_real = x_fin - x
                lienzo[y:y_fin, x:x_fin] = recorte[:h_real, :w_real]
        qimg = QImage(lienzo.data, orig_w, orig_h, orig_w, QImage.Format.Format_Grayscale8).copy()
        return QPixmap.fromImage(qimg)

    def ejecutar_filtrado(self):
        if not self.ruta_imagen_actual or not self.visor_imagen.boxes: self.mostrar_notificacion("Advertencia", "Aplica el conteo primero.", "warning"); return
        import cv2; import numpy as np
        self.crops_en_memoria.clear()
        self.crops_filtrados_temp.clear()
        
        from PyQt6.QtWidgets import QApplication
        dialogo = DialogoCarga("Cargando imágenes a memoria...\nPor favor, espera.", self); dialogo.show(); QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor); QApplication.processEvents()
        
        for box in self.visor_imagen.boxes:
            crop_path = box["crop_path"]
            if os.path.exists(crop_path):
                with open(crop_path, "rb") as f: file_bytes = bytearray(f.read())
                img_array = np.asarray(file_bytes, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if img is not None:
                    nombre = os.path.basename(crop_path)
                    self.crops_en_memoria[nombre] = img
                    
        dialogo.close(); QApplication.restoreOverrideCursor()
        
        self.frame_filtros.show()
        for btn in [self.btn_cargar, self.btn_historial, self.btn_conteo, self.btn_filtrar, self.btn_ramas, self.btn_reporte, self.btn_guardar_img]: btn.setEnabled(False)
        self.combo_vista.setEnabled(True)
        items_combo = [self.combo_vista.itemText(i) for i in range(self.combo_vista.count())]
        if "Previsualización" not in items_combo:
            self.combo_vista.addItem("Previsualización")
        
        self.combo_vista.blockSignals(True)
        self.combo_vista.setCurrentText("Previsualización")
        self.combo_vista.blockSignals(False)
        self.visor_imagen.view_mode = "Previsualización"
        
        self.previsualizar_filtrado()

    def previsualizar_filtrado(self, *args):
        if not self.crops_en_memoria: return
        import cv2; import numpy as np
        clahe_clip = self.sld_clahe.value()
        k_val = self.sld_gauss.value()
        k = k_val if k_val % 2 != 0 else k_val + 1
        otsu_offset = self.sld_otsu.value()
        
        clahe = cv2.createCLAHE(clipLimit=float(clahe_clip), tileGridSize=(8, 8)) if clahe_clip > 0 else None
        
        for nombre, img in self.crops_en_memoria.items():
            if clahe is not None:
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                h_c, s_c, v_c = cv2.split(hsv)
                v_clahe = clahe.apply(v_c)
                hsv_clahe = cv2.merge((h_c, s_c, v_clahe))
                bgr_proc = cv2.cvtColor(hsv_clahe, cv2.COLOR_HSV2BGR)
            else:
                bgr_proc = img
                
            gray = cv2.cvtColor(bgr_proc, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (k, k), 0)
            ret, _ = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            threshold_val = max(0, min(255, ret + otsu_offset))
            _, bin_img = cv2.threshold(blur, threshold_val, 255, cv2.THRESH_BINARY)
            
            self.crops_filtrados_temp[nombre] = bin_img
            
        pixmap_filtrada = self.construir_imagen_global_memoria()
        self.pixmaps_globales["Previsualización"] = pixmap_filtrada
        self.visor_imagen.set_view_mode("Previsualización", pixmap_filtrada)

    def confirmar_filtrado(self):
        base_name = Path(self.ruta_imagen_actual).stem; filtradas_dir = os.path.join(os.getcwd(), "analisis_resultados", base_name, "filtradas"); os.makedirs(filtradas_dir, exist_ok=True); import cv2; count = 0
        from PyQt6.QtWidgets import QApplication
        try:
            dialogo = DialogoCarga("Guardando filtros aplicados...\nPor favor, espera.", self); dialogo.show(); QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor); QApplication.processEvents()
            for nombre, bin_img in self.crops_filtrados_temp.items():
                out_path = os.path.join(filtradas_dir, nombre)
                is_success, im_buf_arr = cv2.imencode(".png", bin_img)
                if is_success: im_buf_arr.tofile(out_path); count += 1
            dialogo.close(); QApplication.restoreOverrideCursor()
            
            if count > 0:
                self.pixmaps_globales["Filtrada"] = self.pixmaps_globales["Previsualización"]
                self.combo_vista.blockSignals(True)
                items_combo = [self.combo_vista.itemText(i) for i in range(self.combo_vista.count())]
                if "Filtrada" not in items_combo: self.combo_vista.addItem("Filtrada")
                idx = self.combo_vista.findText("Previsualización")
                if idx >= 0: self.combo_vista.removeItem(idx)
                self.combo_vista.setCurrentText("Filtrada")
                self.combo_vista.blockSignals(False)
                self.visor_imagen.view_mode = "Filtrada"
                
                self.frame_filtros.hide()
                self.actualizar_estado_flujo(3)
                self.mostrar_notificacion("2. Filtrado", f"Se aplicaron los filtros a {count} microglías.", "info")
            else: self.mostrar_notificacion("Error", "No se guardó ninguna imagen.", "error")
        except Exception as error: dialogo.close(); QApplication.restoreOverrideCursor(); self.mostrar_notificacion("Error", f"Falló el guardado: {str(error)}", "error")

    def cancelar_filtrado(self):
        self.crops_en_memoria.clear()
        self.crops_filtrados_temp.clear()
        self.frame_filtros.hide()
        
        self.combo_vista.blockSignals(True)
        idx = self.combo_vista.findText("Previsualización")
        if idx >= 0: self.combo_vista.removeItem(idx)
        self.combo_vista.setCurrentText("Original")
        self.combo_vista.blockSignals(False)
        self.cambiar_vista_global("Original")
        
        self.actualizar_estado_flujo(1) # Reactivate main buttons

    def mostrar_ramas_morfologia(self):
        if not self.ruta_imagen_actual or not self.visor_imagen.boxes: self.mostrar_notificacion("Advertencia", "Aplica el conteo y filtrado primero.", "warning"); return
        base_name = Path(self.ruta_imagen_actual).stem; filtradas_dir = os.path.join(os.getcwd(), "analisis_resultados", base_name, "filtradas"); esqueletos_dir = os.path.join(os.getcwd(), "analisis_resultados", base_name, "esqueletos"); os.makedirs(esqueletos_dir, exist_ok=True); import cv2; import numpy as np; from skimage.morphology import skeletonize
        from PyQt6.QtWidgets import QApplication; count = 0
        try:
            dialogo = DialogoCarga("Generando esqueletos topológicos...\nPor favor, espera.", self); dialogo.show(); QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor); QApplication.processEvents()
            for box in self.visor_imagen.boxes:
                crop_path = box["crop_path"]; nombre = os.path.basename(crop_path); fil_path = os.path.join(filtradas_dir, nombre)
                if os.path.exists(fil_path):
                    with open(fil_path, "rb") as f: file_bytes = bytearray(f.read())
                    img_array = np.asarray(file_bytes, dtype=np.uint8); img_raw = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
                    if img_raw is not None: _, bin_img = cv2.threshold(img_raw, 127, 255, cv2.THRESH_BINARY); img_bool = bin_img > 0; skeleton = skeletonize(img_bool); skeleton_img = (skeleton * 255).astype(np.uint8); out_path = os.path.join(esqueletos_dir, nombre); is_success, im_buf_arr = cv2.imencode(".png", skeleton_img)
                    if is_success: im_buf_arr.tofile(out_path); count += 1
            dialogo.close(); QApplication.restoreOverrideCursor()
            if count > 0: pixmap_esqueleto = self.construir_imagen_global("esqueletos"); self.pixmaps_globales["Esqueleto"] = pixmap_esqueleto; self.actualizar_estado_flujo(4); self.combo_vista.addItem("Esqueleto"); self.combo_vista.setCurrentText("Esqueleto"); self.mostrar_notificacion("3. Ramas Generadas", f"Se generaron {count} esqueletos topológicos.\n\nYa puedes avanzar a los Reportes o Cargar una imagen nueva.", "info")
            else: self.mostrar_notificacion("Advertencia", "No se generaron esqueletos. Verifica la carpeta de filtrado.", "warning")
        except Exception as error: dialogo.close(); QApplication.restoreOverrideCursor(); self.mostrar_notificacion("Error de Procesamiento", f"Falló el cálculo:\n{str(error)}", "error")

    def generar_reporte(self):
        if not self.ruta_imagen_actual or not self.visor_imagen.boxes:
            self.mostrar_notificacion("Advertencia", "No hay datos para extraer métricas.", "warning")
            return
            
        base_name = Path(self.ruta_imagen_actual).stem
        esqueletos_dir = os.path.join(os.getcwd(), "analisis_resultados", base_name, "esqueletos")
        
        if not os.path.exists(esqueletos_dir):
            self.mostrar_notificacion("Advertencia", "No se encontraron esqueletos generados.", "warning")
            return
            
        from ia.extract_microglia_metrics import extract_microglia_metrics
        from PyQt6.QtWidgets import QApplication, QFileDialog
        import logging
        
        dialogo = DialogoCarga("Extrayendo métricas morfológicas...\nPor favor, espera.", self)
        dialogo.show()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        
        metricas_imagen = []
        for box in self.visor_imagen.boxes:
            nombre = os.path.basename(box["crop_path"])
            out_path = os.path.join(esqueletos_dir, nombre)
            if os.path.exists(out_path):
                try:
                    met = extract_microglia_metrics(out_path)
                    metricas_imagen.append(met)
                except Exception as e:
                    logging.error(f"Error extrayendo métricas de {nombre}: {e}")
                    
        dialogo.close()
        QApplication.restoreOverrideCursor()
        
        if not metricas_imagen:
            self.mostrar_notificacion("Error", "No se pudieron extraer métricas de ninguna microglía.", "error")
            return
            
        self.metricas_reporte.append({
            "campo": self.metadatos_imagen.get("campo", ""),
            "tiempo": self.metadatos_imagen.get("tiempo", ""),
            "metricas": metricas_imagen
        })
        
        opciones = DialogoOpcionesReporte(self)
        opciones.exec()
        
        if opciones.resultado == "agregar":
            # Clean UI to load another image
            self.visor_imagen.set_image_and_boxes(None, [])
            self.ruta_imagen_actual = None
            self.pixmaps_globales = {"Original": None, "Filtrada": None, "Esqueleto": None}
            self.combo_vista.blockSignals(True)
            self.combo_vista.clear()
            self.combo_vista.blockSignals(False)
            self.actualizar_estado_flujo(0)
            self.mostrar_notificacion("Info", "Listo para cargar otra imagen y agregar al reporte.", "info")
            
        elif opciones.resultado == "finalizar":
            from datetime import datetime
            fecha_str = datetime.now().strftime("%Y%m%d_%H%M")
            default_name = f"Reporte_{fecha_str}.xlsx"
            
            filepath, filter_selected = QFileDialog.getSaveFileName(self, "Guardar Reporte", default_name, "Excel Files (*.xlsx);;PDF Files (*.pdf);;Both Formats (*.xlsx *.pdf)")
            if not filepath:
                # If cancel, metrics are still saved.
                return
                
            try:
                # Group by time (common for both formats)
                reporte_por_tiempo = {}
                for img_data in self.metricas_reporte:
                    t = str(img_data.get("tiempo", "X HORA")).upper()
                    if t not in reporte_por_tiempo:
                        reporte_por_tiempo[t] = []
                    reporte_por_tiempo[t].append(img_data)

                columnas_labels = [
                    "No.", "Lines", "Junction Points", "End Points", "Junction Voxels",
                    "Slab Voxels", "Avg. Branch Length", "Triple points", "Quadruple points",
                    "Max Branch Length", "Longest Shortest path"
                ]

                metric_keys = [
                    "lines", "junction points", "end points", "junction voxels",
                    "slab voxels", "average branch length", "triple points", "quadruple points",
                    "maximum branch length", "longest shortest path"
                ]

                save_xlsx = "Excel" in filter_selected or "Both" in filter_selected or filepath.endswith(".xlsx")
                save_pdf = "PDF" in filter_selected or "Both" in filter_selected or filepath.endswith(".pdf")

                # Handle XLSX generation
                if save_xlsx:
                    xlsx_path = filepath if filepath.endswith(".xlsx") else str(Path(filepath).with_suffix(".xlsx"))
                    import openpyxl
                    from openpyxl.styles import PatternFill, Font, Alignment
                    from openpyxl.utils import get_column_letter
                    wb = openpyxl.Workbook()
                    wb.remove(wb.active) 
                    
                    yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
                    header_bg_fill = PatternFill(start_color="3A61A0", end_color="3A61A0", fill_type="solid")
                    light_gray_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
                    bold_font = Font(bold=True)
                    header_black_font = Font(color="000000", bold=True)
                    center_alignment = Alignment(horizontal="center", vertical="center")
                    anchos_fijos = [9.3, 18.0, 22.6, 18.6, 22.6, 16.6, 26.6, 20.0, 26.6, 26.6, 32.0]
                    
                    for tiempo, lista_campos in reporte_por_tiempo.items():
                        ws = wb.create_sheet(title=tiempo[:31])
                        for col_idx, width in enumerate(anchos_fijos, start=1):
                            ws.column_dimensions[get_column_letter(col_idx)].width = width
                        
                        row_idx = 1
                        for img_data in lista_campos:
                            ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=len(columnas_labels))
                            for c in range(1, len(columnas_labels) + 1):
                                ws.cell(row=row_idx, column=c).fill = yellow_fill
                            
                            cell_title = ws.cell(row=row_idx, column=1, value=img_data['campo'])
                            cell_title.font = bold_font
                            cell_title.alignment = center_alignment
                            row_idx += 1
                            
                            for col_idx, label in enumerate(columnas_labels, start=1):
                                cell_h = ws.cell(row=row_idx, column=col_idx, value=label)
                                cell_h.font = header_black_font
                                cell_h.fill = header_bg_fill
                                cell_h.alignment = center_alignment
                            row_idx += 1
                            
                            for i, met in enumerate(img_data['metricas'], start=1):
                                cell_num = ws.cell(row=row_idx, column=1, value=i)
                                cell_num.alignment = center_alignment
                                for col_idx, key in enumerate(metric_keys, start=2):
                                    cell_m = ws.cell(row=row_idx, column=col_idx, value=met.get(key, ""))
                                    cell_m.alignment = center_alignment
                                if i % 2 != 0:
                                    for c in range(1, len(columnas_labels) + 1):
                                        ws.cell(row=row_idx, column=c).fill = light_gray_fill
                                row_idx += 1
                            row_idx += 1
                    wb.save(xlsx_path)

                # Handle PDF generation
                if save_pdf:
                    pdf_path = filepath if filepath.endswith(".pdf") else str(Path(filepath).with_suffix(".pdf"))
                    try:
                        from fpdf import FPDF
                    except ImportError:
                        if not save_xlsx: # Only error if PDF was the only target
                            self.mostrar_notificacion("Librería faltante", "Por favor instala fpdf2:\n'pip install fpdf2'", "error")
                            return
                        else:
                            logging.error("PDF generation skipped: fpdf2 not installed")
                    else:
                        class PDFReport(FPDF):
                            def header(self):
                                self.set_font('Arial', 'B', 14)
                                self.cell(0, 10, 'Reporte de Métricas Morfológicas - Microglías', 0, 1, 'C')
                                self.ln(5)

                        pdf = PDFReport(orientation='L', unit='mm', format='A4')
                        pdf.set_auto_page_break(auto=True, margin=15)
                        pdf_widths = [12, 22, 26, 22, 26, 20, 31, 23, 31, 31, 36] 

                        for tiempo, lista_campos in reporte_por_tiempo.items():
                            pdf.add_page()
                            pdf.set_font('Arial', 'B', 12)
                            pdf.cell(0, 10, f"TIEMPO: {tiempo}", 0, 1, 'L')
                            
                            for img_data in lista_campos:
                                pdf.set_fill_color(255, 255, 0)
                                pdf.set_font('Arial', 'B', 10)
                                pdf.cell(sum(pdf_widths), 8, f"Campo: {img_data['campo']}", 1, 1, 'C', True)
                                
                                pdf.set_fill_color(58, 97, 160)
                                pdf.set_text_color(0, 0, 0)
                                pdf.set_font('Arial', 'B', 7)
                                for i, label in enumerate(columnas_labels):
                                    pdf.cell(pdf_widths[i], 8, label, 1, 0, 'C', True)
                                pdf.ln()
                                
                                pdf.set_font('Arial', '', 9)
                                pdf.set_text_color(0, 0, 0)
                                for idx, met in enumerate(img_data['metricas'], start=1):
                                    if idx % 2 != 0: pdf.set_fill_color(242, 242, 242)
                                    else: pdf.set_fill_color(255, 255, 255)
                                    
                                    pdf.cell(pdf_widths[0], 7, str(idx), 1, 0, 'C', True)
                                    values = [
                                        str(met.get("lines", "")), str(met.get("junction points", "")),
                                        str(met.get("end points", "")), str(met.get("junction voxels", "")),
                                        str(met.get("slab voxels", "")), str(met.get("average branch length", "")),
                                        str(met.get("triple points", "")), str(met.get("quadruple points", "")),
                                        str(met.get("maximum branch length", "")), str(met.get("longest shortest path", ""))
                                    ]
                                    for i, val in enumerate(values):
                                        pdf.cell(pdf_widths[i+1], 7, val, 1, 0, 'C', True)
                                    pdf.ln()
                                pdf.ln(5)
                        pdf.output(pdf_path)

                self.metricas_reporte.clear()
                msg = f"Reporte guardado correctamente en:\n{filepath}"
                if "Both" in filter_selected: msg = "Ambos reportes (XLSX y PDF) han sido guardados."
                self.mostrar_notificacion("Éxito", msg, "success")
                
                # Reset UI completely
                self.visor_imagen.set_image_and_boxes(None, [])
                self.ruta_imagen_actual = None
                self.pixmaps_globales = {"Original": None, "Filtrada": None, "Esqueleto": None}
                self.combo_vista.blockSignals(True)
                self.combo_vista.clear()
                self.combo_vista.blockSignals(False)
                self.lbl_info_conteo.setText("Microglías detectadas: 0")
                self.actualizar_estado_flujo(0)
                
            except Exception as e:
                self.mostrar_notificacion("Error", f"Error al guardar el reporte: {str(e)}", "error")