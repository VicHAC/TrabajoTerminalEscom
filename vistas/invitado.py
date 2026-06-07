from vistas.base_analisis import VentanaBaseAnalisis
from bd.database import limpiar_datos_invitado

class VentanaInvitado(VentanaBaseAnalisis):
    """
    Vista exclusiva para el rol de Invitado.
    Hereda toda la lógica compartida de análisis e interfaces de la ventana base.
    El invitado tiene acceso completo a las funciones de análisis de múltiples imágenes 
    dentro de una sesión temporal (id_usuario = 0).
    Al cerrar la ventana o cerrar sesión, todos los datos se borran de la base de datos.
    """
    def __init__(self, id_usuario=0, rol="Invitado", nombre_usuario="Invitado"):
        # Un Invitado opera con el id_usuario 0, que es temporal.
        super().__init__(id_usuario=0, rol="Invitado", nombre_usuario="Invitado")
        
    def abrir_historial(self):
        # El Invitado no tiene acceso al historial de reportes guardados
        self.mostrar_notificacion("Acceso restringido", "El rol de Invitado opera localmente y no cuenta con un historial de reportes. Solo puedes ver el análisis de la sesión actual.", "warning")

    def cerrar_sesion(self):
        # Limpiar datos volátiles antes de cerrar la sesión
        limpiar_datos_invitado()
        super().cerrar_sesion()
        
    def closeEvent(self, event):
        # Limpiar datos volátiles al cerrar la ventana
        limpiar_datos_invitado()
        super().closeEvent(event)
