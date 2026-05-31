from vistas.base_analisis import VentanaBaseAnalisis

class VentanaInvitado(VentanaBaseAnalisis):
    """
    Vista exclusiva para el rol de Invitado.
    Hereda toda la lógica compartida de análisis e interfaces de la ventana base.
    Como el Invitado opera de forma volátil (sin cuenta persistente en base de datos),
    se desactivan las opciones de historial y las llamadas automáticas de persistencia.
    """
    def __init__(self, id_usuario=0, rol="Invitado", nombre_usuario="Invitado"):
        # Un Invitado siempre opera localmente, por lo que el id_usuario es 0
        super().__init__(id_usuario=0, rol="Invitado", nombre_usuario="Invitado")
        
    def save_current_progress(self, mostrar_notif=True):
        # El Invitado no almacena análisis de forma persistente en la Base de Datos
        pass

    def abrir_historial(self):
        # El Invitado no tiene acceso al historial de reportes guardados
        self.mostrar_notificacion("Acceso restringido", "El rol de Invitado opera localmente y no cuenta con un historial de reportes en la base de datos.", "warning")
