import sqlite3
import hashlib
import os

import sys

if getattr(sys, 'frozen', False):
    app_data = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
    base_dir = os.path.join(app_data, 'AVA_Image_Analytics')
else:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

bd_dir = os.path.join(base_dir, 'bd')
if not os.path.exists(bd_dir):
    os.makedirs(bd_dir, exist_ok=True)

DB_PATH = os.path.join(bd_dir, "database.db")

def conectar():
    """Crea la conexión a la base de datos SQLite (local o remota vía proxy de red)"""
    from red.config import es_cliente
    if es_cliente():
        from red.cliente import conectar_cliente
        return conectar_cliente()
    return sqlite3.connect(DB_PATH)

def inicializar_bd():
    """Crea las tablas si no existen, actualiza el esquema y crea el admin"""
    from red.config import es_cliente
    if es_cliente():
        return
    conexion = conectar()
    cursor = conexion.cursor()

    # 1. Creación de tablas base
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
            campo TEXT,
            tiempo_muestra TEXT,
            fecha_carga DATE DEFAULT CURRENT_DATE,
            FOREIGN KEY (id_usuario) REFERENCES Usuario(id_usuario)
        );

        CREATE TABLE IF NOT EXISTS Reporte (
            id_reporte INTEGER PRIMARY KEY AUTOINCREMENT,
            id_usuario INTEGER NOT NULL,
            nombre_reporte TEXT,
            fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            estado TEXT DEFAULT 'En progreso',
            FOREIGN KEY (id_usuario) REFERENCES Usuario(id_usuario)
        );

        CREATE TABLE IF NOT EXISTS Analisis (
            id_analisis INTEGER PRIMARY KEY AUTOINCREMENT,
            id_reporte INTEGER,
            id_imagen INTEGER NOT NULL,
            fecha_analisis DATETIME DEFAULT CURRENT_TIMESTAMP,
            cantidad_microglias INTEGER NOT NULL,
            paso_actual INTEGER DEFAULT 1,
            datos_persistentes TEXT,
            FOREIGN KEY (id_reporte) REFERENCES Reporte(id_reporte),
            FOREIGN KEY (id_imagen) REFERENCES Imagen(id_imagen)
        );

        CREATE TABLE IF NOT EXISTS Microglia (
            id_microglia INTEGER PRIMARY KEY AUTOINCREMENT,
            id_analisis INTEGER NOT NULL,
            puntos_finales INTEGER,
            uniones_triples INTEGER,
            uniones_cuadruples INTEGER,
            longitud_promedio_ramas REAL,
            longitud_maxima_rama REAL,
            ruta_mas_larga REAL,
            lineas INTEGER,
            puntos_union INTEGER,
            voxeles_union INTEGER,
            voxeles_losa INTEGER,
            filtro_clahe INTEGER DEFAULT 0,
            filtro_gauss INTEGER DEFAULT 0,
            filtro_otsu INTEGER DEFAULT 0,
            filtro_ruido INTEGER DEFAULT 0,
            filtro_cierre INTEGER DEFAULT 0,
            areas_eliminadas TEXT,
            bbox_x REAL, 
            bbox_y REAL, 
            bbox_w REAL, 
            bbox_h REAL, 
            crop_path TEXT,
            FOREIGN KEY (id_analisis) REFERENCES Analisis(id_analisis)
        );

        CREATE TABLE IF NOT EXISTS ReporteCompartido (
            id_reporte_compartido INTEGER PRIMARY KEY AUTOINCREMENT,
            id_reporte INTEGER NOT NULL,
            id_propietario INTEGER NOT NULL,
            id_destinatario INTEGER NOT NULL,
            estado TEXT DEFAULT 'Pendiente',
            comentarios TEXT,
            fecha_compartido DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_reporte) REFERENCES Reporte(id_reporte),
            FOREIGN KEY (id_propietario) REFERENCES Usuario(id_usuario),
            FOREIGN KEY (id_destinatario) REFERENCES Usuario(id_usuario)
        );
    ''')

    # 2. Migraciones (Para asegurar columnas nuevas en instalaciones existentes)
    try: cursor.execute("ALTER TABLE Imagen ADD COLUMN campo TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE Imagen ADD COLUMN tiempo_muestra TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE Analisis ADD COLUMN id_reporte INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE Analisis ADD COLUMN paso_actual INTEGER DEFAULT 1")
    except: pass
    try: cursor.execute("ALTER TABLE Analisis ADD COLUMN datos_persistentes TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE Microglia ADD COLUMN crop_path TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE Microglia ADD COLUMN lineas INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE Microglia ADD COLUMN puntos_union INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE Microglia ADD COLUMN voxeles_union INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE Microglia ADD COLUMN voxeles_losa INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE Microglia ADD COLUMN filtro_clahe INTEGER DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE Microglia ADD COLUMN filtro_gauss INTEGER DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE Microglia ADD COLUMN filtro_otsu INTEGER DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE Microglia ADD COLUMN filtro_ruido INTEGER DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE Microglia ADD COLUMN filtro_cierre INTEGER DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE Microglia ADD COLUMN areas_eliminadas TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE Reporte ADD COLUMN id_usuario INTEGER")
    except: pass
    try: cursor.execute("ALTER TABLE Reporte ADD COLUMN nombre_reporte TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE Reporte ADD COLUMN estado TEXT DEFAULT 'En progreso'")
    except: pass

    # 3. Crear usuario administrador por defecto y usuario Invitado (ID 0)
    cursor.execute("SELECT COUNT(*) FROM Usuario WHERE nombre_usuario = 'admin'")
    if cursor.fetchone()[0] == 0:
        pass_hash = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute('''
            INSERT INTO Usuario (nombre_usuario, contrasenia_hash, rol) 
            VALUES (?, ?, ?)
        ''', ("admin", pass_hash, "Administrador"))
        print("=> ¡BD lista! Usuario: admin | Pass: admin123")
        
    cursor.execute("SELECT COUNT(*) FROM Usuario WHERE id_usuario = 0")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO Usuario (id_usuario, nombre_usuario, contrasenia_hash, rol) 
            VALUES (0, 'Invitado_Volatil', 'none', 'Invitado')
        ''')

    conexion.commit()
    conexion.close()

def limpiar_datos_invitado():
    """
    Limpia todos los registros temporales creados por el rol de Invitado (id_usuario = 0)
    para evitar que la base de datos se llene de datos de prueba.
    """
    try:
        conn = conectar()
        cur = conn.cursor()
        
        cur.execute("""
            DELETE FROM Microglia 
            WHERE id_analisis IN (
                SELECT a.id_analisis FROM Analisis a
                JOIN Reporte r ON a.id_reporte = r.id_reporte
                WHERE r.id_usuario = 0
            )
        """)
        
        cur.execute("""
            DELETE FROM Analisis 
            WHERE id_reporte IN (
                SELECT id_reporte FROM Reporte WHERE id_usuario = 0
            )
        """)
        
        cur.execute("DELETE FROM ReporteCompartido WHERE id_propietario = 0 OR id_destinatario = 0")
        cur.execute("DELETE FROM Reporte WHERE id_usuario = 0")
        cur.execute("DELETE FROM Sesion WHERE id_usuario = 0")
        
        conn.commit()
        conn.close()
    except Exception as e:
        import logging
        logging.error(f"Error limpiando datos de invitado: {e}")

if __name__ == "__main__":
    inicializar_bd()