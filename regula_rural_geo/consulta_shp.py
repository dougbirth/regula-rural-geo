"""Consulta WFS filtrada e publicação de um único Shapefile editável."""
import math
import os
import tempfile
from pathlib import Path

from qgis.PyQt.QtCore import QDateTime, Qt, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.core import (
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsDataSourceUri,
    QgsFeature, QgsFeatureRequest, QgsField, QgsFields, QgsGeometry,
    QgsProcessing, QgsProcessingAlgorithm, QgsProcessingContext,
    QgsProcessingException, QgsProcessingParameterExtent,
    QgsProcessingParameterFileDestination, QgsProcessingParameterString,
    QgsVariantUtils, QgsVectorFileWriter, QgsVectorLayer, QgsWkbTypes,
)


class ConsultaCancelada(Exception):
    pass


def verificar_cancelamento(feedback):
    if feedback.isCanceled():
        raise ConsultaCancelada()


def filtro_area(rect, geometry_field):
    if rect is None:
        return None
    coords = [rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()]
    if (not all(math.isfinite(v) for v in coords) or rect.isEmpty()
            or not (-180 <= coords[0] < coords[2] <= 180)
            or not (-90 <= coords[1] < coords[3] <= 90)):
        raise QgsProcessingException("Área inválida. Informe uma extensão com SRC definido.")
    envelope = ",".join(format(v, ".15g") for v in coords)
    return f'ST_Intersects("{geometry_field}", ST_MakeEnvelope({envelope},4674))'


def uri_wfs(endpoint, typename, sql):
    uri = QgsDataSourceUri()
    for key, value in {
        "url": endpoint, "typename": typename, "version": "2.0.0",
        "srsname": "EPSG:4674", "pagingEnabled": "true", "pageSize": "1000",
        "restrictToRequestBBOX": "1",
    }.items():
        uri.setParam(key, value)
    uri.setSql(sql)
    return uri.uri(False)


def campo(original, short, alias, kind=QVariant.String):
    """Nomes DBF explícitos: até 10 caracteres, sem perda do identificador."""
    length, precision = (24, 8) if kind == QVariant.Double else (254, 0)
    if kind in (QVariant.Int, QVariant.LongLong):
        length = 18
    return original, QgsField(short, kind, len=length, prec=precision), alias


def validar_destino(path):
    path = Path(path)
    if not path.suffix:
        path = path.with_suffix(".shp")
    if path.suffix.lower() != ".shp":
        raise QgsProcessingException("Escolha um arquivo com extensão .shp.")
    # Nunca substituir um conjunto que possa conter edições do usuário.
    for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg", ".qpj", ".qml", ".qmd"):
        if path.with_suffix(suffix).exists():
            raise QgsProcessingException("Já existe um resultado com esse nome. Escolha outro arquivo SHP.")
    return path


def exportar_shp(fontes, esquema, destino, nome, code_field, codigo, rect,
                 estilo, endpoint, filtros, context, feedback):
    """Grava primeiro em área privada; só publica após ler todas as origens."""
    destino = validar_destino(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    target_crs = QgsCoordinateReferenceSystem("EPSG:4674")
    region = QgsGeometry.fromRect(rect) if rect is not None else None
    fields = QgsFields()
    for _, field, _ in esquema:
        fields.append(field)
    count = 0
    shortened = 0
    with tempfile.TemporaryDirectory(prefix="regula_consulta_", dir=str(destino.parent)) as staging:
        stage_path = Path(staging) / destino.name
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"
        options.layerOptions = ["RESIZE=YES", "2GB_LIMIT=YES"]
        writer = QgsVectorFileWriter.create(
            str(stage_path), fields, QgsWkbTypes.MultiPolygon, target_crs,
            context.transformContext(), options,
        )
        try:
            if writer.hasError() != QgsVectorFileWriter.NoError:
                raise QgsProcessingException("Falha ao criar SHP: " + writer.errorMessage())
            for source in fontes:
                verificar_cancelamento(feedback)
                if not source.isValid():
                    raise QgsProcessingException("Falha ao consultar " + source.name() + ": " + source.error().message())
                if source.fields().lookupField(code_field) < 0:
                    raise QgsProcessingException("A origem mudou a estrutura dos dados: " + source.name())
                transform = None
                if source.crs() != target_crs:
                    transform = QgsCoordinateTransform(source.crs(), target_crs, context.transformContext())
                indexes = [source.fields().lookupField(original) for original, _, _ in esquema]
                request = QgsFeatureRequest()
                request.setFeedback(feedback)
                # Sem setLimit: percorrer a resposta inteira e todas as páginas.
                iterator = source.getFeatures(request)
                try:
                    for feature in iterator:
                        verificar_cancelamento(feedback)
                        if codigo and str(feature[code_field]).upper() != codigo.upper():
                            continue
                        geometry = QgsGeometry(feature.geometry())
                        if geometry.isNull() or geometry.isEmpty():
                            continue
                        if transform is not None:
                            geometry.transform(transform)
                        if region is not None and not geometry.intersects(region):
                            continue
                        if geometry.type() != QgsWkbTypes.PolygonGeometry:
                            raise QgsProcessingException("A origem retornou uma geometria que não é um polígono.")
                        geometry.convertToMultiType()
                        values = []
                        for index, (_, field, _) in zip(indexes, esquema):
                            value = feature[index] if index >= 0 else None
                            if QgsVariantUtils.isNull(value):
                                value = None
                            elif field.type() == QVariant.String:
                                if hasattr(value, "toString"):
                                    value = value.toString(Qt.ISODateWithMs) if isinstance(value, QDateTime) else value.toString(Qt.ISODate)
                                else:
                                    value = str(value)
                                if len(value.encode("utf-8")) > 254:
                                    value = value.encode("utf-8")[:254].decode("utf-8", errors="ignore")
                                    shortened += 1
                            values.append(value)
                        output = QgsFeature(fields)
                        output.setGeometry(geometry)
                        output.setAttributes(values)
                        if not writer.addFeature(output):
                            raise QgsProcessingException("Erro ao gravar uma feição: " + writer.lastError())
                        count += 1
                        if count % 500 == 0:
                            feedback.setProgressText(f"{count} imóveis encontrados e gravados…")
                finally:
                    iterator.close()
                verificar_cancelamento(feedback)
                errors = source.dataProvider().errors()
                if errors:
                    raise QgsProcessingException("Falha na consulta " + source.name() + ": " + "; ".join(errors))
            if not writer.flushBuffer():
                raise QgsProcessingException("Não foi possível concluir o SHP: " + writer.lastError())
        finally:
            del writer
        verificar_cancelamento(feedback)
        if not count:
            feedback.pushWarning("Nenhum imóvel encontrado para a área ou o número informado. Nenhuma camada foi adicionada.")
            return None
        # Preparar estilo/aliases antes de publicar qualquer componente.
        layer = QgsVectorLayer(str(stage_path), nome, "ogr")
        if not layer.isValid() or layer.featureCount() != count:
            raise QgsProcessingException("Falha na verificação do arquivo SHP gerado.")
        configurar_resultado(layer, esquema, estilo, endpoint, filtros)
        message, ok = layer.saveNamedStyle(str(stage_path.with_suffix(".qml")))
        if not ok:
            raise QgsProcessingException("Falha ao salvar o estilo: " + message)
        del layer
        verificar_cancelamento(feedback)
        validar_destino(destino)
        published = []
        try:
            for component in Path(staging).iterdir():
                target = destino.parent / component.name
                # rename no Windows não substitui um arquivo existente.
                os.rename(str(component), str(target))
                published.append(target)
        except Exception:
            for target in published:
                target.unlink()
            raise
    layer = QgsVectorLayer(str(destino), nome, "ogr")
    if not layer.isValid():
        raise QgsProcessingException("O SHP foi salvo, mas o QGIS não conseguiu carregá-lo: " + str(destino))
    configurar_resultado(layer, esquema, estilo, endpoint, filtros)
    context.temporaryLayerStore().addMapLayer(layer)
    if context.project() is not None:
        details = QgsProcessingContext.LayerDetails(nome, context.project(), "OUTPUT")
        details.forceName = True
        context.addLayerToLoadOnCompletion(layer.id(), details)
    if shortened:
        feedback.pushWarning(f"{shortened} textos foram abreviados ao limite de 254 bytes do formato SHP.")
    feedback.setProgress(100)
    feedback.pushInfo(f"{count} imóveis em uma única camada SHP editável: {destino}")
    return str(destino)


def configurar_resultado(layer, esquema, estilo, endpoint, filtros):
    layer.setReadOnly(False)
    estilo(layer)
    for _, field, alias in esquema:
        index = layer.fields().lookupField(field.name())
        if index >= 0:
            layer.setFieldAlias(index, alias)
    metadata = layer.metadata()
    metadata.setTitle(layer.name())
    metadata.setIdentifier(endpoint)
    metadata.setAbstract(
        "REGULA RURAL GEO — resultado SHP editável. Consulta nacional por área ou código. "
        "Somente polígonos que correspondem aos filtros, preservados inteiros, sem recorte. "
        "Dados consultados em " + QDateTime.currentDateTimeUtc().toString(Qt.ISODate) + ". "
        "Cópia local sem recarga automática; execute uma nova consulta para obter dados novos. "
        "Filtros: " + " | ".join(filtros)
    )
    layer.setMetadata(metadata)


class ConsultaShp(QgsProcessingAlgorithm):
    AREA, CODIGO, NOME, OUTPUT = "AREA", "CODIGO", "NOME", "OUTPUT"

    def group(self):
        return ""

    def groupId(self):
        return ""

    def icon(self):
        return QIcon(str(Path(__file__).with_name("icon.png")))

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterExtent(self.AREA, "Área de consulta — desenhar na tela", optional=True))
        self.addParameter(QgsProcessingParameterString(self.CODIGO, self.code_label, optional=True))
        self.addParameter(QgsProcessingParameterString(self.NOME, "Nome da camada", defaultValue=self.result_name))
        self.addParameter(QgsProcessingParameterFileDestination(
            self.OUTPUT, "Resultado editável (.shp)", fileFilter="Shapefile (*.shp)",
            defaultValue=QgsProcessing.TEMPORARY_OUTPUT,
        ))

    def prepareAlgorithm(self, parameters, context, feedback):
        self._rect = None
        value = parameters.get(self.AREA)
        if value is not None and str(value).strip():
            self._rect = self.parameterAsExtent(parameters, self.AREA, context, QgsCoordinateReferenceSystem("EPSG:4674"))
        self._codigo = self.normalizar_codigo(self.parameterAsString(parameters, self.CODIGO, context))
        self._queries = self.consultas(self._codigo, self._rect)
        self._name = self.parameterAsString(parameters, self.NOME, context).strip() or self.result_name
        self._path = validar_destino(self.parameterAsFileOutput(parameters, self.OUTPUT, context))
        return True

    def fontes(self, feedback):
        for index, (typename, sql) in enumerate(self._queries):
            verificar_cancelamento(feedback)
            feedback.pushInfo(f"Consultando a base nacional ({index + 1}/{len(self._queries)})…")
            yield QgsVectorLayer(uri_wfs(self.endpoint, typename, sql), typename, "WFS")
            feedback.setProgress(90 * (index + 1) / len(self._queries))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            verificar_cancelamento(feedback)
            result = exportar_shp(
                self.fontes(feedback), self.schema, self._path, self._name, self.code_field,
                self._codigo, self._rect, self.style, self.endpoint,
                [sql for _, sql in self._queries], context, feedback,
            )
        except ConsultaCancelada:
            return {}
        except (OSError, ValueError) as error:
            raise QgsProcessingException("Não foi possível gerar o SHP: " + str(error)) from error
        return {self.OUTPUT: result} if result else {}

    def shortHelpString(self):
        return (
            "<h3>" + self.displayName() + "</h3>"
            "<p><b>Elaboração: Douglas Nascimento.</b><br>"
            "Contato: <a href='mailto:douglas.regularural@gmail.com'>douglas.regularural@gmail.com</a></p>"
            "<p><b>Busca nacional, sem seleção de UF.</b> Desenhe uma área pelo botão à direita "
            "ou informe o código completo. Se preencher os dois campos, ambos serão usados.</p>"
            "<p>Será adicionada <b>uma única camada SHP editável</b>, somente com os imóveis "
            "encontrados. A busca por área preserva os polígonos inteiros que intersectam "
            "o retângulo. Não adiciona camadas estaduais vazias.</p>"
            "<p>" + self.style_help + "</p>"
            "<p>Em Resultado editável, escolha onde salvar o arquivo .shp. Se deixar temporário, "
            "exporte o resultado para uma pasta permanente antes de fechar o QGIS. "
            "Para copiar o Shapefile, mantenha juntos os arquivos .shp, .shx, .dbf, .prj e .cpg. "
            "O .qml guarda as cores e os nomes completos dos campos.</p>"
            "<p>Cada execução consulta a base on-line atual. O SHP é uma cópia local "
            "<b>sem recarga automática</b>, para preservar suas edições. Para atualizar os dados, "
            "execute outra consulta e use um novo nome de arquivo.</p>"
            "<p>" + self.source_help + "</p>"
        )
