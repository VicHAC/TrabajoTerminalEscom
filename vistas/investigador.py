from vistas.base_analisis import VentanaBaseAnalisis

class VentanaInvestigador(VentanaBaseAnalisis):
    """
    Vista exclusiva para el rol de Investigador.
    Hereda toda la lógica compartida de análisis e interfaces de la ventana base
    e incluye las herramientas de persistencia en base de datos e historial completas.
    """
    def __init__(self, id_usuario, rol="Investigador", nombre_usuario=""):
        super().__init__(id_usuario, rol, nombre_usuario)
