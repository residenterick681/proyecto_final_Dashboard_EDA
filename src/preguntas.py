"""Cinco preguntas, respuestas y gráficos reproducibles para el informe grupal."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from .pipeline import ROOT


def number(value, digits=2):
    return f'{value:,.{digits}f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def build(root=ROOT):
    s=json.loads((root/'reportes/resumen.json').read_text(encoding='utf-8'))
    a=json.loads((root/'reportes/auditoria.json').read_text(encoding='utf-8'))
    d=pd.read_csv(root/'data/procesados/produccion_limpia.csv',parse_dates=['fecha'])
    co=pd.read_csv(root/'reportes/comparacion_interanual.csv')
    ch=pd.read_csv(root/'reportes/cambios_mensuales.csv')
    cov=pd.read_csv(root/'reportes/cobertura.csv',parse_dates=['fecha'])
    out=root/'reportes/figuras';out.mkdir(exist_ok=True)
    green='#237E68';amber='#B66C21';ink='#213E35';gray='#9BAFB4'
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':ink,'text.color':ink,'figure.facecolor':'white','savefig.facecolor':'white'})
    fmt=FuncFormatter(lambda x,pos:number(x,0))
    def finish(name):
        plt.tight_layout();plt.savefig(out/name,dpi=190,bbox_inches='tight');plt.close()

    before=s['diario_comparable_anterior'];after=s['diario_comparable_actual']
    fig,ax=plt.subplots(figsize=(9.3,4.2))
    bars=ax.bar(['Enero-agosto 2025','Enero-agosto 2026'],[before,after],color=[gray,green],width=.52)
    ax.bar_label(bars,labels=[number(before,2),number(after,2)],padding=8,fontsize=12,fontweight='bold')
    ax.set(ylim=(0,after*1.22),ylabel='Barriles por día calendario',title='Mismos 14 activos, 8 meses y 243 días por año')
    ax.yaxis.set_major_formatter(fmt);ax.grid(axis='y',alpha=.16);ax.set_axisbelow(True)
    ax.text(.5,.94,'Variación conjunta: +'+number(s['cambio_comparable_pct'])+'%',transform=ax.transAxes,ha='center',va='top',color=green,fontsize=13)
    finish('06_pregunta_comparacion.png')

    cc=co.sort_values('cambio_diario')
    fig,ax=plt.subplots(figsize=(9.3,4.9))
    ax.barh(cc.activo,cc.cambio_diario,color=[amber if x<0 else green for x in cc.cambio_diario])
    for i,r in enumerate(cc.itertuples()):
        label=f'{r.cambio_diario:+,.0f}'.replace(',','.')+' | '+f'{r.cambio_pct:+.1f}'.replace('.',',')+'%'
        ax.text(r.cambio_diario+(70 if r.cambio_diario>=0 else -70),i,label,ha='left' if r.cambio_diario>=0 else 'right',va='center',fontsize=9)
    ax.set(xlim=(-2750,6900),xlabel='Cambio de barriles por día: 2026 menos 2025',title='Magnitud absoluta y porcentaje del cambio por activo')
    ax.axvline(0,color=gray,lw=.8);ax.xaxis.set_major_formatter(fmt);ax.grid(axis='x',alpha=.12);ax.set_axisbelow(True)
    finish('07_pregunta_activos.png')

    current=d[d.anio.eq(s['anio_actual']) & d.mes.le(s['mes_corte'])]
    totals=current.groupby('activo').crudo.sum(min_count=1).sort_values()
    shares=totals/totals.sum()*100
    fig,ax=plt.subplots(figsize=(9.3,4.9))
    bars=ax.barh(shares.index,shares.values,color=[green if x in s['top3'] else gray for x in shares.index])
    ax.bar_label(bars,labels=[number(x,2)+'%' for x in shares.values],padding=5,fontsize=9)
    ax.set(xlim=(0,shares.max()+5.5),xlabel='Participación en el crudo observado (%)',title='Enero-agosto 2026: 15 activos, n = 8 meses por activo')
    ax.grid(axis='x',alpha=.12);ax.set_axisbelow(True)
    finish('08_pregunta_concentracion.png')

    c=s['correlacion']
    fig,ax=plt.subplots(figsize=(9.3,4.5))
    ax.scatter(ch.cambio_precio_pct,ch.cambio_crudo_pct,c=green,s=37,alpha=.75,edgecolor='white',linewidth=.6)
    ax.axhline(0,color=gray,lw=.8,zorder=0);ax.axvline(0,color=gray,lw=.8,zorder=0)
    ax.set(xlabel='Variación mensual del precio (%)',ylabel='Variación mensual del crudo diario (%)',title=f'11 activos constantes | n = {c["n"]} pares mensuales | Pearson r = {number(c["r"],3)}')
    ax.grid(alpha=.10)
    finish('09_pregunta_precio.png')

    dates=pd.DatetimeIndex(sorted(cov.fecha.unique()));assets=sorted(cov.activo.unique())
    status={'fuera de cobertura observada':0,'observado':1,'sin registro interior':2}
    cov['valor']=cov.estado.map(status)
    matrix=cov.pivot(index='activo',columns='fecha',values='valor').reindex(index=assets,columns=dates)
    for row in d.loc[d.conflicto_crudo | d.conflicto_gas].itertuples():matrix.loc[row.activo,row.fecha]=3
    colors=['#E6ECEB',green,'#E5AA45','#BB5349']
    fig,ax=plt.subplots(figsize=(9.3,4.9))
    ax.imshow(matrix.to_numpy(),aspect='auto',cmap=ListedColormap(colors),norm=BoundaryNorm([-.5,.5,1.5,2.5,3.5],4),interpolation='nearest')
    ax.set_yticks(range(len(assets)),[x+'*' if x=='AB16' else x for x in assets])
    ticks=list(range(0,len(dates),6))
    if len(dates)-1-ticks[-1] < 3: ticks.pop()
    ticks.append(len(dates)-1)
    ax.set_xticks(ticks,[dates[i].strftime('%Y-%m') for i in ticks],rotation=35,ha='right',fontsize=8)
    ax.set(title='Cobertura y conflictos: 16 activos x 56 meses',xlabel='Mes | * AB16 no tiene nombre validado en el catálogo')
    ax.set_yticks(np.arange(-.5,len(assets),1),minor=True);ax.grid(which='minor',axis='y',color='white',lw=.6);ax.tick_params(which='minor',left=False)
    ax.legend(handles=[Patch(facecolor=clr,label=label) for clr,label in zip(colors,['Fuera de cobertura','Registro observado','Hueco interior','Conflicto en crudo o gas'])],loc='upper center',bbox_to_anchor=(.5,-.29),ncol=2,frameon=False,fontsize=9)
    finish('10_pregunta_calidad.png')

    up=co[co.cambio_diario.gt(0)];down=co[co.cambio_diario.lt(0)]
    questions=[
      {'numero':1,'titulo':'¿Mejoró la producción diaria conjunta entre enero-agosto de 2025 y 2026 al comparar los mismos activos?',
       'justificacion':'Basada en los datos: existen 14 activos con crudo válido en los ocho meses de ambos períodos. Cada año aporta 112 registros activo-mes y 243 días calendario. Esta coincidencia permite comparar sin mezclar un año parcial con uno completo ni incorporar códigos presentes solo en un período.',
       'figura':'06_pregunta_comparacion.png',
       'respuesta':f'Sí, en volumen por día calendario de esta cohorte: pasa de {number(before)} a {number(after)} bbl/día, un aumento de {number(after-before)} bbl/día (+{number(s["cambio_comparable_pct"])}%). Se calcula sumando barriles y dividiendo por los días distintos del período; no se promedian sin ponderación las tasas mensuales.',
       'implicacion':'El crecimiento conjunto es un avance observable del nivel productivo. Conviene estudiar los activos que aportan ese aumento para formular hipótesis de mejora.',
       'limite':'n = 8 meses por activo y año: menos de un ciclo anual. El aumento no demuestra mayor eficiencia, rentabilidad ni efecto de una intervención. AIT y AB16 se excluyen por cobertura no comparable.',
       'fuente':'reportes/comparacion_interanual.csv; reportes/resumen.json. Cohorte: AM, AP, AU, AV, CU, EY, IN, ITT, LA, LI, OY, PA, SA y SH.'},
      {'numero':2,'titulo':'¿Qué activos conviene revisar por sus caídas y cuáles aportan los mayores aumentos de producción?',
       'justificacion':'Basada en los datos: la comparación homogénea ofrece cambios absolutos y porcentuales para 14 activos, con n = 8 meses en cada año. Combinar ambas medidas evita que una caída porcentual grande en un activo pequeño desplace una pérdida de volumen mucho mayor.',
       'figura':'07_pregunta_activos.png',
       'respuesta':f'{len(up)} activos aumentan y {len(down)} disminuyen. IN presenta la mayor caída absoluta: -837,67 bbl/día (-6,25%). AV cae más en porcentaje (-14,38%), pero su diferencia es solo -3,80 bbl/día. SH aporta +4.839,24 bbl/día (+9,67%) y SA +3.775,47 (+5,57%); AP crece +98,13% desde una base menor.',
       'implicacion':'Priorizar la conciliación y revisión operativa de IN por la magnitud de la pérdida; investigar en SH y SA qué condiciones acompañaron los aumentos antes de intentar replicarlas.',
       'limite':'La prioridad se basa únicamente en volumen observado. Sin costos, riesgos, pozos, paradas ni días operativos no se pueden atribuir causas ni recomendar una inversión específica.',
       'fuente':'reportes/comparacion_interanual.csv. Barras: diferencia absoluta; etiquetas: diferencia absoluta y variación porcentual.'},
      {'numero':3,'titulo':'¿En qué activos se concentra la producción y dónde tendría mayor alcance una revisión de continuidad operativa?',
       'justificacion':'Basada en los datos: enero-agosto de 2026 contiene 120 registros válidos de crudo, distribuidos entre 15 activos con ocho meses cada uno. Esta cobertura común permite medir la contribución de cada activo al volumen total del período.',
       'figura':'08_pregunta_concentracion.png',
       'respuesta':f'SA, AU y SH reúnen el {number(s["top3_pct"])}% de los {number(s["crudo_actual"])} barriles observados. El resto de los 12 activos aporta {number(100-s["top3_pct"])}%. La participación mide concentración del volumen; no determina cuál activo es más eficiente.',
       'implicacion':'Dar seguimiento prioritario a la continuidad de esos tres activos, junto con los criterios de seguridad y mantenimiento, porque representan más de la mitad del volumen observado.',
       'limite':'n = 8 meses por activo; es una concentración de un período parcial. No es una estimación de reservas, de rentabilidad ni de producción nacional. Esta selección de 15 activos difiere de la cohorte interanual de 14.',
       'fuente':'data/procesados/produccion_limpia.csv, filtro anio = 2026 y mes <= 8. Participación = volumen del activo / volumen total observado.'},
      {'numero':4,'titulo':'¿Las variaciones del precio del crudo acompañan las variaciones mensuales de producción de una cohorte estable?',
       'justificacion':'Basada en los datos: once activos tienen crudo válido durante los 56 meses productivos. Tras unir un solo precio por mes hay 55 meses con precio y 54 cambios mensuales pareados. El precio no se repite por activo para inflar el tamaño del análisis.',
       'figura':'09_pregunta_precio.png',
       'respuesta':f'No se observa una asociación lineal contemporánea fuerte: Pearson r = {number(c["r"],3)} y Spearman = {number(c["spearman"],3)}. El intervalo exploratorio del 95% por bloques de tres meses es [{number(c["ic95"][0],3)}; {number(c["ic95"][1],3)}], que incluye cero. La nube de puntos no ofrece evidencia de una relación lineal marcada.',
       'implicacion':'Mantener el precio como contexto y buscar variables operativas para explicar las variaciones de producción; estos resultados no respaldan usar solo el precio para fijar metas productivas.',
       'limite':'n = 54 pares temporales, no independientes. Se analizan cambios en el mismo mes; no se estudian efectos rezagados ni causalidad. No se concluye que el precio nunca influya.',
       'fuente':'reportes/cambios_mensuales.csv y resumen.json. Remuestreo exploratorio: 2.000 réplicas, bloques de 3 meses y semilla 2026.'},
      {'numero':5,'titulo':'¿Qué problemas de calidad deben resolverse antes de interpretar una variación como mejora o deterioro real?',
       'justificacion':'Basada en los datos: la auditoría encuentra 13 claves repetidas y tres celdas conflictivas. La cobertura muestra 18 huecos internos; AB16 tiene 36 registros sin nombre validado y agosto de 2026 carece de precio para sus 15 registros productivos.',
       'figura':'10_pregunta_calidad.png',
       'respuesta':'La consolidación elimina 13 filas redundantes y deja 789 claves únicas. Persisten tres celdas por conciliar en agosto de 2022: crudo de LA y gas de AM y AU. Hay 17 huecos internos en AV y uno en SH (junio de 2024). Los bloques grises solo indican períodos fuera de la cobertura observada; no prueban cierre de operaciones.',
       'implicacion':'Conciliar los tres conflictos con la fuente, confirmar el origen de los huecos, completar el catálogo de AB16 y solicitar el precio faltante. Estas acciones mejorarían la trazabilidad y la calidad de la comparación, sin inventar producción.',
       'limite':'No reemplazar ausencias por cero ni borrar atípicos para mostrar mejoras. Se conservan 52 marcas IQR de crudo y 42 de gas. Cada celda del mapa representa un activo-mes; los colores no equivalen a magnitud de producción.',
       'fuente':'reportes/auditoria.json, cobertura.csv y data/procesados/produccion_limpia.csv. Mapa: 896 combinaciones posibles = 789 observadas + 18 huecos + 89 fuera de cobertura.'}
    ]
    (root/'reportes/preguntas_mejoras.json').write_text(json.dumps(questions,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return questions

if __name__=='__main__':print(json.dumps({'preguntas':len(build())}))
