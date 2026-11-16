# REGULA RURAL GEO

**Elaboração: Regula Rural e Douglas Nascimento**  
**Contato:** douglas.regularural@gmail.com

QGIS Processing tools to query Brazilian rural property boundaries from the public SIGEF/INCRA and CAR/SICAR services. Search by map extent or registration code and receive a single editable Shapefile. The interface is in Portuguese and coverage is Brazil.

## Ferramentas

- **Consultar base GEO INCRA:** consulta nacional do SIGEF por área ou UUID da parcela. Resultado laranja sólido com 50% de transparência.
- **Consultar base CAR:** consulta nacional por área ou número federal completo do CAR. Resultado verde sólido com 50% de transparência.

Cada consulta retorna uma única camada, somente com os imóveis encontrados. As fontes estaduais do CAR são consultadas internamente, sem criar 27 camadas no projeto. Os filtros são aplicados no servidor e conferidos antes da gravação local. São preservados os polígonos inteiros que intersectam o retângulo; não se trata de recorte geométrico.

## Instalação e uso

1. No QGIS, abra **Complementos → Gerenciar e Instalar Complementos → Instalar a partir de ZIP** e escolha o pacote `REGULA_RURAL_GEO_0.4.0.zip`.
2. Habilite **REGULA RURAL GEO**.
3. Abra **Processamento → Caixa de Ferramentas → REGULA RURAL GEO**.
4. Desenhe uma área pelo botão à direita ou informe o código completo. Se ambos forem preenchidos, ambos serão aplicados.
5. No campo **Resultado editável (.shp)**, escolha uma pasta permanente e um nome novo.
6. Execute. A camada resultante pode ser editada, copiada e salva normalmente no QGIS.

Se optar por saída temporária, exporte o resultado antes de fechar o QGIS. Nenhuma camada é adicionada quando não há correspondências. Cancelamentos ou falhas em qualquer fonte não publicam arquivos parciais. Arquivos existentes não são sobrescritos.

## Arquivos e atualização

O Shapefile precisa dos componentes `.shp`, `.shx`, `.dbf`, `.prj` e `.cpg`. Mantenha-os juntos ao copiar. O `.qml` acompanha o estilo e os nomes descritivos dos campos. Os nomes físicos dos campos têm até 10 caracteres; o CAR completo está em `cod_imovel` e o UUID SIGEF em `cod_parcel`. Datas usam texto ISO 8601. Textos acima de 254 bytes são abreviados com aviso no log, por limitação do formato.

Cada execução consulta os dados disponíveis on-line. O resultado é uma cópia local **sem atualização automática**, para preservar as edições do usuário. Execute outra consulta e salve com outro nome para obter dados novos. A frequência de publicação dos dados depende dos órgãos responsáveis.

## Requisitos e fontes

- QGIS 3.40 a 3.99; validado no QGIS 3.44.15 para Windows. QGIS 4 ainda não é suportado.
- Internet para consultar. Apenas bibliotecas fornecidas pelo próprio QGIS; sem dependências Python adicionais ou senha dos serviços.
- SIGEF: <https://geoportal.incra.gov.br/geoserver/ows>, camada `geonode:sigef_geo`.
- CAR: <https://geoserver.car.gov.br/geoserver/sicar/wfs>, camadas `sicar:sicar_imoveis_[uf]`.
- Inclui todas as situações publicadas; confira os campos de situação e condição. Pode haver cadastros cancelados.
- Não inclui SNCI, assentamentos, quilombolas, APP, reserva legal ou documentos dos imóveis.

Este é um complemento independente, sem vínculo oficial com INCRA, SICAR ou QGIS. A consulta nacional por área pode levar alguns minutos, conforme a extensão e a disponibilidade dos servidores.

## Validação da versão 0.4.0

Consultas reais por número em MT e SP, consulta SIGEF por UUID e consulta CAR por área nas 27 fontes. Verificados: resultado único, correspondência espacial, identificadores completos, edição e gravação de atributos, reabertura do SHP e do projeto, cores/transparência, resultado vazio, cancelamento e falha parcial.

## Licença

Código sob licença MIT; veja `LICENSE`. Créditos de elaboração: Regula Rural e Douglas Nascimento.
