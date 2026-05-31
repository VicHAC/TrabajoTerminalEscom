from vistas.base_analisis import VentanaBaseAnalisis

class VentanaTesista(VentanaBaseAnalisis):
    """
    Vista exclusiva para el rol de Tesista (nuevo rol).
    Hereda toda la lógica compartida de análisis e interfaces de la ventana base.
    Permite acceso completo a base de datos, guardado persistente de avances y consulta de historial.
    """
    def __init__(self, id_usuario, rol="Tesista", nombre_usuario=""):
        super().__init__(id_usuario, rol, nombre_usuario)
