from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QHeaderView
from PyQt6.QtCore import Qt
from bd.database import conectar # Importamos tu conexión consolidada

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
        self.tabla = QTableWidget(0, 6)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre Imagen", "Muestra", "Tiempo", "Fecha", "Último Paso"])
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
                SELECT A.id_analisis, I.ruta_archivo, I.campo, I.tiempo_muestra, A.fecha_analisis, A.paso_actual
                FROM Analisis A
                JOIN Imagen I ON A.id_imagen = I.id_imagen
                WHERE I.id_usuario = ?
                ORDER BY A.fecha_analisis DESC
            """
            cur.execute(query, (self.id_usuario,))
            rows = cur.fetchall()
            self.tabla.setRowCount(len(rows))
            
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    text = str(val)
                    if j == 1: # Solo mostrar el nombre del archivo, no la ruta completa
                        text = os.path.basename(text)
                    self.tabla.setItem(i, j, QTableWidgetItem(text))
            conn.close()
        except Exception as e:
            print(f"Error cargando historial: {e}")

    def aceptar_seleccion(self):
        row = self.tabla.currentRow()
        if row != -1:
            self.id_analisis_seleccionado = int(self.tabla.item(row, 0).text())
            self.accept()