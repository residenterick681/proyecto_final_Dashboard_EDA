"""Textos comunes al informe, al notebook y al dashboard."""
QUESTION='¿Cómo cambia la producción de los activos entre meses comparables, dónde se concentra el volumen y qué asociación descriptiva existe entre los cambios del precio y del crudo en una cohorte estable?'
STEPS=[
 ('1','Pregunta de análisis','Problema profesional, usuario, pregunta y alcance.'),
 ('2','Origen y estructura','Fuentes, unidad activo-mes, tipos y diccionario.'),
 ('3','Análisis univariado','Distribución, media, mediana, dispersión y asimetría.'),
 ('4','Análisis bivariado','Producción por activo y relación temporal con el precio.'),
 ('5','Calidad de los datos','Faltantes, duplicados, contradicciones y atípicos.'),
 ('6','Segmentación','Activo y año, tamaños válidos y comparación de períodos equivalentes.'),
 ('7','Hallazgos y decisiones','Evidencia, acción, responsable, indicador y límite.')]
TECHNICAL=[
 ('T1','Carga y trazabilidad','load_sources','read_excel/read_csv cargan las copias conservadas. SHA-256 impide analizar una versión distinta de la documentada. Path hace portables las rutas.'),
 ('T2','Estructura y tipos','clean_sources','to_numeric y to_datetime fallan ante valores inválidos; año/mes son enteros y activo es etiqueta nominal. info, shape y describe se muestran en el notebook.'),
 ('T3','Duplicados y contradicciones','clean_sources','La clave es año-mes-activo. Se consolidan copias exactas y equivalentes con tolerancia absoluta 1e-6. Cuando un volumen discrepa se asigna NA solo a esa medida. No se escoge la primera fila.'),
 ('T4','Faltantes, ceros y atípicos','clean_sources','No se imputa precio ni volumen. Se conservan ceros de gas e IQR fuera de cercas por activo. Un faltante no es cero y un atípico no demuestra error.'),
 ('T5','Uniones y variables','clean_sources','merge many_to_one valida el catálogo y los precios. La unión izquierda retiene producción sin precio. Tasa diaria = volumen/días reales; log1p facilita describir asimetría.'),
 ('T6','Resumen y asociación','analyze','Se distinguen suma, media y mediana. El precio se cuenta una vez por mes. Las correlaciones utilizan una cohorte constante; los cambios mensuales reducen la confusión por niveles y duración de los meses.'),
 ('T7','Segmentación y n','analyze','groupby activo-año calcula n_registros y n válidos por medida. n<12 advierte cobertura inferior a una vuelta anual. La comparación 2026/2025 usa enero-agosto y 14 activos presentes en ambos períodos.'),
 ('T8','Reproducibilidad y validación','block_bootstrap_correlation','Semilla 2026 y 2.000 réplicas por bloques reproducen el diagnóstico. requirements, tests, notebook ejecutado y un comando reconstruyen los resultados. No se generan observaciones petroleras ficticias.')]
DICTIONARY=[
 ('producción','AÑO / anio','int64','año calendario','2022-2026; parte de la clave'),
 ('producción','MES / mes','int64','mes calendario','1-12; parte de la clave'),
 ('producción','ACTIVO / activo','string','código nominal','16 códigos observados; parte de la clave'),
 ('producción','CRUDO / crudo','float64','barriles mensuales*','Volumen observado; 1 contradicción queda NA'),
 ('producción','GAS / gas','float64','MPC mensuales*','Miles de pies cúbicos; 2 contradicciones quedan NA; cero válido'),
 ('precio','Período / fecha','datetime64','primer día del mes','67 meses desde 2021-01 hasta 2026-07; clave única'),
 ('precio','Precio... / precio_usd_barril','float64','USD por barril','Indicador mensual agregado, no cotización por activo'),
 ('catálogo','Activo / nombre_activo','string','nombre nominal','15 nombres; AB16 no está en el catálogo'),
 ('catálogo','Nomenclatura / activo','string','código nominal','Clave única usada para unión muchos-a-uno'),
 ('derivada','fecha','datetime64','primer día del mes','Construida desde anio y mes en producción'),
 ('derivada','filas_origen','string','filas de Excel','Números originales separados por |; encabezado en fila 1'),
 ('derivada','n_filas_origen','int64','conteo','Cantidad de filas originales consolidadas por clave'),
 ('derivada','conflicto_crudo / conflicto_gas','bool','verdadero/falso','True cuando los valores no son equivalentes; no se elige uno'),
 ('derivada','catalogo_faltante','bool','verdadero/falso','True si el código no coincide con el catálogo'),
 ('derivada','dias_mes','int64','días calendario','28, 29, 30 o 31; febrero bisiesto incluido'),
 ('derivada','crudo_diario','float64','barriles por día*','crudo/dias_mes; no mide tasa de días operativos'),
 ('derivada','gas_diario','float64','MPC por día*','gas/dias_mes; no se suma a crudo'),
 ('derivada','log1p_crudo','float64','logaritmo transformado','ln(1+crudo); auxiliar, no volumen físico'),
 ('derivada','trimestre','int64','trimestre calendario','1,2,3,4; derivado de fecha'),
 ('derivada','atipico_crudo_diario / atipico_gas_diario','bool','verdadero/falso','Fuera de Q1-1,5 IQR o Q3+1,5 IQR dentro de cada activo; se conserva')]


def decisions(summary,audit):
    s=summary; c=s['correlacion']; fall=s['mayor_caida']
    return [
      {'titulo':'1. Priorizar la revisión de continuidad de SA, AU y SH',
       'evidencia':f"Sacha, Auca y Shushufindi concentran {s['top3_pct']:.2f}% del crudo de enero-agosto de 2026; 8 meses por activo. Es concentración del volumen observado.",
       'accion':'Revisar semanalmente disponibilidad, paradas y mantenimiento de esos tres activos antes de reasignar recursos.',
       'responsable':'Coordinación de operaciones y mantenimiento.',
       'indicador':'Participación de los tres activos y tasa diaria por activo; activar revisión si cae más de 5% frente al mismo período previo.',
       'limite':'El 5% es un umbral propuesto de gestión, no estimado ni normativo. No hay datos de costo, seguridad, disponibilidad ni reservas; no autoriza por sí solo inversiones.'},
      {'titulo':'2. Investigar la caída de Indillana en períodos comparables',
       'evidencia':f"IN registra {fall['diario_actual']:,.0f} barriles/día en enero-agosto de 2026 y {fall['diario_anterior']:,.0f} en 2025: {fall['cambio_pct']:.2f}%, diferencia de {fall['cambio_diario']:,.0f} barriles/día (n=8 meses en cada año). La cohorte de 14 activos aumenta {s['cambio_comparable_pct']:.2f}%.",
       'accion':'Solicitar bitácoras de paradas y conciliación mensual de medición de IN; completar una revisión en 30 días.',
       'responsable':'Ingeniería de producción del activo y responsable de datos.',
       'indicador':'Variación interanual de tasa diaria y porcentaje de meses conciliados; objetivo de revisión: 100% de los 8 meses.',
       'limite':'La reducción es descriptiva. No se atribuye a agotamiento o fallas sin evidencia operativa. Ocho meses no cubren una vuelta anual completa.'},
      {'titulo':'3. Corregir las brechas antes de certificar totales',
       'evidencia':f"Se encontraron {audit['claves_repetidas']} claves repetidas, {audit['celdas_conflictivas']} celdas contradictorias, {audit['huecos_interiores']} huecos interiores, AB16 sin catálogo y agosto de 2026 sin precio.",
       'accion':'Conciliar AM, AU y LA de agosto de 2022 con la fuente, revisar las ausencias y completar la nomenclatura; mantener identificadas las sumas parciales.',
       'responsable':'Administrador de datos y supervisor de medición.',
       'indicador':'Claves duplicadas después de limpiar = 0; celdas conflictivas pendientes = 0 como meta; cobertura de catálogo = 100% como meta.',
       'limite':'No sustituir faltantes por cero ni interpolar para cumplir la meta. Un hueco puede reflejar cobertura administrativa y requiere confirmación.'},
      {'titulo':'4. Separar la vigilancia del precio de las metas de producción',
       'evidencia':f"En 11 activos con cobertura constante, r entre cambios mensuales de tasa de crudo y precio es {c['r']:.3f}; n={c['n']} meses pareados, IC exploratorio por bloques de 3 meses [{c['ic95'][0]:.3f}, {c['ic95'][1]:.3f}].",
       'accion':'Mantener el precio como indicador de contexto y actualizar la comparación mensual cuando exista el nuevo dato; usar variables operativas para investigar cambios productivos.',
       'responsable':'Analista de planificación y analista comercial.',
       'indicador':'Número de meses pareados, cobertura de la cohorte y correlación de cambios; no emitir conclusión cuantitativa con menos de 12 pares.',
       'limite':'El intervalo incluye cero y valores positivos/negativos. No prueba independencia; no es un modelo de pronóstico ni una estimación causal. Precio × producción no representa ingresos efectivos.'}]
