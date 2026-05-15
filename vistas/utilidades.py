import sys
import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

def get_logo_path():
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, "assets", "logoW.png")

def set_app_icon(window):
    window.setWindowIcon(QIcon(get_logo_path()))

class DialogoNotificacion(QDialog):
    def __init__(self, titulo, mensaje, tipo="info", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        set_app_icon(self)

        layout = QVBoxLayout(self)
        frame = QFrame(self)
        
        color_titulo = "#0969da" # info (GitHub blue)
        if tipo == "warning": color_titulo = "#9a6700"
        elif tipo == "error": color_titulo = "#cf222e" # GitHub red
        
        frame.setStyleSheet(f"""
            QFrame {{ background-color: #FFFFFF; border-radius: 12px; border: 1px solid {color_titulo}; }}
            QLabel {{ color: #24292f; font-size: 13px; padding: 5px; border: none; }}
            QPushButton {{ background-color: #f6f8fa; color: #24292f; border: 1px solid #d0d7de; border-radius: 6px; padding: 6px 16px; font-weight: 600; font-size: 13px; }}
            QPushButton:hover {{ background-color: #f3f4f6; }}
        """)
        
        flayout = QVBoxLayout(frame)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 10, 10, 0)
        lbl_titulo = QLabel(f"<b>{titulo}</b>")
        lbl_titulo.setStyleSheet(f"color: {color_titulo}; font-size: 16px; border: none; font-weight: bold;")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(lbl_titulo)
        flayout.addLayout(header_layout)
        
        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setStyleSheet(f"background-color: {color_titulo}; border: none; max-height: 2px;")
        
        lbl_mensaje = QLabel(mensaje)
        lbl_mensaje.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_mensaje.setWordWrap(True)
        lbl_mensaje.setMargin(10)
        
        btn_layout = QHBoxLayout()
        btn_aceptar = QPushButton("Aceptar")
        btn_aceptar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_aceptar.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_aceptar)
        btn_layout.addStretch()
        
        flayout.addWidget(lbl_titulo)
        flayout.addWidget(linea)
        flayout.addWidget(lbl_mensaje)
        flayout.addLayout(btn_layout)
        layout.addWidget(frame)
        self.setLayout(layout)
        self.setMinimumWidth(450)

    def showEvent(self, event):
        from PyQt6.QtWidgets import QApplication
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
        set_app_icon(self)

        layout = QVBoxLayout(self)
        frame = QFrame(self)
        frame.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border-radius: 12px; border: 1px solid #cf222e; }
            QLabel { color: #24292f; font-size: 13px; padding: 5px; border: none;}
            QPushButton { border-radius: 6px; font-weight: 600; padding: 6px 15px; font-size: 13px; border: 1px solid #d0d7de; }
            QPushButton#btn_eliminar { background-color: #cf222e; color: white; border-color: #a40e26; }
            QPushButton#btn_eliminar:hover { background-color: #a40e26; }
            QPushButton#btn_mantener { background-color: #f6f8fa; color: #24292f; }
            QPushButton#btn_mantener:hover { background-color: #f3f4f6; }
        """)

        flayout = QVBoxLayout(frame)
        lbl_titulo = QLabel(f"<b>{titulo}</b>")
        lbl_titulo.setStyleSheet("color: #cf222e; font-size: 16px; border: none; font-weight: bold;")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setStyleSheet("background-color: #cc0000; border: none; max-height: 4px;")

        lbl_mensaje = QLabel(mensaje)
        lbl_mensaje.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_mensaje.setWordWrap(True)
        lbl_mensaje.setMargin(10)

        btn_layout = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btn_mantener")
        btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancelar.clicked.connect(self.cancelar)

        btn_aceptar = QPushButton("Confirmar")
        btn_aceptar.setObjectName("btn_eliminar")
        btn_aceptar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_aceptar.clicked.connect(self.aceptar)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_aceptar)
        btn_layout.addStretch()

        flayout.addWidget(lbl_titulo)
        flayout.addWidget(linea)
        flayout.addWidget(lbl_mensaje)
        flayout.addLayout(btn_layout)
        layout.addWidget(frame)
        self.setLayout(layout)
        self.setMinimumWidth(450)

    def aceptar(self): self.resultado = True; self.accept()
    def cancelar(self): self.resultado = False; self.reject()

    def showEvent(self, event):
        from PyQt6.QtWidgets import QApplication
        super().showEvent(event)
        if self.parent():
            p_geom = self.parent().geometry()
            self.move(p_geom.x() + (p_geom.width() - self.width()) // 2, p_geom.y() + (p_geom.height() - self.height()) // 2)
        else:
            screen = QApplication.primaryScreen().geometry()
            self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)
