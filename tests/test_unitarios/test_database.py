import pytest
import sqlite3
import hashlib
from bd.database import conectar, inicializar_bd

def test_inicializar_bd_crea_tablas():
    """Verifica que las tablas principales se hayan creado correctamente."""
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tablas = [t[0] for t in cur.fetchall()]
    conn.close()
    
    assert "Usuario" in tablas
    assert "Imagen" in tablas
    assert "Reporte" in tablas
    assert "Analisis" in tablas
    assert "Microglia" in tablas

def test_usuario_admin_por_defecto():
    """Verifica que el usuario 'admin' se cree automáticamente."""
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT contrasenia_hash, rol FROM Usuario WHERE nombre_usuario='admin'")
    resultado = cur.fetchone()
    conn.close()
    
    assert resultado is not None
    pass_hash, rol = resultado
    
    # Comprobar que el hash coincida con 'admin123'
    expected_hash = hashlib.sha256("admin123".encode()).hexdigest()
    assert pass_hash == expected_hash
    assert rol == "Administrador"

def test_usuario_invitado_por_defecto():
    """Verifica que el usuario 'Invitado_Volatil' exista."""
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT id_usuario, rol FROM Usuario WHERE nombre_usuario='Invitado_Volatil'")
    resultado = cur.fetchone()
    conn.close()
    
    assert resultado is not None
    id_usr, rol = resultado
    assert id_usr == 0
    assert rol == "Invitado"
