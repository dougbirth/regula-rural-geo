from qgis.core import QgsFillSymbol, QgsSingleSymbolRenderer, QgsVectorLayer


def aplicar_estilo_geo_incra(layer):
    layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({
        "style": "solid", "color": "255,165,0,255",
        "outline_color": "204,112,0,255", "outline_width": "0.26",
    })))
    layer.setOpacity(0.5)
    layer.setCustomProperty("regula_rural_geo/fonte", "SIGEF")


def aplicar_estilo_car(layer):
    layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({
        "style": "solid", "color": "0,128,0,255",
        "outline_color": "0,100,0,255", "outline_width": "0.26",
    })))
    layer.setOpacity(0.5)
    layer.setCustomProperty("regula_rural_geo/fonte", "CAR")


def atualizar_estilos_projeto(project):
    """Migração explícita dos resultados desta ferramenta no projeto aberto."""
    count = 0
    for layer in project.mapLayers().values():
        if not isinstance(layer, QgsVectorLayer) or layer.providerType() != "WFS":
            continue
        source = layer.customProperty("regula_rural_geo/fonte", "")
        description = layer.metadata().abstract()
        if source == "SIGEF" or description.startswith("SIGEF, consulta direta ao Geoportal do INCRA."):
            aplicar_estilo_geo_incra(layer)
        elif source == "CAR" or (description.startswith("CAR — perímetros dos imóveis")
                                and "Consulta direta ao SICAR." in description):
            aplicar_estilo_car(layer)
        else:
            continue
        layer.triggerRepaint()
        count += 1
    return count
