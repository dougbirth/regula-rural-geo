from qgis.core import QgsApplication
from .provider import RegulaRuralGeoProvider


class RegulaRuralGeoPlugin:
    def __init__(self, iface):
        self.provider = None

    def initGui(self):
        self.provider = RegulaRuralGeoProvider()
        if not QgsApplication.processingRegistry().addProvider(self.provider):
            self.provider = None

    def unload(self):
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
