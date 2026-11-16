from pathlib import Path
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingProvider
from .consultar_sigef import ConsultarSigef
from .consultar_car import ConsultarCar


class RegulaRuralGeoProvider(QgsProcessingProvider):
    def id(self):
        return "regula_rural_geo"

    def name(self):
        return "REGULA RURAL GEO"

    def longName(self):
        return "REGULA RURAL GEO — consultas ao SIGEF e CAR"

    def icon(self):
        return QIcon(str(Path(__file__).with_name("icon.png")))

    def loadAlgorithms(self):
        self.addAlgorithm(ConsultarSigef())
        self.addAlgorithm(ConsultarCar())
