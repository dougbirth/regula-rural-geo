"""Busca nacional do CAR com resultado único em Shapefile."""
import re
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsProcessingException
from .consulta_shp import ConsultaShp, campo, filtro_area, uri_wfs
from .estilos import aplicar_estilo_car

ENDPOINT_CAR = "https://geoserver.car.gov.br/geoserver/sicar/wfs"
UF_CODES = {
    "AC": 12, "AL": 27, "AM": 13, "AP": 16, "BA": 29, "CE": 23, "DF": 53,
    "ES": 32, "GO": 52, "MA": 21, "MG": 31, "MS": 50, "MT": 51, "PA": 15,
    "PB": 25, "PE": 26, "PI": 22, "PR": 41, "RJ": 33, "RN": 24, "RO": 11,
    "RR": 14, "RS": 43, "SC": 42, "SE": 28, "SP": 35, "TO": 17,
}


def normalizar_car(value):
    value = re.sub(r"\s+", "", value or "").upper()
    if not value:
        return "", None
    match = re.fullmatch(r"([A-Z]{2})-(\d{7})-([0-9A-F.\-]+)", value)
    if match:
        uf, municipio, suffix = match.groups()
        suffix = suffix.replace(".", "").replace("-", "")
        if (uf in UF_CODES and municipio.startswith(str(UF_CODES[uf]))
                and re.fullmatch(r"[0-9A-F]{32}", suffix)):
            return f"{uf}-{municipio}-{suffix}", uf
    raise QgsProcessingException(
        "Informe o número completo do CAR federal. Exemplo: "
        "MT-5104526-B1129A3802C14041889514856D9F2B02. Pontos no identificador são aceitos."
    )


def consultas_car(codigo="", rect=None):
    codigo, uf_codigo = normalizar_car(codigo)
    if rect is None and not codigo:
        raise QgsProcessingException("Desenhe uma área na tela ou informe o número do CAR federal.")
    conditions = []
    if codigo:
        conditions.append(f'"cod_imovel" = \'{codigo}\'')
    area = filtro_area(rect, "geo_area_imovel")
    if area:
        conditions.append(area)
    queries = []
    for uf in ([uf_codigo] if uf_codigo else UF_CODES):
        typename = f"sicar:sicar_imoveis_{uf.lower()}"
        queries.append((uf, typename, f'SELECT * FROM "{typename}" WHERE ' + " AND ".join(conditions)))
    return queries


def car_uri(typename, sql):
    return uri_wfs(ENDPOINT_CAR, typename, sql)


class ConsultarCar(ConsultaShp):
    endpoint = ENDPOINT_CAR
    code_field = "cod_imovel"
    code_label = "Número do CAR federal"
    result_name = "CAR — imóveis encontrados"
    style = staticmethod(aplicar_estilo_car)
    style_help = "Preenchimento verde sólido com 50% de transparência."
    source_help = (
        "Fonte: SICAR / CAR, geoserver.car.gov.br. Consulta perímetros dos imóveis em todo o Brasil. "
        "Inclui todas as situações publicadas; confira situação e condição. Não inclui APP, "
        "reserva legal nem documentos. As datas disponíveis variam conforme a origem."
    )
    schema = [
        campo("cod_imovel", "cod_imovel", "Número do CAR federal"),
        campo("status_imovel", "situacao", "Situação do cadastro"),
        campo("dat_criacao", "dt_criacao", "Data de criação (ISO 8601)"),
        campo("data_atualizacao", "dt_atualiz", "Data de atualização (ISO 8601)"),
        campo("area", "area_ha", "Área declarada (ha)", QVariant.Double),
        campo("condicao", "condicao", "Condição do cadastro"),
        campo("uf", "uf", "UF"),
        campo("municipio", "municipio", "Município"),
        campo("cod_municipio_ibge", "cod_munic", "Código do município (IBGE)", QVariant.Int),
        campo("m_fiscal", "mod_fiscal", "Módulos fiscais", QVariant.Double),
        campo("tipo_imovel", "tipo_imov", "Tipo de imóvel"),
    ]

    def name(self):
        return "consultar_base_car"

    def displayName(self):
        return "Consultar base CAR"

    def tags(self):
        return ["CAR", "SICAR", "cadastro ambiental rural", "nacional", "SHP", "REGULA RURAL GEO"]

    def createInstance(self):
        return ConsultarCar()

    def normalizar_codigo(self, value):
        return normalizar_car(value)[0]

    def consultas(self, codigo, rect):
        return [(typename, sql) for _, typename, sql in consultas_car(codigo, rect)]
