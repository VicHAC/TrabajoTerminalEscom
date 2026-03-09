import sqlite3
import hashlib
import os

# Asegurarse de que la carpeta bd exista
if not os.path.exists('bd'):
    os.makedirs('bd')

DB_PATH = "bd/database.db"

def conectar():
    """Crea la conexión a la base de datos SQLite"""
    return sqlite3.connect(DB_PATH)

def inicializar_bd():
    """Crea las tablas si no existen y mete al admin por defecto"""
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS Usuario (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_usuario TEXT NOT NULL UNIQUE,
            contrasenia_hash TEXT NOT NULL,
            rol TEXT NOT NULL,
            fecha_creacion DATE DEFAULT CURRENT_DATE
        );

        CREATE TABLE IF NOT EXISTS Sesion (
            id_sesion INTEGER PRIMARY KEY AUTOINCREMENT,
            id_usuario INTEGER NOT NULL,
            fecha_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_usuario) REFERENCES Usuario(id_usuario)
        );

        CREATE TABLE IF NOT EXISTS Imagen (
            id_imagen INTEGER PRIMARY KEY AUTOINCREMENT,
            id_usuario INTEGER NOT NULL,
            ruta_archivo TEXT NOT NULL,
            formato TEXT NOT NULL,
            fecha_carga DATE DEFAULT CURRENT_DATE,
            FOREIGN KEY (id_usuario) REFERENCES Usuario(id_usuario)
        );

        CREATE TABLE IF NOT EXISTS Analisis (
            id_analisis INTEGER PRIMARY KEY AUTOINCREMENT,
            id_imagen INTEGER NOT NULL,
            fecha_analisis DATETIME DEFAULT CURRENT_TIMESTAMP,
            cantidad_microglias INTEGER NOT NULL,
            FOREIGN KEY (id_imagen) REFERENCES Imagen(id_imagen)
        );

        CREATE TABLE IF NOT EXISTS Microglia (
            id_microglia INTEGER PRIMARY KEY AUTOINCREMENT,
            id_analisis INTEGER NOT NULL,
            
            -- Localización Espacial en la imagen 2D
            centroide_x REAL NOT NULL,
            centroide_y REAL NOT NULL,
            
            -- Morfología General (Área en lugar de Volumen)
            area_total_pixeles REAL NOT NULL,
            area_soma_pixeles REAL, -- El tamaño del cuerpo central
            perimetro REAL NOT NULL,
            
            -- Análisis del Esqueleto 2D (Lo que saca ImageJ)
            pixeles_rama INTEGER, -- Píxeles que forman el esqueleto
            puntos_finales INTEGER, -- Puntas de las dendritas
            uniones_triples INTEGER, -- Bifurcaciones (nodos de 3)
            uniones_cuadruples INTEGER, -- Cruces (nodos de 4)
            
            -- Métricas de Longitud
            longitud_promedio_ramas REAL,
            longitud_maxima_rama REAL,
            ruta_mas_larga REAL, -- Longest shortest path en 2D
            
            -- Clasificación Biomédica (El chisme de qué le pasó a la rata)
            tiempo_exposicion_horas REAL,
            estado_clasificado TEXT, -- "Ramificado" (0.2h-5h) o "Fagocítico/Ameboide" (24h-168h)
            
            -- Datos técnicos para pintar la cajita en la Interfaz
            bbox_x REAL, 
            bbox_y REAL, 
            bbox_w REAL, 
            bbox_h REAL, 
            
            FOREIGN KEY (id_analisis) REFERENCES Analisis(id_analisis)
        );

        CREATE TABLE IF NOT EXISTS Reporte (
            id_reporte INTEGER PRIMARY KEY AUTOINCREMENT,
            id_analisis INTEGER NOT NULL,
            ruta_archivo TEXT NOT NULL,
            fecha_generacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_analisis) REFERENCES Analisis(id_analisis)
        );
    ''')
    
    # Crear usuario administrador si la BD esta
    cursor.execute("SELECT COUNT(*) FROM Usuario")
    if cursor.fetchone()[0] == 0:
        pass_hash = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute('''
            INSERT INTO Usuario (nombre_usuario, contrasenia_hash, rol) 
            VALUES (?, ?, ?)
        ''', ("admin", pass_hash, "Administrador"))
        print("=> ¡BD lista! Usuario: admin | Pass: admin123")

    conexion.commit()
    conexion.close()

# EJECUTAR SOLO LA PRIMERA VEZ
if __name__ == "__main__":
    inicializar_bd()