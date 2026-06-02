from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QHeaderView
from PyQt6.QtCore import Qt
from bd.database import conectar # Importamos tu conexión consolidada
import os

class VentanaHistorial(QDialog):
    def __init__(self, id_usuario, parent=None):
        super().__init__(parent)
        self.id_usuario = id_usuario
        self.id_analisis_seleccionado = None
        self.setWindowTitle("Historial de Procesamientos")
        self.setMinimumSize(800, 450)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Tabla de reportes
        self.tabla = QTableWidget(0, 7)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre Imagen", "Muestra", "Tiempo", "Fecha", "Último Paso", "Detecciones"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tabla)

        self.cargar_datos()

        # Botones
        btns = QHBoxLayout()
        self.btn_retomar = QPushButton("Retomar Trabajo")
        self.btn_retomar.setStyleSheet("padding: 10px; font-weight: bold; background-color: #007bff; color: white; border-radius: 5px;")
        self.btn_retomar.setEnabled(False)
        self.btn_retomar.clicked.connect(self.aceptar_seleccion)
        
        self.tabla.itemSelectionChanged.connect(lambda: self.btn_retomar.setEnabled(True))
        
        btns.addStretch()
        btns.addWidget(self.btn_retomar)
        layout.addLayout(btns)

    def cargar_datos(self):
        try:
            conn = conectar()
            cur = conn.cursor()
            # Unimos Analisis con Imagen para sacar los datos completos del investigador
            query = """
                SELECT A.id_analisis, I.ruta_archivo, I.campo, I.tiempo_muestra, A.fecha_analisis, A.paso_actual, A.cantidad_microglias, A.datos_persistentes
                FROM Analisis A
                JOIN Imagen I ON A.id_imagen = I.id_imagen
                WHERE I.id_usuario = ?
                ORDER BY A.fecha_analisis DESC
            """
            cur.execute(query, (self.id_usuario,))
            rows = cur.fetchall()
            self.tabla.setRowCount(len(rows))
            
            for i, row in enumerate(rows):
                id_an, ruta, campo, tiempo, fecha, paso, cant, dp = row
                
                # Sistema de fallback robusto de 3 niveles para detecciones
                if not cant or cant == 0:
                    cur.execute("SELECT COUNT(*) FROM Microglia WHERE id_analisis = ?", (id_an,))
                    cant = cur.fetchone()[0] or 0
                    if cant == 0 and dp:
                        try:
                            import json
                            datos = json.loads(dp)
                            cant = len(datos.get("boxes", []))
                        except:
                            pass
                
                valores = [
                    str(id_an),
                    os.path.basename(ruta),
                    str(campo),
                    str(tiempo),
                    str(fecha),
                    "Completado" if paso >= 5 else f"En proceso ({paso}/4)",
                    str(cant)
                ]
                
                for j, val in enumerate(valores):
                    self.tabla.setItem(i, j, QTableWidgetItem(val))
            conn.close()
        except Exception as e:
            print(f"Error cargando historial: {e}")

    def aceptar_seleccion(self):
        row = self.tabla.currentRow()
        if row != -1:
            self.id_analisis_seleccionado = int(self.tabla.item(row, 0).text())
            self.accept()