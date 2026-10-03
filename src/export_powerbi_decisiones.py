"""Power BI para decisiones. Conserva el proyecto básico como respaldo."""
from pathlib import Path
import hashlib
import json
import pandas as pd
from . import export_powerbi as b

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'powerbi_decisiones'
REPORT = 'Petroleo_Decisiones.Report'
MODEL = 'Petroleo_Decisiones.SemanticModel'
NAVY, INK, CYAN, TEAL, CORAL, AMBER, VIOLET = '#0C1630', '#172745', '#007EB5', '#008C72', '#DC3156', '#F2AC20', '#7955C8'
PALETTE = [TEAL, CORAL, CYAN, VIOLET, AMBER, '#007C91', '#DA6598', '#64748B', '#799F21', '#C06418', '#3954B7', '#9F5477', '#39966D', '#8C7B42', '#758DA8', '#B697CC']
F, L, C, save = b.field, b.literal, b.color, b.save


def get_tables():
    tables = b.get_tables()
    comp = pd.read_csv(ROOT/'reportes/comparacion_interanual.csv').rename(columns={
        'activo':'Activo', 'n_actual':'N_2026', 'n_anterior':'N_2025',
        'diario_actual':'Bpd_2026', 'diario_anterior':'Bpd_2025',
        'cambio_pct':'Cambio_pct', 'cambio_diario':'Cambio_bpd'})
    comp['Cambio_pct'] /= 100
    comp['Resultado'] = comp.Cambio_bpd.map(lambda x: 'Aumento' if x > 0 else ('Descenso' if x < 0 else 'Sin cambio'))
    comp['Prioridad'] = comp.Cambio_bpd.map(lambda x: '1 · Investigar caída' if x <= -500 else ('2 · Vigilar descenso' if x < 0 else ('3 · Sostener aumento' if x >= 3000 else '4 · Seguir evolución')))
    tables['Comparacion'] = comp
    prod = pd.read_csv(ROOT/'data/procesados/produccion_limpia.csv')
    cut = prod[prod.activo.isin(comp.Activo) & prod.anio.isin([2025,2026]) & prod.mes.le(8)]
    serie = cut.pivot(index=['activo','mes'], columns='anio', values='crudo').reset_index()
    serie.columns = ['Activo','Mes_numero','Crudo_2025','Crudo_2026']
    serie['Dias_mes'] = pd.to_datetime('2026-'+serie.Mes_numero.astype(str)+'-01').dt.days_in_month
    months = ['ene','feb','mar','abr','may','jun','jul','ago']
    serie['Mes_nombre'] = serie.Mes_numero.map(lambda x:months[x-1])
    tables['SerieComparable'] = serie
    cohort = pd.read_csv(ROOT/'reportes/serie_cohorte.csv')
    tables['Cohorte'] = cohort[['fecha','crudo','dias_mes','n_activos']].rename(columns={'fecha':'Mes','crudo':'Crudo_bbl','dias_mes':'Dias_mes','n_activos':'N_activos'})
    changes = pd.read_csv(ROOT/'reportes/cambios_mensuales.csv')
    tables['Cambios'] = changes[['fecha','cambio_crudo_pct','cambio_precio_pct']].rename(columns={'fecha':'Mes','cambio_crudo_pct':'Cambio_crudo','cambio_precio_pct':'Cambio_precio'})
    # En el pipeline los cambios están en puntos porcentuales; DAX usa fracciones.
    tables['Cambios'][['Cambio_crudo','Cambio_precio']] /= 100
    tables['Activos']['Grupo_volumen'] = tables['Activos'].Activo.map(lambda a: 'SA + AU + SH' if a in ['SA','AU','SH'] else 'Resto de activos')
    return tables


EXTRA = []
def m(name, expression, fmt='#,0', folder='Decisiones', description=''):
    EXTRA.append((name,expression,fmt,folder,description or name))

m('Comparable 2026', 'SUM(Comparacion[Bpd_2026])', '#,0', description='Enero-agosto 2026; mismos activos y 243 días que en 2025. Suma de tasas con denominador idéntico.')
m('Comparable 2025', 'SUM(Comparacion[Bpd_2025])', '#,0')
m('Cambio comparable bpd', '[Comparable 2026] - [Comparable 2025]', '+#,0;-#,0;0')
m('Cambio comparable pct', 'DIVIDE([Cambio comparable bpd], [Comparable 2025])', '+0.0%;-0.0%;0.0%')
m('Activos comparables', 'COUNTROWS(Comparacion)')
m('Activos en descenso', 'COALESCE(CALCULATE(COUNTROWS(Comparacion), KEEPFILTERS(Comparacion[Cambio_bpd] < 0)), 0)')
m('Activos en aumento', 'COALESCE(CALCULATE(COUNTROWS(Comparacion), KEEPFILTERS(Comparacion[Cambio_bpd] > 0)), 0)')
m('Impacto absoluto bpd', 'ABS([Cambio comparable bpd])', '#,0')
m('N comparable 2026', 'SUM(Comparacion[N_2026])')
m('N comparable 2025', 'SUM(Comparacion[N_2025])')
m('Aumentos bpd', 'CALCULATE([Cambio comparable bpd], KEEPFILTERS(Comparacion[Cambio_bpd] >= 0))', '+#,0;-#,0;0')
m('Descensos bpd', 'CALCULATE([Cambio comparable bpd], KEEPFILTERS(Comparacion[Cambio_bpd] < 0))', '+#,0;-#,0;0')
m('Diario comparable 2025', 'DIVIDE(SUM(SerieComparable[Crudo_2025]), SUMX(VALUES(SerieComparable[Mes_numero]), CALCULATE(MAX(SerieComparable[Dias_mes]))))', '#,0')
m('Diario comparable 2026', 'DIVIDE(SUM(SerieComparable[Crudo_2026]), SUMX(VALUES(SerieComparable[Mes_numero]), CALCULATE(MAX(SerieComparable[Dias_mes]))))', '#,0')
m('Variacion sin julio', 'VAR A = CALCULATE(SUM(SerieComparable[Crudo_2026]), KEEPFILTERS(SerieComparable[Mes_numero] <> 7)) VAR B = CALCULATE(SUM(SerieComparable[Crudo_2025]), KEEPFILTERS(SerieComparable[Mes_numero] <> 7)) RETURN IF(B>0,DIVIDE(A,B)-1)', '+0.0%;-0.0%;0.0%', description='Sensibilidad: excluye julio de ambos años; siete meses y 212 días por año. No reemplaza la comparación principal completa.')
m('Caida prioritaria', 'VAR T = TOPN(1, FILTER(Comparacion, Comparacion[Cambio_bpd] < 0), Comparacion[Cambio_bpd], ASC, Comparacion[Activo], ASC) RETURN IF(COUNTROWS(T)=0,"Sin descensos en selección",CONCATENATEX(T,Comparacion[Activo] & " | " & FORMAT(Comparacion[Cambio_bpd],"#,0") & " bbl/día"))', '')
m('Crudo 2026', 'CALCULATE([Crudo observado (bbl)], KEEPFILTERS(Calendario[Anio]=2026))', '#,0', 'Concentracion')
m('Diario 2026', 'CALCULATE([Aporte diario observado (bbl)], KEEPFILTERS(Calendario[Anio]=2026))', '#,0', 'Concentracion')
m('Participacion 2026', 'DIVIDE([Crudo 2026], CALCULATE([Crudo 2026], ALLSELECTED(Activos)))', '0.0%', 'Concentracion')
m('Participacion tres activos', 'DIVIDE(CALCULATE([Crudo 2026], KEEPFILTERS(Activos[Grupo_volumen]="SA + AU + SH")), [Crudo 2026])', '0.0%', 'Concentracion', 'Participación de SA/AU/SH entre los activos seleccionados. Grupo fijo, no ranking recalculado.')
m('Activos 2026', 'CALCULATE([Activos observados], KEEPFILTERS(Calendario[Anio]=2026))', '#,0', 'Concentracion')
m('N 2026', 'CALCULATE([N crudo], KEEPFILTERS(Calendario[Anio]=2026))', '#,0', 'Concentracion')
m('Diario cohorte', 'DIVIDE(SUM(Cohorte[Crudo_bbl]), SUM(Cohorte[Dias_mes]))', '#,0', 'Tendencia', 'Once activos completos durante 56 meses. No depende del filtro Activos.')
m('N pares mensuales', 'COUNTROWS(Cambios)', '#,0', 'Tendencia')
m('Cambio precio mensual', 'AVERAGE(Cambios[Cambio_precio])', '0.0%', 'Tendencia')
m('Cambio crudo mensual', 'AVERAGE(Cambios[Cambio_crudo])', '0.0%', 'Tendencia')
m('Correlacion cambios', '''VAR T = Cambios
VAR N = COUNTROWS(T)
VAR SX = SUMX(T,Cambios[Cambio_precio])
VAR SY = SUMX(T,Cambios[Cambio_crudo])
VAR SXY = SUMX(T,Cambios[Cambio_precio]*Cambios[Cambio_crudo])
VAR SXX = SUMX(T,Cambios[Cambio_precio]^2)
VAR SYY = SUMX(T,Cambios[Cambio_crudo]^2)
VAR D = MAX(0,(N*SXX-SX^2)*(N*SYY-SY^2))
RETURN IF(N>=12,DIVIDE(N*SXY-SX*SY,SQRT(D)))''', '0.000', 'Tendencia', 'Pearson sobre cambios mensuales pareados. Se oculta con n<12; no demuestra causalidad ni independencia temporal.')
m('Aviso pares', 'IF([N pares mensuales]<12,"PRECAUCIÓN: menos de 12 pares; r se oculta.","Asociación descriptiva; no identifica causalidad ni rentabilidad.")', '', 'Tendencia')
m('Meses cohorte', 'COUNTROWS(Cohorte)', '#,0', 'Tendencia')
m('Celdas cobertura', 'COUNTROWS(Cobertura)', '#,0', 'Calidad')
m('Meses esperados por activo', 'CALCULATE(COUNTROWS(Cobertura), KEEPFILTERS(Cobertura[Estado] <> "fuera de cobertura observada"))', '#,0', 'Calidad')
m('Cobertura crudo pct', 'DIVIDE(SUM(Cobertura[Crudo_valido]), [Meses esperados por activo])', '0.0%', 'Calidad', 'Meses con crudo válido / meses entre primer y último registro del activo. No penaliza meses fuera de su cobertura observada.')
m('Color cobertura', 'VAR P = [Cobertura crudo pct] RETURN IF(ISBLANK(P),"#E8EDF5",IF(P>=0.99,"#A4EAD6",IF(P>=0.90,"#FFE0A0","#FFADB9")))', '', 'Calidad')
m('Activos sin catalogo', 'SUMX(VALUES(Activos[Activo]), IF(CALCULATE([N registros])>0,CALCULATE(MAX(Activos[Catalogo_faltante])),0))', '#,0', 'Calidad')
m('Huecos visibles', 'IF([Huecos internos]>0,[Huecos internos])', '#,0', 'Calidad')
m('Conflictos crudo visibles', 'IF([Conflictos crudo]>0,[Conflictos crudo])', '#,0', 'Calidad')
m('Conflictos gas visibles', 'IF([Conflictos gas]>0,[Conflictos gas])', '#,0', 'Calidad')


def create_model(tables):
    old = (b.OUT,b.MEASURES)
    b.OUT,b.MEASURES = OUT,b.MEASURES+EXTRA
    try:
        model_tables = [b.model_table(n,d) for n,d in tables.items()]
    finally:
        b.OUT,b.MEASURES = old
    for tab in model_tables:
        if tab['name']=='SerieComparable':
            next(c for c in tab['columns'] if c['name']=='Mes_nombre')['sortByColumn']='Mes_numero'
    rels = [('Produccion','Calendario','Mes'),('Produccion','Activos','Activo'),('Precios','Calendario','Mes'),('Cobertura','Calendario','Mes'),('Cobertura','Activos','Activo'),('Comparacion','Activos','Activo'),('SerieComparable','Activos','Activo'),('Cohorte','Calendario','Mes'),('Cambios','Calendario','Mes')]
    model = {'name':'Petroleo_Decisiones','compatibilityLevel':1567,'model':{'culture':'es-ES','sourceQueryCulture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','tables':model_tables,
        'relationships':[{'name':b.tagged('decisiones/'+fact+dim),'fromTable':fact,'fromColumn':c,'toTable':dim,'toColumn':c,'fromCardinality':'many','toCardinality':'one','crossFilteringBehavior':'oneDirection','isActive':True} for fact,dim,c in rels],
        'annotations':[{'name':'PBI_QueryOrder','value':json.dumps(list(tables))},{'name':'__PBI_TimeIntelligenceEnabled','value':'0'}]}}
    save(OUT/MODEL/'model.bim',model)
    save(OUT/MODEL/'definition.pbism',{'$schema':b.BASE+'item/semanticModel/definitionProperties/1.0.0/schema.json','version':'1.0','settings':{'qnaEnabled':False}})


def ms(*names): return [('Produccion',n,True) for n in names]
def col(t,n): return [(t,n,False)]
def props(**kwargs): return [{'properties':{k:L(v) for k,v in kwargs.items()}}]


def visual(page,name,kind,x,y,w,h,title='',roles=None,objects=None,sort=None,bg='#FFFFFF',accent=None):
    v={'visualType':kind,'drillFilterOtherVisuals':True}
    if roles:
        v['query']={'queryState':{r:{'projections':[b.projection(*p) for p in ps]} for r,ps in roles.items()}}
        if sort:v['query']['sortDefinition']={'sort':[{'field':F(*sort[:3]),'direction':sort[3]}],'isDefaultSort':False}
    v['visualContainerObjects']={
        'title':[{'properties':{'show':L(bool(title)),'text':L(title),'fontSize':L(13),'fontColor':C(INK),'bold':L(True)}}],
        'background':[{'properties':{'show':L(True),'color':C(bg),'transparency':L(0)}}],
        'border':[{'properties':{'show':L(True),'color':C(accent or bg),'radius':L(12)}}],
        'general':[{'properties':{'altText':L(title or name)}}]}
    if kind=='textbox':v['visualContainerObjects']['padding']=props(top=2,bottom=2,left=8,right=8)
    if objects:v['objects']=objects
    path=OUT/REPORT/'definition/pages'/page/'visuals'/name/'visual.json'
    save(path,{'$schema':b.DEF+'visualContainer/2.1.0/schema.json','name':name,'position':{'x':x,'y':y,'z':y+x/10000,'width':w,'height':h,'tabOrder':y+x/10000},'visual':v})


def text(page,name,txt,x,y,w,h,size=13,fg='#FFFFFF',bg=NAVY):
    paragraphs=[{'textRuns':[{'value':line,'textStyle':{'fontFamily':'Segoe UI','fontSize':str(size)+'pt','color':fg}}]} for line in txt.split('\n')]
    visual(page,name,'textbox',x,y,w,h,objects={'general':[{'properties':{'paragraphs':paragraphs}}]},bg=bg)


def card(page,name,measure,x,y,w=370,h=112,title=None,ink=CYAN,size=32):
    precision = 3 if measure=='Correlacion cambios' else (2 if measure=='Precio promedio (USD/bbl)' else (1 if measure in ['Cambio comparable pct','Participacion tres activos','Variacion sin julio'] else 0))
    visual(page,name,'card',x,y,w,h,measure if title is None else title,{'Values':ms(measure)},
        {'labels':[{'properties':{'fontSize':L(size),'color':C(ink),'labelDisplayUnits':L(1),'labelPrecision':L(precision)}}], 'categoryLabels':props(show=False)},accent=ink)


def slicer(page,name,table,column,x,y,w=440,title='Filtrar activos'):
    visual(page,name,'slicer',x,y,w,76,title,{'Values':col(table,column)}, {'data':props(mode='Dropdown'),'header':props(show=False),'selection':props(selectAllCheckboxEnabled=True,singleSelect=False)})


def chart(page,name,kind,x,y,w,h,title,roles,colors=None,sort=None,objects=None):
    obj={}
    if kind in ['lineChart','clusteredBarChart','barChart','clusteredColumnChart','columnChart','scatterChart','waterfallChart']:
        obj.update({'categoryAxis':[{'properties':{'show':L(True),'fontSize':L(10),'labelColor':C(INK),'preferredCategoryWidth':L(10)}}],
                    'valueAxis':[{'properties':{'show':L(True),'fontSize':L(10),'labelColor':C(INK)}}]})
    if kind in ['barChart','clusteredBarChart','clusteredColumnChart','columnChart','waterfallChart']:
        obj['labels']=props(show=True,fontSize=10,labelDisplayUnits=1,labelPrecision=0)
    if kind=='lineChart':obj['lineStyles']=props(strokeWidth=3)
    obj['legend']=[{'properties':{'show':L('Series' in roles or len(roles.get('Y',[]))>1 or kind in ['donutChart','treemap']),'fontSize':L(10),'labelColor':C(INK)}}]
    if colors:
        obj['dataPoint']=[]
        for i,co in enumerate(colors):
            item={'properties':{'fill':C(co)}}
            ys=roles.get('Y',[])
            if len(ys)>1:item['selector']={'metadata':ys[i][0]+'.'+ys[i][1]}
            elif i>0:continue
            else:item['properties']={'defaultColor':C(co)}
            obj['dataPoint'].append(item)
    if objects:obj.update(objects)
    visual(page,name,kind,x,y,w,h,title,roles,obj,sort)


PAGES=[('Decidir','01 · Decidir'),('Priorizar','02 · Priorizar activos'),('Proteger','03 · Proteger volumen'),('Tendencia','04 · Tendencia y precio'),('Calidad','05 · Calidad para decidir')]


def page(name,title,subtitle,index):
    save(OUT/REPORT/'definition/pages'/name/'page.json',{'$schema':b.DEF+'page/1.0.0/schema.json','name':name,'displayName':title,'displayOption':'FitToPage','width':1600,'height':1000,
        'objects':{'background':[{'properties':{'color':C(NAVY),'transparency':L(0)}}]}})
    text(name,'titulo',title.upper(),28,6,1230,60,27)
    text(name,'grupo','GRUPO 5  /  ECUADOR',1280,24,292,40,13,fg='#58DCE5')
    text(name,'subtitulo',subtitle,28,67,1544,43,12,fg='#CBD9F2')
    text(name,'pie',f'{index}/5   •   Petróleo y gas  |  Análisis para decidir  •   Usa las pestañas inferiores para navegar.  •   Ctrl + clic permite selección múltiple.',28,960,1544,38,10,fg='#B3C5E3')


def create_report():
    for folder,kind in [(REPORT,'Report'),(MODEL,'SemanticModel')]:
        save(OUT/folder/'.platform',{'$schema':b.BASE+'gitIntegration/platformProperties/2.0.0/schema.json','metadata':{'type':kind,'displayName':'Petróleo · Decisiones · Grupo 5'},'config':{'version':'2.0','logicalId':b.tagged('decisiones/platform/'+kind)}})
    save(OUT/'Petroleo_Decisiones.pbip',{'$schema':b.BASE+'pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':REPORT}}],'settings':{'enableAutoRecovery':True}})
    save(OUT/REPORT/'definition.pbir',{'$schema':b.BASE+'item/report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../'+MODEL}}})
    save(OUT/REPORT/'definition/version.json',{'$schema':b.DEF+'versionMetadata/1.0.0/schema.json','version':'2.0.0'})
    theme_name='Grupo5-Decisiones-9f245dc8.json'
    save(OUT/REPORT/'StaticResources/RegisteredResources'/theme_name,{'name':theme_name,'dataColors':PALETTE,'good':TEAL,'bad':CORAL,'neutral':AMBER,'background':'#FFFFFF','foreground':INK,'tableAccent':CYAN,'textClasses':{'title':{'fontFace':'Segoe UI','fontSize':13,'color':INK},'label':{'fontFace':'Segoe UI','fontSize':11,'color':INK},'callout':{'fontFace':'Segoe UI','fontSize':32,'color':CYAN}}})
    save(OUT/REPORT/'definition/report.json',{'$schema':b.DEF+'report/1.0.0/schema.json','layoutOptimization':'None','themeCollection':{'baseTheme':{'name':'CY24SU06','reportVersionAtImport':'5.55','type':'SharedResources'},'customTheme':{'name':theme_name,'reportVersionAtImport':'5.55','type':'RegisteredResources'}},'resourcePackages':[{'name':'RegisteredResources','type':'RegisteredResources','items':[{'name':theme_name,'path':theme_name,'type':'CustomTheme'}]}]})
    save(OUT/REPORT/'definition/pages/pages.json',{'$schema':b.DEF+'pagesMetadata/1.1.0/schema.json','pageOrder':[p for p,t in PAGES],'activePageName':'Decidir'})

    p='Decidir'
    page(p,PAGES[0][1],'¿Dónde sostener el aumento y dónde investigar?  •  Comparación fija: enero–agosto 2026 frente a enero–agosto 2025.',1)
    slicer(p,'activos','Activos','Etiqueta',28,120,570)
    text(p,'alcance','El aumento depende de la baja base de julio 2025; revisar antes de declarar mejora.\n14 activos · 243 días/año · n = 8 por activo/año (< 12).',622,121,950,75,13,fg='#FFD47A',bg='#1B2946')
    for name,measure,x,title,ink in [('nivel','Comparable 2026',28,'Producción comparable · bbl/día',CYAN),('variacion','Cambio comparable pct',420,'Variación frente a 2025 · %',TEAL),('aporte','Variacion sin julio',812,'Sin julio en ambos años · sensibilidad',CORAL),('caidas','Activos en descenso',1204,'Activos en descenso',CORAL)]:
        card(p,name,measure,x,215,368,title=title,ink=ink)
    chart(p,'contribuciones','waterfallChart',28,349,944,340,'¿Quién explica el cambio neto? · aporte en bbl/día',{'Category':col('Activos','Activo'),'Y':ms('Cambio comparable bpd'),'Tooltips':ms('Cambio comparable pct','N comparable 2026','N comparable 2025')},sort=('Produccion','Cambio comparable bpd',True,'Descending'),objects={'sentimentColors':[{'properties':{'increaseFill':C(TEAL),'decreaseFill':C(CORAL),'totalFill':C(CYAN)}}]})
    chart(p,'balance','donutChart',996,349,576,340,'Balance de activos · número, no volumen',{'Category':col('Comparacion','Resultado'),'Y':ms('Activos comparables')})
    chart(p,'trayectorias','lineChart',28,711,944,232,'¿El cambio se sostiene entre meses? · bbl/día',{'Category':col('SerieComparable','Mes_nombre'),'Y':ms('Diario comparable 2025','Diario comparable 2026')},colors=[VIOLET,TEAL],sort=('SerieComparable','Mes_nombre',False,'Ascending'))
    text(p,'decision','DECISIÓN 01 · VALIDAR EL EFECTO DE JULIO 2025\nCon los 14 activos: 7 de 8 meses caen; sin julio: -2,26 %.\nPlanificación: revisar esa base excepcional en 30 días.\nIndicador: cambio con/sin julio; n = 8 / 7 por año.\nNo atribuir el aumento a eficiencia sin causas y costos.',996,711,576,147,12,fg=INK,bg='#FFE4EB')
    card(p,'prioridad','Caida prioritaria',996,876,576,67,'Mayor descenso dentro de la selección',CORAL,19)

    p='Priorizar'
    page(p,PAGES[1][1],'Priorizar por impacto absoluto y variación relativa  •  Comparación fija enero–agosto 2026 / 2025, solo activos comunes.',2)
    slicer(p,'activos','Activos','Etiqueta',28,120,570)
    text(p,'reglas','Coral: descensos  •  Turquesa: aumentos\nBurbuja = tamaño de producción. Ejes = nivel y cambio porcentual.',622,121,950,75,14,fg='#91EAD7',bg='#1B2946')
    chart(p,'mapa_prioridades','scatterChart',28,216,830,452,'Mapa de prioridades · X: bbl/día 2026; Y: cambio %',{'Category':col('Activos','Activo'),'X':ms('Comparable 2026'),'Y':ms('Cambio comparable pct'),'Size':ms('Comparable 2026'),'Tooltips':ms('Cambio comparable bpd','N comparable 2026')},objects={'categoryLabels':props(show=True,fontSize=10),'dataPoint':[{'properties':{'defaultColor':C(CYAN)}}]})
    chart(p,'impacto','barChart',882,216,690,452,'¿Dónde actuar primero? · cambio en bbl/día',{'Category':col('Activos','Activo'),'Y':ms('Aumentos bpd','Descensos bpd'),'Tooltips':ms('Cambio comparable pct','Cambio comparable bpd')},colors=[TEAL,CORAL],sort=('Produccion','Cambio comparable bpd',True,'Descending'))
    chart(p,'porcentaje','clusteredColumnChart',28,690,830,252,'Cambio relativo · contrastar siempre con el volumen',{'Category':col('Activos','Activo'),'Y':ms('Cambio comparable pct'),'Tooltips':ms('Cambio comparable bpd','Comparable 2026')},colors=[VIOLET],sort=('Produccion','Cambio comparable pct',True,'Descending'),objects={'labels':props(show=True,fontSize=9,labelDisplayUnits=1,labelPrecision=1)})
    text(p,'accion','DECISIÓN 02 · ASIGNAR LA REVISIÓN POR IMPACTO\nJefatura de activos: revisar primero pérdidas ≥ 500 bbl/día;\nvigilar las menores y sostener aumentos ≥ 3.000 bbl/día.\nSon umbrales propuestos de gestión, no normas técnicas.\nIndicador: brecha bbl/día y n por activo. Plazo: 30 días.\nNo inferir eficiencia sin costos, pozos y días de operación.\nCada activo tiene n = 8 por año: grupo pequeño.',882,690,690,252,13,fg=INK,bg='#FFF0CE')

    p='Proteger'
    page(p,PAGES[2][1],'¿Dónde concentrar continuidad operativa?  •  Enero–agosto 2026; incluye los 15 activos observados, no solo la cohorte comparable.',3)
    slicer(p,'activos','Activos','Etiqueta',28,120,570)
    text(p,'alcance','SA + AU + SH es un grupo fijo: 51,75 % con todos los activos.\nLas participaciones cambian al filtrar. Cada activo: n = 8 meses.',622,121,950,75,14,fg='#FFD47A',bg='#1B2946')
    for name,measure,x,title,ink in [('volumen','Crudo 2026',28,'Crudo observado 2026 · bbl',CYAN),('diario','Diario 2026',420,'Aporte diario 2026 · bbl/día',TEAL),('concentracion','Participacion tres activos',812,'Peso SA + AU + SH · selección',VIOLET),('n','N 2026',1204,'n válido · activo-mes',CYAN)]:
        card(p,name,measure,x,215,368,title=title,ink=ink)
    chart(p,'arbol','treemap',28,349,708,342,'Mapa de volumen · área proporcional a barriles',{'Group':col('Activos','Activo'),'Values':ms('Crudo 2026'),'Tooltips':ms('Participacion 2026','N 2026')})
    chart(p,'peso','clusteredBarChart',760,349,812,342,'Participación por activo · % de la selección',{'Category':col('Activos','Activo'),'Y':ms('Participacion 2026'),'Tooltips':ms('Crudo 2026')},colors=[CYAN],sort=('Produccion','Crudo 2026',True,'Descending'),objects={'labels':props(show=True,fontSize=9,labelDisplayUnits=1,labelPrecision=1)})
    chart(p,'concentracion_dona','donutChart',28,713,448,230,'SA + AU + SH frente al resto',{'Category':col('Activos','Grupo_volumen'),'Y':ms('Crudo 2026')})
    chart(p,'concentracion_mensual','columnChart',500,713,604,230,'Dependencia mensual · barriles',{'Category':col('Calendario','Mes_nombre'),'Series':col('Activos','Grupo_volumen'),'Y':ms('Crudo 2026')},sort=('Calendario','Mes_nombre',False,'Ascending'),objects={'labels':props(show=False)})
    text(p,'accion','DECISIÓN 03 · PROTEGER CONTINUIDAD\nMantenimiento: revisar contingencias\nde SA, AU y SH cada mes.\nIndicador: participación y aporte diario.\nLímite: concentración no equivale\na riesgo de falla ni rentabilidad.',1128,713,444,230,13,fg=INK,bg='#DBF5EE')

    p='Tendencia'
    page(p,PAGES[3][1],'¿El precio ayuda a explicar cambios de producción?  •  Cohorte fija de 11 activos completos; precio de referencia mensual.',4)
    slicer(p,'anio','Calendario','Anio',28,120,300,'Filtrar años')
    slicer(p,'meses','Calendario','Anio_mes',352,120,430,'Filtrar meses')
    text(p,'alcance','No hay filtro de activos: la cohorte se mantiene fija.\nLos filtros temporales ajustan los pares y su correlación.',806,121,766,75,13,fg='#91EAD7',bg='#1B2946')
    for name,measure,x,title,ink in [('r','Correlacion cambios',28,'r de Pearson · cambios pareados',VIOLET),('pares','N pares mensuales',420,'n de pares mensuales',CYAN),('precio_kpi','Precio promedio (USD/bbl)',812,'Precio medio · USD/bbl',AMBER),('sinprecio','Meses productivos sin precio',1204,'Meses productivos sin precio',CORAL)]:
        card(p,name,measure,x,215,368,title=title,ink=ink)
    axis={'categoryAxis':[{'properties':{'axisType':L('Scalar'),'show':L(True),'fontSize':L(10),'labelColor':C(INK)}}]}
    chart(p,'cohorte','lineChart',28,349,842,254,'Producción diaria · cohorte fija de 11 activos',{'Category':col('Calendario','Mes'),'Y':ms('Diario cohorte')},colors=[TEAL],sort=('Calendario','Mes',False,'Ascending'),objects=axis)
    chart(p,'precio','lineChart',28,625,842,252,'Precio mensual de referencia · USD/bbl',{'Category':col('Calendario','Mes'),'Y':ms('Precio promedio (USD/bbl)')},colors=[VIOLET],sort=('Calendario','Mes',False,'Ascending'),objects=axis)
    chart(p,'asociacion','scatterChart',894,349,678,376,'X: cambio del precio % · Y: cambio de producción %',{'Category':col('Cambios','Mes'),'X':ms('Cambio precio mensual'),'Y':ms('Cambio crudo mensual'),'Tooltips':ms('N pares mensuales')},colors=[CYAN])
    text(p,'accion','DECISIÓN 04 · EVITAR METAS BASADAS SOLO EN PRECIO\nPlanificación: incorporar paradas, capacidad y costos.\nHistorial completo: r = 0,017; n = 54 pares mensuales.\nLa asociación lineal observada es débil; no prueba causalidad.\nNo convertir precio × producción en ingresos.',894,747,678,130,12,fg=INK,bg='#EEE6FF')
    card(p,'aviso','Aviso pares',28,897,1544,47,'',AMBER,16)

    p='Calidad'
    page(p,PAGES[4][1],'¿Qué resultados pueden usarse con confianza?  •  Antes de actuar, revisar cobertura, conflictos y tamaño de los grupos.',5)
    slicer(p,'anio','Calendario','Anio',28,120,292,'Filtrar años')
    slicer(p,'activos','Activos','Etiqueta',344,120,612)
    text(p,'leyenda','Cobertura válida: verde ≥ 99 %; ámbar ≥ 90 %; coral < 90 %.\nVacío: fuera de cobertura. Ausencia de registro ≠ cero.',980,121,592,75,11,fg='#FFD47A',bg='#1B2946')
    for name,measure,x,title,ink in [('conflictos','Conflictos totales',28,'Celdas con conflicto',CORAL),('huecos','Huecos internos',420,'Meses internos sin registro',AMBER),('catalogo','Activos sin catalogo',812,'Activos con nombre pendiente',VIOLET),('n','N crudo',1204,'n crudo válido · activo-mes',CYAN)]:
        card(p,name,measure,x,215,368,title=title,ink=ink)
    heat={'columnHeaders':[{'properties':{'fontSize':L(11),'autoSizeColumnWidth':L(True),'columnAdjustment':L('growToFit'),'backColor':C('#DCE7F5')}}],
          'rowHeaders':props(fontSize=11),
          'values':[{'properties':{'fontSize':L(11)}},{'properties':{'backColor':{'solid':{'color':{'expr':F('Produccion','Color cobertura',True)}}}},'selector':{'data':[{'dataViewWildcard':{'matchingOption':1}}],'metadata':'Produccion.Cobertura crudo pct'}}]}
    visual(p,'mapa_cobertura','pivotTable',28,349,772,461,'Mapa de cobertura válida · activo × año',{'Rows':col('Activos','Activo'),'Columns':col('Calendario','Anio'),'Values':ms('Cobertura crudo pct')},heat)
    chart(p,'huecos_activo','clusteredBarChart',824,349,748,220,'Faltantes internos · activos que requieren revisión',{'Category':col('Activos','Activo'),'Y':ms('Huecos visibles'),'Tooltips':ms('N crudo')},colors=[AMBER],sort=('Produccion','Huecos visibles',True,'Descending'))
    chart(p,'conflictos_activo','clusteredBarChart',824,591,748,219,'Conflictos por activo · celdas, no barriles',{'Category':col('Activos','Activo'),'Y':ms('Conflictos crudo visibles','Conflictos gas visibles')},colors=[CORAL,VIOLET])
    text(p,'accion','DECISIÓN 05 · VALIDAR ANTES DE CERTIFICAR\nGestión de datos: resolver conflictos, verificar faltantes y completar AB16. Indicador: pendientes confirmados; objetivo propuesto: 0 antes de certificar.\nNo imputar ceros ni eliminar atípicos automáticamente. El mapa excluye del denominador los meses fuera de cobertura observada.',28,824,1544,84,11,fg=INK,bg='#FFF0CE')
    card(p,'grupos','Advertencia de grupos',28,918,1544,37,'',CORAL,12)


def create_docs(tables):
    measures=b.MEASURES+EXTRA
    (OUT/'Medidas_DAX.txt').write_text('\n\n'.join('// '+d+'\n'+n+' =\n'+e for n,e,f,g,d in measures)+'\n',encoding='utf-8-sig',newline='\n')
    counts={n:len(t) for n,t in tables.items()}
    visuals=[json.loads(p.read_text(encoding='utf-8')) for p in (OUT/REPORT).rglob('visual.json')]
    from collections import Counter
    save(OUT/'manifest.json',{'grupo':'GRUPO 5','tablas':counts,'relaciones':9,'medidas':len(measures),'paginas':5,'visuales_por_tipo':dict(Counter(v['visual']['visualType'] for v in visuals)), 'sha256_csv':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((OUT/'datos').glob('*.csv'))}})
    guide='''POWER BI · DECISIONES SOBRE PRODUCCIÓN · GRUPO 5

ABRIR
1. Extrae TODO el ZIP en una carpeta nueva. Mantén juntas las carpetas .Report y .SemanticModel.
2. Abre Petroleo_Decisiones.pbip en Power BI Desktop.
3. Pulsa Inicio > Actualizar. El proyecto incorpora los datos en consultas M; no necesita rutas locales ni credenciales para cargarlos.
4. Recorre las cinco pestañas y selecciona activos/años en sus filtros. Borra una selección con el borrador del filtro o vuelve a hacer clic en el gráfico.
5. Después de actualizar, puedes guardar un .pbix con Archivo > Guardar como. No cambies la extensión del .pbip.

GUION PARA DECIDIR
01 DECIDIR: producción comparable, variación, sensibilidad sin julio, cascada de aportes, balance de aumentos/descensos y evolución mensual. Validar la base excepcional de julio 2025 antes de declarar mejora sostenida.
02 PRIORIZAR ACTIVOS: mapa de burbujas (volumen/cambio), barras de impacto absoluto y cambio relativo. Asignar revisión por impacto, no solo por porcentaje.
03 PROTEGER VOLUMEN: mapa de árbol, ranking de participación, anillo y columnas mensuales de concentración. Planear continuidad de SA/AU/SH.
04 TENDENCIA Y PRECIO: dos series separadas, dispersión de cambios y r de Pearson con n. No fijar metas operativas basadas exclusivamente en precio.
05 CALIDAD PARA DECIDIR: mapa de calor activo/año, faltantes y conflictos. Validar antes de certificar; conserva n y alertas de grupos pequeños.

FILTROS Y PERÍODOS
Páginas 1 y 2: comparación fija enero-agosto 2026 contra enero-agosto 2025. Catorce activos con 8 meses válidos por año y 243 días en cada período. Solo el filtro de activos modifica esta comparación. AIT y AB16 no tienen pares completos comunes: al seleccionarlos se muestra vacío, no cero. No se unieron sus códigos.
Página 3: enero-agosto 2026, quince activos observados. SA/AU/SH es un grupo fijo, no un top 3 recalculado por filtro. Su porcentaje es sobre la selección vigente.
Página 4: cohorte histórica fija de 11 activos completos (AM, AP, AU, CU, EY, IN, ITT, LI, OY, PA, SA). Los filtros de tiempo ajustan las series y los pares. Precio se cuenta una vez por mes. No se filtra por activo. Los cambios se calculan contra el mes calendario anterior con datos disponibles, antes de filtrar; seleccionar un mes conserva su variación contra el mes anterior, aunque este no esté seleccionado.
Página 5: historial completo inicialmente; filtros por año y activo. Cobertura válida = meses con crudo válido / meses entre primer y último registro de cada activo. Los meses fuera de cobertura no se penalizan; los huecos internos y conflictos sí.
Los filtros son independientes por página. Los rótulos "historial completo" o "con todos los activos" muestran referencias fijas; los indicadores y gráficos se recalculan según sus filtros.

REGLAS PARA INTERPRETAR
Menos de 12 meses por activo activa precaución descriptiva; no es una prueba estadística. La comparación interanual tiene n=8 por activo y año, 112 observaciones por año con todos los activos. Una mejora observada significa mayor producción diaria, no eficiencia demostrada. Faltan costos, días operativos, pozos y causas de paradas.
Umbrales propuestos para revisión: pérdida de 500 bbl/día o más y aumento de 3.000 bbl/día o más. Se documentan como criterios de gestión, no normas ni estimaciones de riesgo. Responsable: Operaciones/Jefatura de activos; plazo de revisión: 30 días. No implican inversiones ni cambios físicos automáticos.
La correlación se calcula sobre cambios pareados, no niveles ni 789 registros repetidos. Con n<12 se oculta r. La asociación no es causal y los meses no son independientes. El precio de exportación de referencia no es precio específico de cada activo y precio por producción no equivale a ingreso.
No hay coordenadas o ubicaciones verificadas en las fuentes. Por eso se incluyen mapas de prioridades, volumen y cobertura, no posiciones geográficas supuestas.

CONTROLES ESPERADOS SIN FILTROS
Comparación: 352.214,84 bbl/día en 2026; 327.535,93 en 2025; +24.678,91 bbl/día (+7,53 %); 11 aumentos, 3 descensos. IN: -837,67 bbl/día (-6,25 %). AV: -3,80; AM: -0,96 bbl/día.
Sensibilidad: siete de ocho meses agregados muestran descenso interanual. Julio 2026 contra julio 2025: +238,63 %. Excluyendo julio de AMBOS años, el cambio es -2,2592 %; n=7 meses/activo/año, 212 días/año. No se elimina julio de la fuente ni de la comparación principal: se explicita el efecto de la base. Antes de afirmar mejora sostenida, Planificación debe contrastar esa base en 30 días con información operativa; los datos no prueban la causa de la caída de 2025.
2026 observado: 88.304.451,13 bbl; 363.392,80 bbl/día; 120 registros; SA/AU/SH 51,75 %.
Cambios: 54 pares; r=0,016568. Historial de producción: 789 registros, 788 crudo válido; 18 huecos, 3 celdas conflictivas; AB16 sin nombre; agosto 2026 sin precio.

REPRODUCIR Y EDITAR
Desde la raíz del repositorio: python -m src.export_powerbi_decisiones
Los CSV y consultas M son respaldos legibles. El modelo contiene los CSV codificados en Base64. Editar datos/*.csv no altera por sí solo el modelo: regenera el proyecto o cambia su consulta M.
Medidas_DAX.txt documenta todas las medidas. manifest.json registra conteos y huellas de los datos. validacion_powerbi.json describe las comprobaciones realizadas y las limitaciones de verificación en Desktop.
Se mantiene por separado el proyecto básico anterior en powerbi/.

DECLARACIÓN DE USO DE IA
Se utilizó inteligencia artificial (Codex/OpenAI) como apoyo para programar, analizar datos, proponer la presentación visual y redactar documentación. No se inventaron registros de producción ni ubicaciones geográficas. GRUPO 5 debe revisar la interpretación y asume la responsabilidad académica de la entrega.
'''
    (OUT/'LEEME_PRIMERO.txt').write_text(guide,encoding='utf-8-sig',newline='\n')


def main():
    OUT.mkdir(exist_ok=True)
    tables=get_tables()
    create_model(tables)
    create_report()
    create_docs(tables)
    print(json.dumps({'carpeta':str(OUT),'tablas':{n:len(t) for n,t in tables.items()},'medidas':len(b.MEASURES+EXTRA)},ensure_ascii=False))


if __name__=='__main__':main()
