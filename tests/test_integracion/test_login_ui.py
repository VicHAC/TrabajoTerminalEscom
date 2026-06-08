import pytest
from PyQt6.QtWidgets import QApplication
from vistas.login import VentanaLogin
from unittest.mock import patch

@patch('vistas.administrador.VentanaAdministrador')
@patch('vistas.utilidades.DialogoCarga')
def test_login_ui_credenciales_correctas(mock_dialogo_carga, mock_ventana_admin, qtbot, clean_db):
    """Prueba que al ingresar 'admin' y 'admin123' el sistema permita el acceso al panel."""
    ventana = VentanaLogin()
    qtbot.addWidget(ventana)

    # Simular teclado
    qtbot.keyClicks(ventana.input_usuario, "admin")
    qtbot.keyClicks(ventana.input_password, "admin123")

    # Hacer clic en ingresar llamando al método
    ventana.verificar_login()

    # Si las credenciales son correctas, debe instanciar la ventana de Administrador
    mock_ventana_admin.assert_called_once()
    
    # Verificamos que se asignó
    assert hasattr(ventana, 'dashboard')
