"""Exporta datos depurados a un proyecto Power BI PBIP portable y editable."""
from pathlib import Path
import base64, hashlib, json, uuid
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'powerbi'
BASE = 'https://developer.microsoft.com/json-schemas/fabric/'
DEF = BASE + 'item/report/definition/'
MODEL = 'Petroleo_EDA.SemanticModel'
REPORT = 'Petroleo_EDA.Report'


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def tagged(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'petroleo-eda/' + name))


def literal(value):
    if isinstance(value, bool): s = str(value).lower()
    elif isinstance(value, (int, float)): s = str(value) + ('D' if isinstance(value, float) else 'L')
    else: s = "'" + str(value).replace("'", "''") + "'"
    return {'expr': {'Literal': {'Value': s}}}


def color(value):
    return {'solid': {'color': literal(value)}}


def field(table, name, measure=False, source=False):
    return {'Measure' if measure else 'Column': {'Expression': {'SourceRef': {'Source' if source else 'Entity': table}}, 'Property': name}}


def projection(table, name, measure=False):
    return {'field': field(table, name, measure), 'queryRef': table+'.'+name, 'nativeQueryRef': name}


def get_tables():
    prod = pd.read_csv(ROOT/'data/procesados/produccion_limpia.csv')
    price = pd.read_csv(ROOT/'data/procesados/precios_limpios.csv')
    cov = pd.read_csv(ROOT/'reportes/cobertura.csv')
    mapping = {'fecha':'Mes','activo':'Activo','crudo':'Crudo_bbl','gas':'Gas_miles_pies3',
        'crudo_diario':'Crudo_diario_bbl','gas_diario':'Gas_diario_miles_pies3',
        'conflicto_crudo':'Conflicto_crudo','conflicto_gas':'Conflicto_gas',
        'atipico_crudo_diario':'Atipico_crudo','atipico_gas_diario':'Atipico_gas',
        'n_filas_origen':'Filas_origen','filas_origen':'Referencias_origen'}
    fact = prod[list(mapping)].rename(columns=mapping)
    for c in ['Conflicto_crudo','Conflicto_gas','Atipico_crudo','Atipico_gas']: fact[c] = fact[c].astype(int)
    asset = prod[['activo','nombre_activo','catalogo_faltante']].drop_duplicates().rename(columns={
        'activo':'Activo','nombre_activo':'Nombre','catalogo_faltante':'Catalogo_faltante'})
    asset['Catalogo_faltante'] = asset.Catalogo_faltante.astype(int)
    asset['Etiqueta'] = asset.Activo + ' | ' + asset.Nombre
    dates = pd.date_range(min(price.fecha.min(),prod.fecha.min()),max(price.fecha.max(),prod.fecha.max()),freq='MS')
    month_names = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    cal = pd.DataFrame({'Mes': dates.strftime('%Y-%m-%d'), 'Anio':dates.year,
        'Mes_numero':dates.month,'Mes_nombre':[month_names[x-1] for x in dates.month],
        'Anio_mes':dates.strftime('%Y-%m'), 'Trimestre':['T'+str(x) for x in dates.quarter],
        'Dias_mes':dates.days_in_month})
    cal['Con_produccion'] = cal.Mes.isin(prod.fecha.unique()).astype(int)
    cal['Con_precio'] = cal.Mes.isin(price.fecha.unique()).astype(int)
    price = price.rename(columns={'fecha':'Mes','precio_usd_barril':'Precio_USD_bbl'})
    cov = cov.rename(columns={'fecha':'Mes','activo':'Activo','estado':'Estado',
        'crudo_valido':'Crudo_valido','gas_valido':'Gas_valido'})
    for c in ['Crudo_valido','Gas_valido']: cov[c] = cov[c].astype(int)
    return {'Produccion':fact, 'Precios':price, 'Activos':asset.reset_index(drop=True), 'Calendario':cal, 'Cobertura':cov}


MEASURES = [
 ('Crudo observado (bbl)', 'SUM(Produccion[Crudo_bbl])', '#,0.00', 'Produccion', 'Suma del volumen disponible. Los faltantes no se sustituyen por cero.'),
 ('Gas observado (miles pies3)', 'SUM(Produccion[Gas_miles_pies3])', '#,0.00', 'Produccion', 'Unidad adoptada del diccionario del proyecto; no es crudo equivalente.'),
 ('N registros', 'COUNTROWS(Produccion)', '#,0', 'Calidad', 'Filas unicas activo-mes en el contexto filtrado.'),
 ('N crudo', 'COUNT(Produccion[Crudo_bbl])', '#,0', 'Calidad', 'Numero de observaciones mensuales no vacias de crudo; por activo equivale al n del grupo.'),
 ('N gas', 'COUNT(Produccion[Gas_miles_pies3])', '#,0', 'Calidad', 'Numero de observaciones mensuales no vacias de gas.'),
 ('Dias del periodo productivo', 'CALCULATE(SUM(Calendario[Dias_mes]), KEEPFILTERS(Calendario[Con_produccion] = 1))', '#,0', 'Produccion', 'Dias de los meses seleccionados dentro de enero 2022-agosto 2026, contados una sola vez. Un activo con cobertura incompleta conserva el denominador del periodo.'),
 ('Aporte diario observado (bbl)', 'DIVIDE([Crudo observado (bbl)], [Dias del periodo productivo])', '#,0.00', 'Produccion', 'Volumen observado / dias del periodo. No es la media simple de las tasas ni un ajuste de faltantes; revisar n y cobertura al comparar activos.'),
 ('Precio promedio (USD/bbl)', 'AVERAGE(Precios[Precio_USD_bbl])', '$#,0.00', 'Precios', 'Media simple entre meses con precio; no se repite por activo, no se pondera por produccion y no equivale a ingresos.'),
 ('N meses con precio', 'COUNT(Precios[Precio_USD_bbl])', '#,0', 'Precios', 'Numero de precios mensuales validos en el periodo.'),
 ('Meses productivos sin precio', 'CALCULATE(COUNTROWS(Calendario), KEEPFILTERS(Calendario[Con_produccion] = 1), KEEPFILTERS(Calendario[Con_precio] = 0))', '#,0', 'Precios', 'Meses de la ventana productiva sin precio: agosto de 2026 en la fuente disponible.'),
 ('Activos observados', 'DISTINCTCOUNT(Produccion[Activo])', '#,0', 'Produccion', 'Activos con al menos un registro dentro de la seleccion.'),
 ('Conflictos crudo', 'SUM(Produccion[Conflicto_crudo])', '#,0', 'Calidad', 'Celdas de crudo anuladas por valores discrepantes de una misma clave.'),
 ('Conflictos gas', 'SUM(Produccion[Conflicto_gas])', '#,0', 'Calidad', 'Celdas de gas anuladas por valores discrepantes de una misma clave.'),
 ('Conflictos totales', '[Conflictos crudo] + [Conflictos gas]', '#,0', 'Calidad', 'Cuenta de celdas conflictivas, no de filas duplicadas.'),
 ('Atipicos crudo', 'SUM(Produccion[Atipico_crudo])', '#,0', 'Calidad', 'Banderas IQR calculadas previamente dentro de cada activo. Se conservan los registros.'),
 ('Atipicos gas', 'SUM(Produccion[Atipico_gas])', '#,0', 'Calidad', 'Banderas IQR del gas diario dentro de cada activo; el filtro no recalcula los limites historicos.'),
 ('Huecos internos', 'CALCULATE(COUNTROWS(Cobertura), KEEPFILTERS(Cobertura[Estado] = "sin registro interior"))', '#,0', 'Calidad', 'Meses ausentes entre el primer y ultimo registro de cada activo; no son volumen cero.'),
 ('Estado del grupo', 'VAR N = [N crudo] RETURN IF(ISBLANK(N) || N = 0, "Sin crudo valido", IF(N < 12, "PRECAUCION: n < 12", "n >= 12; revisar cobertura"))', '', 'Calidad', 'Umbral descriptivo de doce meses para advertir series cortas; no garantiza independencia ni suficiencia estadistica.'),
 ('Grupos pequenos', 'SUMX(VALUES(Activos[Activo]), VAR N = CALCULATE([N crudo]) RETURN IF(N > 0 && N < 12, 1, 0))', '#,0', 'Calidad', 'Numero de activos seleccionados con entre uno y once meses validos de crudo.'),
 ('Advertencia de grupos', 'VAR G = [Grupos pequenos] RETURN IF(ISBLANK([N crudo]) || [N crudo] = 0, "Sin datos de crudo en esta seleccion", IF(G > 0, FORMAT(G, "0") & " grupo(s) con n < 12. Interpretar con cautela.", "Revisar cobertura, faltantes y cambios de composicion."))', '', 'Calidad', 'Advertencia dinamica segun filtros. Observaciones mensuales, no muestras independientes.'),
 ('Participacion crudo', 'DIVIDE([Crudo observado (bbl)], CALCULATE([Crudo observado (bbl)], ALLSELECTED(Activos)))', '0.0%', 'Produccion', 'Fraccion del crudo observado entre los activos seleccionados, manteniendo el periodo.'),
]


def model_table(name, df):
    csv = df.to_csv(index=False, lineterminator='\n', float_format='%.9f')
    encoded = base64.b64encode(csv.encode('utf-8')).decode('ascii')
    specs = []
    columns = []
    for c in df.columns:
        dtype = 'dateTime' if c == 'Mes' else ('int64' if pd.api.types.is_integer_dtype(df[c]) else ('double' if pd.api.types.is_numeric_dtype(df[c]) else 'string'))
        mtype = {'dateTime':'type date','int64':'Int64.Type','double':'type number','string':'type text'}[dtype]
        specs.append('{"'+c+'", '+mtype+'}')
        col = {'name':c,'dataType':dtype,'sourceColumn':c,'summarizeBy':'none','lineageTag':tagged(name+'/'+c)}
        if dtype == 'dateTime': col['formatString'] = 'yyyy-MM-dd'
        if dtype == 'double': col['formatString'] = '#,0.00'
        if dtype == 'int64': col['formatString'] = '0'
        if name == 'Calendario' and c == 'Mes_nombre': col['sortByColumn'] = 'Mes_numero'
        if name == 'Calendario' and c == 'Mes': col['isKey'] = True
        if name == 'Activos' and c == 'Activo': col['isKey'] = True
        columns.append(col)
    m = ['let', '    Fuente = Csv.Document(Binary.FromText("'+encoded+'", BinaryEncoding.Base64), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        '    Encabezados = Table.PromoteHeaders(Fuente, [PromoteAllScalars=true]),',
        '    Nulos = Table.ReplaceValue(Encabezados, "", null, Replacer.ReplaceValue, Table.ColumnNames(Encabezados)),',
        '    Tipos = Table.TransformColumnTypes(Nulos, {'+', '.join(specs)+'}, "en-US")', 'in', '    Tipos']
    table = {'name':name,'lineageTag':tagged(name),'columns':columns,
        'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':m}}],
        'annotations':[{'name':'PBI_ResultType','value':'Table'}]}
    if name == 'Produccion':
        table['measures'] = [{'name':n,'expression':e,'formatString':f,'displayFolder':g,'description':d,'lineageTag':tagged('measure/'+n)} for n,e,f,g,d in MEASURES]
    (OUT/'datos').mkdir(parents=True, exist_ok=True)
    (OUT/'datos'/f'{name}.csv').write_text(csv, encoding='utf-8-sig', newline='\n')
    (OUT/'consultas_m').mkdir(exist_ok=True)
    (OUT/'consultas_m'/f'{name}.pq').write_text('\n'.join(m)+'\n',encoding='utf-8', newline='\n')
    return table


def create_model(tables):
    rels = []
    for fact, dim, col in [('Produccion','Calendario','Mes'),('Produccion','Activos','Activo'),('Precios','Calendario','Mes'),('Cobertura','Calendario','Mes'),('Cobertura','Activos','Activo')]:
        rels.append({'name':tagged(fact+'-'+dim),'fromTable':fact,'fromColumn':col,'toTable':dim,'toColumn':col,
            'fromCardinality':'many','toCardinality':'one','crossFilteringBehavior':'oneDirection','isActive':True})
    model = {'name':'Petroleo_EDA','compatibilityLevel':1567,'model':{'culture':'es-ES','sourceQueryCulture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3',
        'tables':[model_table(n,d) for n,d in tables.items()], 'relationships':rels,
        'annotations':[{'name':'PBI_QueryOrder','value':json.dumps(list(tables))}, {'name':'__PBI_TimeIntelligenceEnabled','value':'0'}]}}
    save(OUT/MODEL/'model.bim', model)
    save(OUT/MODEL/'definition.pbism', {'$schema':BASE+'item/semanticModel/definitionProperties/1.0.0/schema.json','version':'1.0','settings':{'qnaEnabled':False}})


def visual(page, name, vtype, x,y,w,h,title='',roles=None, objects=None, sort=None):
    vc = {'visualType':vtype,'drillFilterOtherVisuals':True}
    if roles:
        vc['query'] = {'queryState':{role:{'projections':[projection(*p) for p in projs]} for role,projs in roles.items()}}
        if sort: vc['query']['sortDefinition'] = {'sort':[{'field':field(*sort[:3]),'direction':sort[3]}],'isDefaultSort':False}
    vc['visualContainerObjects'] = {
        'title':[{'properties':{'show':literal(bool(title)),'text':literal(title),'fontSize':literal(13),'fontColor':color('#17324D'),'bold':literal(True)}}],
        'background':[{'properties':{'show':literal(True),'color':color('#FFFFFF'),'transparency':literal(0)}}],
        'border':[{'properties':{'show':literal(True),'color':color('#DCE5EB'),'radius':literal(8)}}]}
    if objects: vc['objects'] = objects
    save(OUT/REPORT/'definition/pages'/page/'visuals'/name/'visual.json', {'$schema':DEF+'visualContainer/2.1.0/schema.json','name':name,
        'position':{'x':x,'y':y,'z':y+x/10000,'width':w,'height':h,'tabOrder':y+x/10000},'visual':vc})


def text_box(page,name,text,x,y,w,h,size=13):
    visual(page,name,'textbox',x,y,w,h,objects={'general':[{'properties':{'paragraphs':[{'textRuns':[{'value':text,'textStyle':{'fontFamily':'Segoe UI','fontSize':str(size)+'pt','color':'#17324D'}}]}]}}]})


def slicer(page,name,table,col,x,w,default_year=False):
    objects = {'data':[{'properties':{'mode':literal('Dropdown')}}], 'selection':[{'properties':{'selectAllCheckboxEnabled':literal(True),'singleSelect':literal(False)}}]}
    if default_year:
        objects['general'] = [{'properties':{'filter':{'filter':{'Version':2,'From':[{'Name':'c','Entity':'Calendario','Type':0}],
            'Where':[{'Condition':{'In':{'Expressions':[field('c','Anio',source=True)],'Values':[[{'Literal':{'Value':'2026L'}}]]}}}]}}}}]
    visual(page,name,'slicer',x,100,w,76,{'Anio':'Año','Anio_mes':'Meses','Etiqueta':'Activo'}.get(col,col),{'Values':[(table,col,False)]},objects)


def page(name,title,year=True):
    save(OUT/REPORT/'definition/pages'/name/'page.json', {'$schema':DEF+'page/1.0.0/schema.json','name':name,'displayName':title,
        'displayOption':'FitToPage','width':1400,'height':950,'objects':{'background':[{'properties':{'color':color('#F3F6F9'),'transparency':literal(0)}}]}})
    text_box(name,'encabezado',title+' | Petróleo y gas · Ecuador',24,18,1352,67,23)
    slicer(name,'filtro_anio','Calendario','Anio',24,260,year)
    slicer(name,'filtro_meses','Calendario','Anio_mes',304,380)
    slicer(name,'filtro_activo','Activos','Etiqueta',704,672)


def card(page,name,measure,x,w=323,title=None):
    visual(page,name,'card',x,196,w,104,title or measure,{'Values':[('Produccion',measure,True)]},
        {'labels':[{'properties':{'fontSize':literal(27),'color':color('#007F7A'),'labelDisplayUnits':literal(1),'labelPrecision':literal(2)}}],
         'categoryLabels':[{'properties':{'show':literal(False)}}]})


def create_report():
    # La version del contenido PBIR es distinta de la version 4.0 de definition.pbir.
    # Referencia: microsoft/BCApps, Projects app.Report/definition/version.json.
    for folder, kind in [(REPORT, 'Report'), (MODEL, 'SemanticModel')]:
        save(OUT/folder/'.platform', {
            '$schema':BASE+'gitIntegration/platformProperties/2.0.0/schema.json',
            'metadata':{'type':kind,'displayName':'Petroleo EDA'},
            'config':{'version':'2.0','logicalId':tagged('platform/'+kind)}})
    save(OUT/'Petroleo_EDA.pbip', {'$schema':BASE+'pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':REPORT}}],'settings':{'enableAutoRecovery':True}})
    save(OUT/REPORT/'definition.pbir', {'$schema':BASE+'item/report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../'+MODEL}}})
    save(OUT/REPORT/'definition/version.json', {'$schema':DEF+'versionMetadata/1.0.0/schema.json','version':'2.0.0'})
    save(OUT/REPORT/'definition/report.json', {'$schema':DEF+'report/1.0.0/schema.json','layoutOptimization':'None',
        'themeCollection':{'baseTheme':{'name':'CY24SU06','reportVersionAtImport':'5.55','type':'SharedResources'}}})
    save(OUT/REPORT/'definition/pages/pages.json', {'$schema':DEF+'pagesMetadata/1.1.0/schema.json','pageOrder':['Panorama','Calidad','Detalle'],'activePageName':'Panorama'})
    page('Panorama','01 · Panorama productivo')
    for name,measure,x in [('crudo','Crudo observado (bbl)',24),('diario','Aporte diario observado (bbl)',367),('precio','Precio promedio (USD/bbl)',710),('n','N crudo',1053)]:card('Panorama',name,measure,x)
    visual('Panorama','serie_crudo','lineChart',24,320,815,270,'Producción mensual observada · bbl',
        {'Category':[('Calendario','Anio_mes',False)],'Y':[('Produccion','Crudo observado (bbl)',True)]},sort=('Calendario','Anio_mes',False,'Ascending'))
    visual('Panorama','serie_precio','lineChart',24,610,815,240,'Precio de referencia · USD/bbl · no cambia por activo',
        {'Category':[('Calendario','Anio_mes',False)],'Y':[('Produccion','Precio promedio (USD/bbl)',True)]},sort=('Calendario','Anio_mes',False,'Ascending'))
    visual('Panorama','ranking','clusteredBarChart',859,320,517,530,'Crudo observado por activo · bbl',
        {'Category':[('Activos','Activo',False)],'Y':[('Produccion','Crudo observado (bbl)',True)],'Tooltips':[('Produccion','N crudo',True),('Produccion','Participacion crudo',True)]},sort=('Produccion','Crudo observado (bbl)',True,'Descending'))
    visual('Panorama','advertencia','card',24,867,1352,64,'Grupos pequeños: n = meses con crudo válido',{'Values':[('Produccion','Advertencia de grupos',True)]},
        {'labels':[{'properties':{'fontSize':literal(13),'color':color('#9A5600')}}],'categoryLabels':[{'properties':{'show':literal(False)}}]})
    page('Calidad','02 · Calidad y tamaño de grupos',False)
    for name,measure,x in [('conflictos','Conflictos totales',24),('huecos','Huecos internos',367),('atipicos','Atipicos crudo',710),('precio_n','Meses productivos sin precio',1053)]:card('Calidad',name,measure,x)
    visual('Calidad','grupos','tableEx',24,320,1352,400,'Tamaño de grupos, cobertura y alertas por activo',{'Values':[
        ('Activos','Etiqueta',False),('Produccion','N crudo',True),('Produccion','N gas',True),('Produccion','Huecos internos',True),
        ('Produccion','Conflictos totales',True),('Produccion','Atipicos crudo',True),('Produccion','Estado del grupo',True)]})
    text_box('Calidad','criterios','LECTURA DE CALIDAD\nLos n son meses válidos por activo; n < 12 activa una precaución descriptiva. Los meses no son observaciones independientes.\nLos conflictos permanecen vacíos; los atípicos IQR se conservan. Las banderas IQR usan el historial completo de cada activo.\nHay 18 huecos internos en el historial y 3 celdas conflictivas. AB16 tiene nombre no resuelto en el catálogo.\nAgosto 2026 no tiene precio. El precio es una referencia mensual; multiplicarlo por producción no demuestra ingresos.',24,740,1352,190,13)
    page('Detalle','03 · Detalle auditable',False)
    visual('Detalle','registros','tableEx',24,196,1352,650,'Una fila por activo y mes · vacíos conservados',{'Values':[
        ('Produccion','Mes',False),('Produccion','Activo',False),('Produccion','Crudo_bbl',False),('Produccion','Gas_miles_pies3',False),
        ('Produccion','Conflicto_crudo',False),('Produccion','Conflicto_gas',False),('Produccion','Atipico_crudo',False),('Produccion','Referencias_origen',False)]},sort=('Produccion','Mes',False,'Ascending'))
    text_box('Detalle','fuentes','Fuentes: los tres archivos entregados por el autor. Producción: enero 2022–agosto 2026; precios: enero 2021–julio 2026.\nReferencias_origen identifica filas del Excel original. Los filtros se manejan de forma independiente en cada página.',24,866,1352,66,12)


def create_docs(tables):
    dax = '\n\n'.join('// '+d+'\n'+n+' =\n'+e for n,e,f,g,d in MEASURES)
    (OUT/'Medidas_DAX.txt').write_text(dax+'\n',encoding='utf-8-sig', newline='\n')
    (OUT/'LEEME_POWER_BI.txt').write_text('''PROYECTO POWER BI · PETRÓLEO Y GAS
Autor: Erick Leandro Ruano Lara

CORRECCIÓN DE COMPATIBILIDAD
Esta revisión corrige la versión del contenido PBIR a 2.0.0, incorpora los metadatos .platform y actualiza el índice de páginas. La versión de definition.pbir permanece en 4.0 porque corresponde a un archivo distinto.

ABRIR Y ANALIZAR
1. Cierra el informe anterior y extrae TODO el ZIP en una carpeta local NUEVA. Conserva juntas las carpetas .Report y .SemanticModel.
2. Abre Petroleo_EDA.pbip con Power BI Desktop actualizado. También puedes abrir Petroleo_EDA.Report/definition.pbir.
3. Pulsa Inicio > Actualizar para cargar los datos incorporados. El proyecto PBIP no incluye caché binaria; los visuales necesitan esta primera actualización.
4. Analiza las páginas Panorama, Calidad y Detalle. Panorama inicia en 2026; las otras páginas muestran el historial. Los filtros de cada página son independientes.
5. Si deseas UN SOLO ARCHIVO, después de actualizar utiliza Archivo > Guardar como > archivo .pbix. No renombres la extensión .pbip a .pbix.
Si tu versión solicita habilitar proyectos PBIP en Opciones > Características de versión preliminar, habilita esa opción y reinicia Desktop.

QUÉ INCLUYE
Cinco tablas importadas, cinco relaciones uno a varios y medidas DAX. Los datos están incorporados en las consultas M como CSV UTF-8 codificado en Base64: no hay rutas absolutas, credenciales ni descargas necesarias para actualizarlos.
Los CSV de datos/ y las consultas de consultas_m/ son copias legibles de respaldo. Modificar un CSV no actualiza automáticamente el modelo: para cambiar los datos, regenera desde el repositorio con python -m src.export_powerbi o edita la consulta M correspondiente.

MODELO
Calendario[Mes] 1 -> * Produccion[Mes]
Activos[Activo] 1 -> * Produccion[Activo]
Calendario[Mes] 1 -> * Precios[Mes]
Calendario[Mes] 1 -> * Cobertura[Mes]
Activos[Activo] 1 -> * Cobertura[Activo]
Todas las relaciones filtran en una sola dirección, desde la dimensión. El activo no filtra la tabla de precios porque el precio de referencia no es específico por activo. Calendario tiene granularidad mensual; no se marca como calendario diario ni se usa DATEADD sobre una serie diaria inexistente.

INTERPRETACIÓN
Crudo en barriles mensuales; gas en miles de pies cúbicos mensuales, según la convención documentada en el proyecto. Precio en USD por barril. No se interpreta precio por producción como ingresos.
Aporte diario observado = volumen disponible / días de los meses seleccionados dentro de enero 2022–agosto 2026. Los días no se repiten por activo. Con huecos o cobertura parcial, este aporte no estima la producción faltante; consulta n y Calidad.
Los n son observaciones activo-mes válidas. Menos de 12 meses activa una precaución descriptiva, no una prueba estadística. El total de N crudo suma activo-mes; no son meses calendario distintos.
No se unió AB16 con AIT. Un mes ausente no es cero. Se conservan ceros legítimos. Tres celdas en conflicto se dejan vacías. Los atípicos se conservan y sus límites IQR históricos no se recalculan al filtrar.
Las series agregadas pueden cambiar porque cambia la composición de activos. Las comparaciones causales o interanuales requieren cobertura y activos comunes; véase el informe EDA original.

CONTROL ESPERADO
Historial: Produccion 789 filas; Precios 67; Activos 16; Calendario 68; Cobertura 896.
Crudo válido: 788; gas válido: 787. Conflictos: 1 crudo y 2 gas. Huecos internos: 18.
Panorama, 2026, todos los activos: 120 registros, 88.304.451,13 bbl, 243 días y 363.392,80 bbl/día.
Precio promedio enero–julio 2026: 75,897142857 USD/bbl, siete meses; agosto permanece sin precio.

VALIDACIÓN Y ALCANCE
Se validan los datos, claves, relaciones, consultas incorporadas y esquemas JSON públicos de PBIP/PBIR. El modelo model.bim también se deserializó correctamente con las bibliotecas Tabular de Microsoft en modo PowerBI (5 tablas, 5 relaciones y 21 medidas). Esto no ejecuta las medidas DAX. Consulta validacion_powerbi.json para los controles realmente ejecutados.
La apertura, actualización y representación visual dentro de Power BI Desktop no se verificaron en esta sesión porque el controlador de aplicaciones no pudo iniciarse. El archivo entregado es un proyecto PBIP editable; no se presenta como un PBIX ya actualizado.

FUENTES Y DOCUMENTACIÓN
Repositorio: https://github.com/residenterick681/proyecto_final_Dashboard_EDA
Dashboard web: https://residenterick681.github.io/proyecto_final_Dashboard_EDA/
Estructura PBIR: https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report
Modelo PBIP: https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset
''',encoding='utf-8-sig', newline='\n')
    manifest = {'tablas':{n:len(df) for n,df in tables.items()},'medidas':len(MEASURES),'paginas':3,
        'sha256_csv':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((OUT/'datos').glob('*.csv'))}}
    save(OUT/'manifest.json',manifest)


def main():
    OUT.mkdir(exist_ok=True)
    tables = get_tables()
    create_model(tables)
    create_report()
    create_docs(tables)
    print(json.dumps({'carpeta':str(OUT),'tablas':{n:len(d) for n,d in tables.items()},'medidas':len(MEASURES)},ensure_ascii=False))

if __name__ == '__main__': main()
