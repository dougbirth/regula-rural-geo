"""Consulta à base nacional SIGEF com resultado único em Shapefile."""
from uuid import UUID
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsExpression, QgsProcessingException
from .consulta_shp import ConsultaShp, campo, filtro_area, uri_wfs
from .estilos import aplicar_estilo_geo_incra

ENDPOINT = "https://geoportal.incra.gov.br/geoserver/ows"
TYPENAME = "geonode:sigef_geo"


def normalizar_sigef(codigo):
    codigo = (codigo or "").strip()
    if not codigo:
        return ""
    try:
        return str(UUID(codigo))
    except ValueError:
        raise QgsProcessingException("Informe o código UUID completo da parcela SIGEF.")


def consulta_filtro(codigo="", rect=None):
    codigo = normalizar_sigef(codigo)
    if rect is None and not codigo:
        raise QgsProcessingException("Desenhe uma área na tela ou informe o código da parcela SIGEF.")
    conditions = []
    if codigo:
        conditions.append(QgsExpression.createFieldEqualityExpression("parcela_codigo", codigo))
    area = filtro_area(rect)
    if area:
        conditions.append(area)
    return " AND ".join(conditions)


def wfs_uri(expression):
    return uri_wfs(ENDPOINT, TYPENAME, expression)


class ConsultarSigef(ConsultaShp):
    endpoint = ENDPOINT
    code_field = "parcela_codigo"
    code_label = "Código da parcela SIGEF (UUID)"
    result_name = "GEO INCRA — imóveis encontrados"
    style = staticmethod(aplicar_estilo_geo_incra)
    style_help = "Preenchimento laranja sólido com 50% de transparência."
    source_help = (
        "Fonte: SIGEF, Geoportal do INCRA. A conexão abrange todo o Brasil. "
        "O UUID identifica a parcela; não é a matrícula do imóvel. Inclui todas as situações "
        "publicadas, inclusive canceladas quando presentes. Não inclui SNCI ou assentamentos."
    )
    schema = [
        campo("status", "status", "Situação da parcela"),
        campo("rt", "rt", "Responsável técnico"),
        campo("data_aprovacao", "dt_aprov", "Data de aprovação (ISO 8601)"),
        campo("data_submissao", "dt_submis", "Data de submissão (ISO 8601)"),
        campo("parcela_codigo", "cod_parcel", "Código da parcela SIGEF"),
        campo("situacao_informada", "sit_inform", "Situação informada"),
        campo("registro_cns", "reg_cns", "CNS do cartório"),
        campo("registro_matricula", "matricula", "Matrícula"),
        campo("data_registro", "dt_regist", "Data do registro (ISO 8601)"),
        campo("transcricao", "transcr", "Transcrição"),
        campo("natureza", "natureza", "Natureza"),
        campo("codigo_imovel", "cod_imovel", "Código do imóvel"),
        campo("municipio_id", "cod_munic", "Código do município (IBGE)", QVariant.Int),
        campo("uf_id", "cod_uf", "Código da UF (IBGE)", QVariant.Int),
        campo("area_hectares", "area_ha", "Área (ha)", QVariant.Double),
        campo("nome_area", "nome_area", "Nome do imóvel"),
        campo("tipo_envio", "tipo_envio", "Tipo de envio"),
    ]

    def name(self):
        return "consultar_base_incra"

    def displayName(self):
        return "Consultar base GEO INCRA"

    def tags(self):
        return ["SIGEF", "INCRA", "nacional", "imóvel", "parcela", "SHP"]

    def createInstance(self):
        return ConsultarSigef()

    def normalizar_codigo(self, value):
        return normalizar_sigef(value)

    def consultas(self, codigo, rect):
        return [(TYPENAME, consulta_filtro(codigo, rect))]
