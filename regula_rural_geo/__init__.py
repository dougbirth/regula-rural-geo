"""REGULA RURAL GEO: ferramentas de consulta ao SIGEF e CAR."""


def classFactory(iface):
    from .plugin import RegulaRuralGeoPlugin
    return RegulaRuralGeoPlugin(iface)
