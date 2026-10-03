"""Documento PDF de entrega, regenerado desde los resultados verificados."""
from pathlib import Path
from xml.sax.saxutils import escape
import json
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,Image,Preformatted,KeepTogether
from .pipeline import ROOT
from .content import QUESTION,STEPS,TECHNICAL,DICTIONARY,decisions

GREEN=colors.HexColor('#145e4a'); INK=colors.HexColor('#213e35'); PALE=colors.HexColor('#edf3ee')

def build(root=ROOT):
    s=json.loads((root/'reportes/resumen.json').read_text(encoding='utf-8'))
    a=json.loads((root/'reportes/auditoria.json').read_text(encoding='utf-8'))
    links_path=root/'docs/enlaces.json'
    links=json.loads(links_path.read_text(encoding='utf-8')) if links_path.exists() else {'repositorio':'https://github.com/residenterick681/proyecto_final_Dashboard_EDA','dashboard':'Pendiente de publicar'}
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyEDA',fontName='Helvetica',fontSize=9.4,leading=14,textColor=INK,spaceAfter=9))
    styles.add(ParagraphStyle(name='SmallEDA',fontName='Helvetica',fontSize=7.8,leading=11,textColor=INK,spaceAfter=5))
    styles.add(ParagraphStyle(name='TitleEDA',fontName='Helvetica-Bold',fontSize=31,leading=37,textColor=GREEN,spaceAfter=18))
    styles.add(ParagraphStyle(name='HeadEDA',fontName='Helvetica-Bold',fontSize=19,leading=24,textColor=GREEN,spaceAfter=14))
    styles.add(ParagraphStyle(name='SubEDA',fontName='Helvetica-Bold',fontSize=12,leading=16,textColor=GREEN,spaceBefore=10,spaceAfter=8))
    styles.add(ParagraphStyle(name='CodeEDA',fontName='Courier',fontSize=7.2,leading=10,textColor=INK,backColor=PALE,borderPadding=10,spaceAfter=12))
    story=[]
    def p(text,small=False): story.append(Paragraph(text,styles['SmallEDA' if small else 'BodyEDA']))
    def h(text):story.append(Paragraph(text,styles['HeadEDA']))
    def sub(text):story.append(Paragraph(text,styles['SubEDA']))
    def page(title):
        if story:story.append(PageBreak())
        h(title)
    def code(text):story.append(Preformatted(text,styles['CodeEDA']))
    def table(headers,rows,widths=None):
        cells=[[Paragraph(escape(str(v)),styles['SmallEDA']) for v in row] for row in [headers]+rows]
        t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),1,GREEN),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#d4dfd6')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
        story.append(t);story.append(Spacer(1,10))
    def figure(name,width=490):
        im=Image(str(root/'reportes/figuras'/name));im.drawHeight=im.imageHeight*width/im.imageWidth;im.drawWidth=width;story.append(im);story.append(Spacer(1,8))
    def num(x,n=2):return f'{x:,.{n}f}'
    p('MIACD02P01 | PROGRAMACIÓN Y ANÁLISIS DE DATOS',True);story.append(Spacer(1,35))
    story.append(Paragraph('Producción petrolera<br/>con evidencia y contexto',styles['TitleEDA']))
    p('<b>Proyecto final: análisis exploratorio y dashboard</b><br/>Erick Leandro Ruano Lara<br/>Corte analítico: producción enero 2022-agosto 2026; precio enero 2021-julio 2026.<br/>Documento preparado el 2 de octubre de 2026 (hora de Ecuador).')
    story.append(Spacer(1,20));table(['88,30 millones','51,75%','789 registros'],[['Barriles observados en enero-agosto de 2026.','Crudo concentrado en SA, AU y SH durante ese período.','Claves activo-mes después de consolidar 13 filas redundantes.']],[164,164,164])
    sub('Pregunta');p(QUESTION)
    sub('Resultado principal');p(f'En los 14 activos con ocho meses completos en ambos años, la tasa diaria conjunta aumenta <b>{s["cambio_comparable_pct"]:.2f}%</b> entre enero-agosto de 2025 y 2026. Indillana registra una variación de <b>{s["mayor_caida"]["cambio_pct"]:.2f}%</b>. Las diferencias son descriptivas; los archivos no identifican las causas.')
    sub('Entrega');p('Este documento integra contexto, fuentes, diccionario, siete pasos EDA, ocho apartados técnicos, dashboard, cuatro decisiones y reproducción. El notebook incluye código ejecutado y salidas. El repositorio conserva las tres fuentes originales con SHA-256.')
    p('<b>Repositorio:</b> <link href="'+links['repositorio']+'" color="#145e4a">'+links['repositorio']+'</link>',True)
    if links['dashboard'].startswith('http'):p('<b>Dashboard:</b> <link href="'+links['dashboard']+'" color="#145e4a">'+links['dashboard']+'</link>',True)
    else:p('Dashboard: '+links['dashboard'],True)
    p('Alcance: registros aportados por el usuario; no equivalen a toda la producción nacional. Las unidades de producción se interpretan con apoyo de la ficha pública, sin certificación de identidad de archivos.',True)

    page('1. Contexto, usuario y origen de los datos')
    p('La planificación petrolera requiere distinguir la evolución de los volúmenes de los cambios en la cobertura de activos, la duración de cada mes y los problemas de registro. Un total anual parcial puede inducir decisiones equivocadas si se compara directamente con un año completo.')
    p('<b>Usuario identificado:</b> analista de planificación y supervisión de producción de una operación petrolera. Utilizaría el dashboard para priorizar revisiones de medición y continuidad operativa; no para aprobar inversiones o diagnosticar fallas únicamente con estas tablas.')
    table(['Fuente entregada','Contenido y cobertura','Tratamiento'],[
        ['eppec_prd_petroleo_acumulada_2026 (2).xlsx','802 filas; 5 columnas con datos; 16 códigos; enero 2022-agosto 2026. Hoja1.','Una clave por año-mes-activo; se conserva la fila de origen.'],
        ['precio-petrleo-crudo-ecu (1).csv','67 precios mensuales, enero 2021-julio 2026; USD por barril.','Clave de mes única. Unión izquierda a producción.'],
        ['activos_nomenclatura.csv','15 códigos y nombres.','Unión muchos-a-uno. AB16 queda sin nombre validado.']],[165,175,152])
    sub('Procedencia y supuestos explícitos')
    p('El nombre del XLSX y la ficha de Datos Abiertos Ecuador son compatibles con producción mensual de EP Petroecuador. La ficha describe BPPM y MPC. Se adoptan barriles por mes y miles de pies cúbicos por mes. Los valores suben y bajan dentro del año, por lo que no se calcula una diferencia de un supuesto acumulado anual. La hoja por sí sola no declara unidades ni metodología; esta limitación permanece visible.')
    p('La definición del BCE identifica el precio como promedio ponderado mensual de exportaciones de crudos Oriente y Napo de EP Petroecuador. El CSV entregado explicita USD por barril. Se usa como contexto agregado; no es el precio efectivo de cada activo. No se interpreta precio × producción como facturación.')
    p('Se preservan los tres archivos entregados, sin descargar sustitutos ni atribuir autenticidad byte a byte a una publicación oficial. El catálogo no incluye AB16; no se presume su equivalencia con AIT. Los huecos pueden reflejar cambios de cobertura o de operación y requieren verificación.')
    p('<b>Datos observados, no simulados:</b> C2 se cubre mediante origen documentado, script determinista, problemas encontrados y remuestreo analítico con semilla 2026. La semilla no se usa para inventar registros petroleros.')

    page('2. Diccionario completo de las fuentes')
    p('Unidad de observación: un activo en un mes calendario. La clave original es AÑO + MES + ACTIVO; en la tabla analítica es anio + mes + activo. Los códigos no tienen orden numérico ni significado cuantitativo.')
    table(['Origen / campo','Tipo y unidad','Definición y regla'],[[f'{r[0]}: {r[1]}',f'{r[2]} / {r[3]}',r[4]] for r in DICTIONARY[:9]],[182,120,190])
    p('* Las unidades de CRUDO y GAS son interpretaciones respaldadas por la ficha del conjunto mensual (BPPM y MPC), no metadatos internos del XLSX. Se explicita esta diferencia para no dar una certeza que el archivo no contiene.',True)
    sub('Conservación y versiones');p('data/crudos/manifest.json registra nombre original, nombre portable, tamaño y SHA-256. El lector comprueba cada huella antes de ejecutar; una modificación de la fuente detiene el proceso. Actualizar fuentes requiere actualizar el manifiesto y revisar las interpretaciones.')

    page('3. Diccionario de la tabla analítica y métricas')
    table(['Campo derivado','Tipo / unidad','Definición y tratamiento'],[[r[1],f'{r[2]} / {r[3]}',r[4]] for r in DICTIONARY[9:]],[178,120,194])
    p('<b>Métricas de grupos:</b> n_registros = filas del grupo; n_crudo, n_gas y n_precio = observaciones válidas de cada medida. crudo_total/gas_total = suma observada (NA si no existe ningún valor); media_crudo_diario y mediana_crudo_diario = promedio y mediana de las tasas mensuales. grupo_pequeno = n_crudo &lt; 12.',True)
    p('<b>Métricas de períodos:</b> tasa conjunta = suma de volumen / suma de días de meses distintos; participación = volumen del activo / volumen total observado; cambio (%) = 100 × (tasa actual/tasa anterior - 1). El precio medio es la media simple de los meses válidos, sin multiplicarlos por activos. No es un promedio ponderado del período.',True)

    page('4. Método EDA: pasos 1 y 2')
    p('Se sigue el orden explícito de S3_P1_Ruano.ipynb. La preparación y consolidación se ejecutan antes de los gráficos para no duplicar observaciones; sus decisiones se explican en el paso 5, como en el taller.')
    table(['Paso del curso','Aplicación al proyecto'],[[n+'. '+title,desc] for n,title,desc in STEPS],[210,282])
    sub('Paso 1: pregunta y unidad');p(QUESTION)
    code("raw, prices_raw, catalog = load_sources(ROOT)\nprint(raw.shape, prices_raw.shape, catalog.shape)\nraw.info()\nraw.describe(include='all')")
    sub('Paso 2: resultado e interpretación');p('La lectura devuelve (802, 5), (67, 2) y (15, 2). Hay 56 meses de producción y 16 activos observados en distintas ventanas. Excel tiene formato hasta la columna Q, pero solo A:E contienen datos; el lector ignora el resto. Los precios de 2021 no tienen producción correspondiente y no se fuerzan al panel. Agosto de 2026 permanece sin precio.')
    p('El alcance no es una encuesta nacional, ni hay ponderadores. No se extrapolan resultados fuera de los activos y meses incluidos. Las fuentes carecen de fechas de revisión por registro; por ello los duplicados contradictorios no pueden resolverse dando preferencia a una versión.')

    page('5. Paso 3: análisis univariado')
    code("df[['crudo','gas','crudo_diario']].agg(\n    ['count','mean','median','std','skew','min','max']\n)")
    figure('01_distribucion.png')
    table(['Indicador del crudo por activo-mes','Resultado'],[['n válido',s['n_crudo']],['Media (barriles)',num(s['crudo_media'])],['Mediana (barriles)',num(s['crudo_mediana'])],['Desviación estándar (barriles)',num(s['crudo_std'])],['Asimetría',num(s['crudo_asimetria'],3)]],[285,207])
    p('La media supera la mediana y la asimetría es positiva: hay una cola de volúmenes altos. El histograma combina activos de tamaños muy distintos y no implica una distribución homogénea de pozos. La mediana describe mejor el centro de los registros, mientras la suma responde al volumen total observado. Ninguna de estas medidas demuestra crecimiento por sí sola.')

    page('6. Paso 4: evolución y asociación')
    figure('02_serie_cobertura.png',470)
    p('Las sumas mensuales se acompañan del número de activos con crudo válido. La cobertura variable puede alterar el total aunque no cambie un activo individual. En el dashboard, los faltantes y combinaciones sin registro activan una advertencia; un mes sin registros no se dibuja como cero.')
    code("monthly = monthly_series(df)\ncounts = df.groupby('activo').crudo.count()\ncohort = counts[counts == df.fecha.nunique()].index\nbalanced = monthly_series(df[df.activo.isin(cohort)])")
    p('Para la asociación temporal se seleccionan AM, AP, AU, CU, EY, IN, ITT, LI, OY, PA y SA: 11 activos con crudo válido en los 56 meses. Esta cohorte excluye LA y SH por sus faltantes, y AB16, AIT y AV por cobertura incompleta. La selección limita a qué activos se refiere la asociación.')
    p('Precio y producción se alinean una vez por mes. Quedan 55 meses con precio y 54 cambios desde febrero de 2022 hasta julio de 2026. Se usa volumen/días calendario para no confundir febrero con un mes de 31 días.')

    page('7. Paso 4: interpretación de la asociación')
    figure('04_cambios.png')
    c=s['correlacion']
    code("paired['cambio_crudo_pct'] = (\n    paired.crudo_diario.pct_change(fill_method=None) * 100\n)\npaired['cambio_precio_pct'] = (\n    paired.precio_usd_barril.pct_change(fill_method=None) * 100\n)\nblock_bootstrap_correlation(x, y, seed=2026, reps=2000, block=3)")
    table(['Diagnóstico','Resultado'],[['Pearson en niveles',num(c['r_niveles'],3)],['Pearson entre cambios',num(c['r'],3)],['Spearman entre cambios',num(c['spearman'],3)],['IC exploratorio 95%, bloques de 3',f'[{c["ic95"][0]:.3f}, {c["ic95"][1]:.3f}]'],['Sensibilidad, bloques de 6',f'[{c["sensibilidad_bloque_6"]["ic95"][0]:.3f}, {c["sensibilidad_bloque_6"]["ic95"][1]:.3f}]']],[285,207])
    p('No se observa asociación lineal contemporánea fuerte en los cambios de esta cohorte. El intervalo incluye cero y asociaciones pequeñas de ambos signos; no demuestra independencia ni ausencia de efectos con rezagos. Los bloques circulares conservan dependencia local de pares, pero suponen suficiente estabilidad del proceso. Este intervalo no es garantía de cobertura del 95% ante cambios estructurales. No se usa un p-valor ingenuo ni se presenta un modelo predictivo.')

    page('8. Paso 5: limpieza y calidad trazable')
    table(['Hallazgo real','Resultado / decisión'],[
      ['Copias exactas','9 filas extra; se consolidan por clave.'],['Claves repetidas','13 claves de agosto 2022; 13 filas redundantes en total.'],
      ['Crudo de LA, agosto 2022','366668,06 vs. 366668,05: queda NA; no se promedia una contradicción.'],
      ['Gas de AM, agosto 2022','713407,82 vs. 103,69: queda NA.'],['Gas de AU, agosto 2022','310275,38 vs. 310050,89: queda NA.'],
      ['Diferencia binaria equivalente','Tolerancia absoluta 1e-6, rtol=0; no altera discrepancias mayores.'],
      ['18 huecos interiores','17 meses de AV y junio 2024 de SH; no equivalen a cero.'],
      ['AB16 ausente del catálogo','36 registros conservados con código y etiqueta sin catálogo.'],
      ['Precio de agosto 2026','15 registros productivos sin precio; unión izquierda y sin imputación.'],
      ['Ceros y atípicos',f'18 ceros de gas conservados; {a["atipicos_crudo_diario"]} marcas IQR de crudo diario y {a["atipicos_gas_diario"]} de gas diario.']],[175,317])
    code("equivalent = np.allclose(values, values[0], atol=1e-6, rtol=0)\nrecord[col] = float(np.mean(values)) if equivalent else np.nan\nq1, q3 = g[var].quantile([.25, .75])\nflag = (g[var] < q1 - 1.5*(q3-q1)) | (g[var] > q3 + 1.5*(q3-q1))")
    p('Resultado: 789 claves únicas, 788 crudos válidos y 787 gases válidos. Se conservan filas originales, conflictos, límites IQR y cobertura en reportes separados. Las sumas con datos faltantes son parciales. Los atípicos se calculan dentro de cada activo; no se eliminan volúmenes grandes por pertenecer a activos grandes.')
    p('Sensibilidad de limpieza: escoger la primera o última fila de LA alteraría el crudo en 0,01 barriles, pero asumir una preferencia seguiría sin evidencia. Para AM la discrepancia de gas es material. Se elige una política uniforme de NA por medida y se mantiene la observación disponible en la otra medida. Los ceros de gas de AV son ceros reportados, no imputaciones.')

    page('9. Paso 6: segmentación con n')
    groups=pd.read_csv(root/'reportes/segmentacion.csv')
    pivot=groups.pivot(index='activo',columns='anio',values='n_crudo')
    table(['Activo']+[str(x) for x in pivot.columns],[[idx]+['-' if pd.isna(v) else str(int(v)) for v in row] for idx,row in pivot.iterrows()],[102]+[78]*len(pivot.columns))
    p('Cada celda muestra n de crudo válido por activo-año, no población de pozos. Un guion significa que no hay registros del grupo. En 2026 todos los grupos tienen ocho meses; la advertencia n&lt;12 permanece activa. En 2022 LA tiene 11 crudos válidos por la contradicción; en 2024 SH tiene 11 por la ausencia de junio.')
    code("groups = df.groupby(['activo','nombre_activo','anio']).agg(\n    n_registros=('fecha','size'), n_crudo=('crudo','count'),\n    n_gas=('gas','count'), n_precio=('precio_usd_barril','count'),\n    mediana_crudo_diario=('crudo_diario','median')\n)")
    p('El archivo reportes/segmentacion.csv contiene la tabla completa con medias, medianas, totales y n de cada medida. El umbral de 12 es una regla de cobertura de un ciclo anual; no un criterio universal de suficiencia estadística ni de privacidad. Las tres fuentes no contienen información personal.')

    page('10. Paso 6: comparación interanual homogénea')
    figure('05_comparacion.png',480)
    comp=pd.read_csv(root/'reportes/comparacion_interanual.csv')
    table(['Indicador comparable','Enero-agosto 2025','Enero-agosto 2026'],[['Activos completos',14,14],['Meses por activo',8,8],['Días calendario',243,243],['Tasa diaria conjunta (barriles/día)',num(s['diario_comparable_anterior']),num(s['diario_comparable_actual'])]],[240,126,126])
    p(f'La variación de la cohorte es <b>+{s["cambio_comparable_pct"]:.2f}%</b>. El cálculo pondera por días calendario (suma de barriles dividida por días distintos), en lugar de dar igual peso a meses de distinta duración. AIT y AB16 no aparecen en ambos períodos completos y se excluyen; no se equiparan sus códigos.')
    p(f'Indillana (IN) registra el mayor descenso absoluto de tasa dentro de esta cohorte: <b>{s["mayor_caida"]["cambio_diario"]:,.2f} barriles/día</b>, equivalente a {s["mayor_caida"]["cambio_pct"]:.2f}%. AV tiene pequeña escala absoluta: su variación porcentual no debe dominar la priorización operativa. Las tasas describen días calendario y no corrigen por días efectivos de operación.')

    for i,chunk in enumerate([decisions(s,a)[:2],decisions(s,a)[2:]]):
        page(f'{11+i}. Paso 7: decisiones sustentadas ({i+1}/2)')
        for d in chunk:
            sub(d['titulo']);p('<b>Evidencia:</b> '+d['evidencia']);p('<b>Acción:</b> '+d['accion']);p('<b>Responsable:</b> '+d['responsable']);p('<b>Indicador:</b> '+d['indicador']);p('<b>Límite:</b> '+d['limite']);story.append(Spacer(1,12))
        if i==0:p('Estas son propuestas para un escenario profesional académico; no se afirma que la organización ya las haya aprobado o ejecutado. Los umbrales y plazos son decisiones de diseño explícitas.')

    snippets=[
     "raw = pd.read_excel(path / 'produccion_original.xlsx')\nprices = pd.read_csv(path / 'precios_original.csv')\nassert hashlib.sha256(file.read_bytes()).hexdigest() == expected",
     "d[col] = pd.to_numeric(d[col], errors='raise')\nd[['anio','mes']] = d[['anio','mes']].astype('int64')\nd['activo'] = d.activo.astype('string').str.strip().str.upper()",
     "exact = d.duplicated(KEY + ['crudo','gas'])\nfor key, g in d.loc[~exact].groupby(KEY):\n    equivalent = np.allclose(values, values[0], atol=1e-6, rtol=0)\n    record[col] = np.mean(values) if equivalent else np.nan",
     "q1, q3 = g[var].quantile([.25, .75])\nlo, hi = q1 - 1.5*(q3-q1), q3 + 1.5*(q3-q1)\nflag = (g[var] < lo) | (g[var] > hi)\n# Se guarda la marca; no se filtra la observacion.",
     "clean = clean.merge(catalog, on='activo', how='left',\n                    validate='many_to_one')\nclean = clean.merge(prices, on='fecha', how='left',\n                    validate='many_to_one')\nclean['crudo_diario'] = clean.crudo / clean.fecha.dt.days_in_month",
     "paired['cambio_crudo_pct'] = paired.crudo_diario.pct_change() * 100\npaired['cambio_precio_pct'] = paired.precio_usd_barril.pct_change() * 100\n# Un par por mes de la cohorte, nunca un par por activo.",
     "n = df.groupby(['activo','anio']).crudo.count()\nalerta = n < 12\n# Comparar enero-agosto con enero-agosto, mismo grupo de activos.\nvariacion = 100 * (tasa_actual/tasa_anterior - 1)",
     "rng = np.random.default_rng(2026)\nstarts = rng.integers(0, n, size=int(np.ceil(n/block)))\nidx = ((starts[:, None] + np.arange(block)) % n).ravel()[:n]\nr_replica = np.corrcoef(x[idx], y[idx])[0, 1]"
    ]
    for block in range(4):
        page(f'{13+block}. Explicación técnica T{2*block+1}-T{2*block+2}')
        if block==0:p('<b>Correspondencia propuesta:</b> los materiales y la rúbrica recibidos no incluyen los enunciados oficiales de T1-T8. Se organizan ocho apartados verificables que cubren carga, tipos, calidad, limpieza, integración, análisis, segmentación y reproducción. Esta numeración debe cotejarse si se entrega una guía adicional.')
        for k in range(2*block,2*block+2):
            tag,title,func,explanation=TECHNICAL[k];sub(tag+' | '+title);p(explanation);code(snippets[k]);p('Implementación completa: src/pipeline.py, función '+func+'. El notebook muestra el código de la función y sus resultados ejecutados.',True)
        if block==1:p('La conservación de valores extremos permite auditar sin cambiar la población analizada por conveniencia. La ausencia de precio afecta comparaciones con precio, no la disponibilidad del volumen productivo. Los CSV de conflictos y cobertura permiten revisar cada caso.')
        if block==2:p('Los gráficos seleccionados responden a su variable: líneas para meses, barras ordenadas para contribuciones, histogramas y cajas para distribución y dispersión para asociación. No se usan pasteles ni ejes dobles para sugerir coincidencias visuales.')
        if block==3:p('El remuestreo es una simulación del procedimiento estadístico, no de los datos de producción. Con el mismo entorno y semilla se repiten los intervalos. Bloques de 3 y 6 meses permiten examinar sensibilidad; cambiar la longitud puede cambiar la incertidumbre y no corrige todo cambio estructural.')

    page('17. Dashboard y validación funcional')
    p('El dashboard estático se construye desde la misma tabla depurada usada en Python. Incluye gráficos Plotly locales, de modo que no depende de una CDN para abrirlo. Puede servirse con python app.py o abrirse desde dashboard/index.html. La versión publicada ofrece el mismo análisis a través del enlace de entrega.')
    table(['Elemento','Comportamiento comprobado'],[['Indicadores','Volumen observado, tasa por día calendario, precio mensual medio y concentración de los tres mayores.'],['Filtros','Mes inicial, mes final, activo, crudo/gas y cobertura completa en el período.'],['Gráficos','Serie, barras de contribución, cajas de tasas, dispersión mensual y mapa de cobertura.'],['Tamaños','Tabla con n válido por activo y medida; alerta cuando n<12 meses.'],['Vacíos y conflictos','Selección vacía y rango inverso muestran mensajes; contradicciones no se sustituyen por cero.'],['Exportación','CSV de la selección con fecha, medidas, banderas y filas de origen.'],['Decisiones','Referencia fija enero-agosto 2026/2025, declarada como independiente de los filtros.'],['Diseño','Vista de escritorio y 390 px sin desbordamiento; ejes numéricos conservan escala lineal tras filtrar.']],[125,367])
    qa=root/'reportes/qa_dashboard.json'
    if qa.exists():
        test=json.loads(qa.read_text(encoding='utf-8'));p(f'<b>Validación funcional:</b> {len(test["checks"])} comprobaciones aprobadas en Microsoft Edge sin ventana visible, usando la página local. No hubo errores JavaScript. Evidencia: reportes/qa_dashboard.json y docs/dashboard.png. La prueba local no sustituye la confirmación de publicación del servicio.')
    p('Guion de revisión: (1) abrir la selección inicial de 2026; (2) seleccionar IN; (3) cambiar a gas; (4) consultar AB16 en 2026 para ver el estado vacío; (5) ampliar a toda la historia y activar cobertura completa; (6) examinar calidad y descargar una selección. La advertencia de grupos pequeños acompaña la lectura, no bloquea la exploración.')
    p('La funcionalidad opcional WebMCP configura los mismos filtros de la interfaz cuando el navegador dispone de ella. Su compatibilidad nativa no se certifica en esta entrega; no es necesaria para utilizar el dashboard ni forma parte de la rúbrica.')

    page('18. Reproducibilidad y evidencia de la rúbrica')
    p('Entorno de referencia: Python 3.12.14. Instalar las versiones exactas de requirements.txt dentro de un entorno virtual. No se requieren credenciales para regenerar los análisis. El repositorio contiene fuentes pequeñas sin información personal; no se incluyen secretos del proyecto previo de clase.')
    code("python -m venv .venv\n# Windows:\n.venv\\Scripts\\python -m pip install -r requirements.txt\n.venv\\Scripts\\python -m src.reproducir\n.venv\\Scripts\\python -m unittest discover -s tests -v\n.venv\\Scripts\\python app.py")
    table(['Ruta','Contenido'],[['data/crudos/','3 archivos intactos y manifiesto SHA-256'],['data/procesados/','Panel depurado y precios'],['src/','Carga, análisis, gráficos, notebook, PDF y dashboard'],['notebooks/','EDA ejecutado con código, resultados e interpretaciones'],['reportes/','Auditoría, cobertura, grupos, comparación, figuras y pruebas'],['dashboard/','Página interactiva compilada y biblioteca local'],['docs/','PDF único de entrega, enlaces y captura'],['tests/','Pruebas de integridad, política de limpieza y reproducibilidad']],[150,342])
    table(['Criterio','Máximo','Evidencia en esta entrega'],[['C1','10','Secciones 1-4; diccionario completo y usuario.'],['C2','10','Fuentes conservadas, SHA-256, semilla y calidad encontrada.'],['C3','20','Secciones 4-12 y notebook: siete pasos de S3_P1.'],['C4','15','Dashboard, n, alertas, filtros y 17 controles funcionales.'],['C5','20','Secciones 13-16; ocho apartados propuestos, código y justificación.'],['C6','15','Cuatro decisiones con evidencia, responsable, indicador y límite.'],['C7','5','README, requirements, estructura, scripts y pruebas.']],[70,60,362])
    p('<b>La rúbrica recibida suma 95 puntos máximos, no 100.</b> Esta matriz facilita comprobar la cobertura; no asigna una calificación. La correspondencia literal de T1-T8 queda sujeta a sus enunciados oficiales, que no estaban incluidos en los materiales entregados.',True)

    page('19. Referencias, trazabilidad y límites finales')
    sub('Material de clase analizado')
    table(['Material de Sabado_26','Uso en el proyecto'],[['S3_P1_Ruano.ipynb','Orden de los siete pasos, mediana, IQR y segmentación con n.'],['S3_P2_Ruano.ipynb','Interpretación prudente de incertidumbre y correlación; no se fuerzan contrastes independientes.'],['S3_P3_ruano.ipynb','Prevención de fuga y necesidad de pregunta predictiva; no se añade un modelo innecesario.'],['S3_P4_Ruano.ipynb y mi_proyecto_ruano','Módulos, rutas portables, versiones, Git y minimización de datos.'],['S3_EDA_Critico_Reel_Turismo y S3_reel_Ruano','Suma frente a media, gráficos apropiados y límites de procedencia.'],['EDA_Produccion_Petrolera_Ecuador_Ruano','Antecedente temático y cohorte estable; no se reutilizó su CSV incrustado.']],[237,255])
    sub('Referencias externas consultadas')
    p('Datos Abiertos Ecuador. <link href="https://www.datosabiertos.gob.ec/dataset/produccion-mensual-petroecuador" color="#145e4a">Producción Mensual Petroecuador</link>. La ficha indexada indica volúmenes BPPM y MPC por activo. La apertura directa devolvió 403; no se descargó su diccionario ni se certificaron los archivos originales.')
    p('Banco Central del Ecuador. <link href="https://contenido.bce.fin.ec/" color="#145e4a">Portal de información económica: Precio Petróleo Crudo Ecuatoriano</link>. Definición del promedio mensual ponderado de exportaciones Oriente/Napo. Consulta: 2 de octubre de 2026, hora de Ecuador.')
    sub('Identidad de los tres archivos')
    manifest=json.loads((root/'data/crudos/manifest.json').read_text(encoding='utf-8'))
    for item in manifest:
        p(escape(item['archivo'])+' | '+str(item['bytes'])+' bytes',True)
        code(item['sha256'])
    p('Límites: no hay datos de pozos, costos, días operativos, calidad del crudo ni causas de cambios. El precio agregado no representa ingresos de cada activo. Las coberturas administrativas no están documentadas. Las observaciones mensuales son dependientes. Las asociaciones y decisiones no se extrapolan a la producción nacional.')

    target=root/'docs/Proyecto_Final_EDA_Ruano.pdf'
    def footer(canvas,doc):
        canvas.saveState();w,hh=A4
        canvas.setStrokeColor(colors.HexColor('#d7e3d9'));canvas.line(42,40,w-42,40)
        canvas.setFont('Helvetica',7);canvas.setFillColor(INK)
        canvas.drawString(42,27,'EDA PETROLERO | RUANO | MIACD02P01')
        canvas.drawRightString(w-42,27,f'{doc.page}');canvas.restoreState()
    doc=SimpleDocTemplate(str(target),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=55,title='Proyecto final: Dashboard EDA de producción petrolera',author='Erick Leandro Ruano Lara')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return target

if __name__=='__main__':print(build())
