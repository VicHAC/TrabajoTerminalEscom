import os
import pytest
import sqlite3
import shutil

# Variables para base de datos temporal de pruebas
TEST_DB_DIR = "bd_test"
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_database.db")

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Fixture global que redirige la base de datos a un archivo temporal
    para todas las pruebas, garantizando que no se toque la base real.
    """
    # Crear directorio temporal si no existe
    if not os.path.exists(TEST_DB_DIR):
        os.makedirs(TEST_DB_DIR)

    # Limpiar si ya había una bd de pruebas anterior
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    # Parchear la ruta en el módulo
    import bd.database
    bd.database.DB_PATH = TEST_DB_PATH
    
    # Inicializar la base de datos (crear tablas, admin, etc.)
    bd.database.inicializar_bd()

    yield

    # Limpiar después de las pruebas
    if os.path.exists(TEST_DB_DIR):
        shutil.rmtree(TEST_DB_DIR)

@pytest.fixture
def clean_db():
    """Limpia los datos de las tablas (excepto admin) antes de una prueba específica."""
    import bd.database
    conn = sqlite3.connect(TEST_DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM Microglia")
    cur.execute("DELETE FROM Analisis")
    cur.execute("DELETE FROM ReporteCompartido")
    cur.execute("DELETE FROM Reporte")
    cur.execute("DELETE FROM Imagen")
    cur.execute("DELETE FROM Sesion")
    cur.execute("DELETE FROM Usuario WHERE id_usuario > 0 AND nombre_usuario != 'admin'")
    conn.commit()
    conn.close()
