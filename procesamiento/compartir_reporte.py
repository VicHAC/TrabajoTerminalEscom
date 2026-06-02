"""
procesamiento/compartir_reporte.py
====================================
Módulo que centraliza la lógica de base de datos y la interfaz
para compartir reportes entre investigadores y tesistas.
"""

import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

def db_obtener_usuarios_compartir(id_usuario: int) -> list:
    """
    Obtiene los usuarios (Investigadores y Tesistas) con los que se puede compartir
    un reporte (excluyendo al usuario actual).
    Retorna una lista de tuplas (id_usuario, nombre_usuario, rol).
    """
    from bd.database import conectar
    conn = conectar()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id_usuario, nombre_usuario, rol FROM Usuario WHERE id_usuario != ? AND rol IN ('Investigador', 'Tesista')",
            (id_usuario,)
        )
        return cur.fetchall()
    except Exception as e:
        logging.error(f"[compartir_reporte] Error al obtener usuarios para compartir: {e}")
        return []
    finally:
        conn.close()

def db_compartir_reportes(id_propietario: int, id_destinatario: int, id_reportes: list) -> int:
    """
    Inserta registros en ReporteCompartido para los reportes indicados,
    siempre y cuando no se hayan compartido previamente con el mismo destinatario.
    Retorna la cantidad de reportes compartidos exitosamente.
    """
    from bd.database import conectar
    conn = conectar()
    cur = conn.cursor()
    exito_count = 0
    try:
        for id_rep in id_reportes:
            # Verificar si ya está compartido con este usuario
            cur.execute(
                "SELECT COUNT(*) FROM ReporteCompartido WHERE id_reporte = ? AND id_destinatario = ?",
                (id_rep, id_destinatario)
            )
            if cur.fetchone()[0] > 0:
                continue # Omitir si ya está compartido
            
            cur.execute(
                "INSERT INTO ReporteCompartido (id_reporte, id_propietario, id_destinatario, estado) "
                "VALUES (?, ?, ?, 'Pendiente')", 
                (id_rep, id_propietario, id_destinatario)
            )
            exito_count += 1
        conn.commit()
        return exito_count
    except Exception as e:
        logging.error(f"[compartir_reporte] Error al guardar compartidos en BD: {e}")
        raise
    finally:
        conn.close()

class DialogoCompartirReporte(QDialog):
    def __init__(self, id_usuario, id_reportes, parent=None):
        super().__init__(parent)
        self.id_usuario = id_usuario
        self.id_reportes = id_reportes if isinstance(id_reportes, list) else [id_reportes]
        
        self.setWindowTitle("Compartir Reportes" if len(self.id_reportes) > 1 else "Compartir Reporte")
        self.setFixedSize(400, 210)
        from vistas.utilidades import set_app_icon
        set_app_icon(self)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        msg_text = (
            f"<b>Compartir {len(self.id_reportes)} Reportes Científicos</b><br>Selecciona al Investigador o Tesista con el que deseas compartir el acceso a estos reportes:"
            if len(self.id_reportes) > 1 else
            "<b>Compartir Reporte Científico</b><br>Selecciona al Investigador o Tesista con el que deseas compartir el acceso a este reporte:"
        )
        lbl_msg = QLabel(msg_text)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("font-size: 12px; color: #24292f;")
        layout.addWidget(lbl_msg)
        
        self.combo_usuarios = QComboBox()
        self.combo_usuarios.setStyleSheet("""
            QComboBox { background-color: white; border: 1px solid #d0d7de; border-radius: 6px; padding: 6px 10px; font-size: 12px; color: #24292f; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: white; border: 1px solid #d0d7de; selection-background-color: #eaf2ff; }
        """)
        layout.addWidget(self.combo_usuarios)
        
        # Cargar usuarios disponibles usando la función de BD centralizada
        self.usuarios_list = []
        rows = db_obtener_usuarios_compartir(self.id_usuario)
        for id_u, name, rol in rows:
            self.combo_usuarios.addItem(f"{name} ({rol})")
            self.usuarios_list.append(id_u)
            
        btn_layout = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("background-color: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px; padding: 8px 16px; font-weight: bold;")
        btn_cancelar.clicked.connect(self.reject)
        
        self.btn_compartir = QPushButton("Compartir")
        self.btn_compartir.setStyleSheet("background-color: #0969da; color: white; border-radius: 6px; padding: 8px 16px; font-weight: bold; border: none;")
        self.btn_compartir.clicked.connect(self.compartir_reporte)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(self.btn_compartir)
        layout.addLayout(btn_layout)

    def compartir_reporte(self):
        index = self.combo_usuarios.currentIndex()
        if index < 0 or index >= len(self.usuarios_list):
            self.reject()
            return
        dest_id = self.usuarios_list[index]
        
        try:
            exito_count = db_compartir_reportes(self.id_usuario, dest_id, self.id_reportes)
            from vistas.utilidades import DialogoNotificacion
            if exito_count > 0:
                DialogoNotificacion("Éxito", f"Acceso a {exito_count} reporte(s) compartido exitosamente.", "info", self).exec()
            else:
                DialogoNotificacion("Atención", "Los reportes seleccionados ya estaban compartidos con este usuario.", "warning", self).exec()
            self.accept()
        except Exception as e:
            logging.error(f"Error al compartir reporte desde el diálogo: {e}")
            self.reject()
