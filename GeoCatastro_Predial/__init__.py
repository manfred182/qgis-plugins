def classFactory(iface):
    from .consultas_prediales import ConsultasPrediales
    return ConsultasPrediales(iface)
