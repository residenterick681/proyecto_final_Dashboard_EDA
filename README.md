# proyecto_final_Dashboard_EDA

Proyecto final de Programación y Análisis de Datos (MIACD02P01). **GRUPO 5.**

Analiza tres archivos aportados por el usuario: producción mensual por activo, precio mensual del crudo ecuatoriano y catálogo de activos. Conserva los originales, audita la calidad y genera un notebook ejecutado, un informe PDF y un dashboard interactivo.

## Entrega

- **Dashboard público:** https://residenterick681.github.io/proyecto_final_Dashboard_EDA/
- **Informe único:** [Proyecto_Final_EDA_Grupo_5.pdf](docs/Proyecto_Final_EDA_Grupo_5.pdf), aproximadamente 0,7 MB, por debajo de 20 MB.
- **Notebook autónomo, paso a paso, con datos y salidas incorporados:** [01_EDA_petroleo.ipynb](notebooks/01_EDA_petroleo.ipynb).
- **Repositorio:** https://github.com/residenterick681/proyecto_final_Dashboard_EDA
- **Texto listo para el aula:** [texto_entrega.txt](docs/texto_entrega.txt).

## Notebook autónomo: un solo archivo para estudiar y ejecutar

[01_EDA_petroleo.ipynb](notebooks/01_EDA_petroleo.ipynb) contiene **todo el proceso ejecutable** en orden: lectura del XLSX y los dos CSV, inspección, tipos, duplicados, conflictos, uniones, variables, atípicos, cobertura, estadísticas, correlaciones, remuestreo, segmentación, comparaciones y decisiones. Cada bloque tiene explicación técnica y resultados. Incluye nueve gráficas construidas dentro del notebook, las cinco preguntas complementarias y la sensibilidad a julio de 2025.

Las tres fuentes originales están incorporadas como bytes codificados en Base64, en una celda identificada y plegable. Se verifica su SHA-256 al recuperarlas. **No importa módulos de `src`, no lee tablas procesadas ni carga imágenes previas.** Puedes copiar únicamente el `.ipynb` a otra carpeta y ejecutarlo con las bibliotecas indicadas en su introducción; no requiere descargar datos.

En Jupyter o VS Code selecciona Python y usa **Reiniciar kernel y ejecutar todo**. Ya contiene resultados guardados para leerlo sin ejecutar. Al ejecutarlo crea `salidas_EDA_notebook/` con copias de fuentes, tablas y figuras; esta carpeta es una salida, no un requisito de entrada. Los apartados T1–T8 están junto al código correspondiente y tienen un índice al final. La declaración de IA permanece al final del documento.

Se comprobó su ejecución desde una carpeta vacía: **32 celdas de código, nueve figuras y 23 controles internos correctos**. Una prueba adicional ejecuta el notebook aislado y compara su tabla depurada y comparación interanual con el análisis auditado del proyecto. `src/notebook.py` conserva únicamente la herramienta de mantenimiento para regenerar el `.ipynb`; no se necesita para estudiarlo o ejecutarlo.

## Versión para Power BI

La versión recomendada está en [powerbi_decisiones/](powerbi_decisiones/): **Petroleo_Decisiones.pbip**, nueve tablas relacionadas, 58 medidas DAX y cinco páginas orientadas a decidir: **Decidir, Priorizar activos, Proteger volumen, Tendencia y precio, Calidad para decidir**. Incluye 16 gráficos/mapas analíticos, indicadores, filtros y cinco acciones propuestas con responsable, indicador y límite. Se usan gráficos nativos editables, fondo azul oscuro y colores de contraste; la única matriz es el mapa de calor de cobertura.

Extrae o descarga **toda la carpeta**, abre el `.pbip` con Power BI Desktop y pulsa **Inicio > Actualizar** si los datos no se cargan automáticamente. Después puedes guardar un `.pbix` desde Desktop. Las consultas M incorporan los datos depurados: no requieren rutas a archivos originales ni credenciales. Consulta las [instrucciones](powerbi_decisiones/LEEME_PRIMERO.txt) y las [medidas DAX](powerbi_decisiones/Medidas_DAX.txt).

**Comparación y sensibilidad:** las páginas 1–2 comparan enero-agosto 2026 / 2025 con los mismos 14 activos y 243 días por año. El aumento agregado de **7,53 %** depende de la baja base de julio 2025: siete de ocho meses caen y, al excluir julio de ambos años, la variación es **-2,26 %** (siete meses y 212 días por año). La sensibilidad no elimina observaciones de la fuente ni sustituye la comparación completa. Se requiere información operativa para explicar la causa; no demuestra eficiencia.

La página 3 cubre los 15 activos observados en 2026; la página 4 conserva la cohorte histórica de 11 activos, con filtros temporales. Los precios se cuentan una sola vez por mes. El mapa de prioridades es de burbujas y el mapa de cobertura es de calor: las fuentes no contienen coordenadas verificadas para un mapa geográfico.

La versión de decisiones se abrió y representó en **Power BI Desktop 2.158.1177.0**. Se ejecutaron consultas DAX con escenarios filtrados para confirmar indicadores, selección sin comparación, n<12, cobertura y precios. También se validan esquemas PBIP/PBIR, relaciones y datos incorporados. Las evidencias están en `powerbi_decisiones/validacion_powerbi.json` y `validacion_dax.json`. El proyecto portable no incluye caché binaria. La validación del contexto de filtros mediante DAX no equivale a recorrer manualmente cada combinación de clics.

Para regenerar: `python -m src.export_powerbi_decisiones`, después del análisis. También forma parte de `python -m src.reproducir`. Regenerar sobrescribe la definición: conserva aparte tus cambios manuales. Editar los CSV de respaldo no modifica por sí solo las consultas incorporadas.

La versión básica anterior permanece en [powerbi/](powerbi/) como respaldo. Ambas conservan la corrección de compatibilidad: contenido PBIR **2.0.0**, `definition.pbir` **4.0**, archivos `.platform` e índice de páginas.

El informe incorpora cinco preguntas adicionales con justificación basada en los datos, respuestas, gráficos y límites de interpretación. Sus resultados y figuras se regeneran desde `src/preguntas.py`.

## Problema, pregunta y usuario

Un analista de planificación y supervisión de producción necesita distinguir cambios productivos de diferencias de cobertura, duración de los meses y errores de registro.

**¿Qué mejoras y oportunidades de mejora pueden identificarse a partir de las variaciones de producción, al comparar períodos equivalentes y considerar la cobertura y calidad de los datos?**

La unidad es **activo-mes**, no pozo ni persona. Los resultados describen los archivos aportados, no toda la producción nacional. No se infiere causalidad ni se calcula facturación multiplicando volumen producido por un precio agregado de exportación.

## Reproducir de principio a fin

Entorno probado: **Python 3.12.14**. Las versiones directas probadas están fijadas en `requirements.txt`. Los datos están incluidos y se comprueban mediante SHA-256; no se necesita descargar datasets.

### Windows / PowerShell

```powershell
git clone https://github.com/residenterick681/proyecto_final_Dashboard_EDA.git
cd proyecto_final_Dashboard_EDA
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.reproducir
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe app.py
```

Si `py` no está disponible, usar `python -m venv .venv` con un Python 3.12 instalado.

### Linux / macOS

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m src.reproducir
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python app.py
```

Abrir `http://127.0.0.1:8501`. Detener con `Ctrl+C`. Se puede elegir otro puerto con `python app.py --port 8502` o abrir directamente `dashboard/index.html`; todos sus datos y gráficos se sirven localmente, sin CDN. En VS Code se puede abrir el notebook seleccionando el intérprete de `.venv`.

El comando completo regenera datos depurados, auditoría, tablas, figuras, dashboard, notebook **ejecutado** y PDF. `--sin-notebook` omite solamente su reejecución, como alternativa rápida, pero no es el comando de validación completa. La ejecución no modifica los archivos originales ni publica automáticamente en servicios externos. GitHub Pages se actualiza automáticamente cuando cambian los archivos de dashboard/ en main, mediante .github/workflows/publicar.yml.

## Estructura

```text
app.py                         Servidor local del dashboard
data/
  crudos/                      Las tres fuentes intactas y manifest.json (SHA-256)
  procesados/                  Producción consolidada y precios tipados
  diccionario.csv              Campos originales y derivados, tipos, unidades y reglas
src/
  pipeline.py                  Carga, limpieza, segmentación y análisis
  content.py                   Pregunta, diccionario y decisiones compartidas
  figures.py                   Figuras del notebook y PDF
  dashboard.html / dashboard.js  Interfaz y cálculos de filtros
  build_dashboard.py           Compilación de la página con datos integrados
  notebook.py                  Generación y ejecución del notebook
  report.py                    Generación del PDF
  reproducir.py                Orquestación completa
notebooks/01_EDA_petroleo.ipynb Código, resultados e interpretación
reportes/                      Auditoría, conflictos, cobertura, grupos, comparación y QA
dashboard/                     Versión estática compilada, lista para alojar
docs/                          PDF, enlaces, texto de entrega y captura
tests/                         Pruebas de datos y control de la interfaz
requirements.txt               Dependencias Python con versiones exactas
.github/workflows/validar.yml   Reproducción y pruebas al hacer push
```

## Fuentes, supuestos y calidad encontrada

| Fuente original | Cobertura | Regla |
|---|---|---|
| `eppec_prd_petroleo_acumulada_2026 (2).xlsx` | 802 filas, enero 2022-agosto 2026, 16 códigos | Un activo-mes; volúmenes mensuales |
| `precio-petrleo-crudo-ecu (1).csv` | 67 meses, enero 2021-julio 2026 | Un precio por mes en USD/barril |
| `activos_nomenclatura.csv` | 15 códigos | Catálogo muchos-a-uno; AB16 ausente |

La [ficha de Datos Abiertos Ecuador](https://www.datosabiertos.gob.ec/dataset/produccion-mensual-petroecuador) describe producción mensual en BPPM y MPC. Se interpretan como barriles por mes y miles de pies cúbicos por mes; el XLSX no explicita las unidades. La ficha indexada fue consultada; la apertura directa devolvió 403. No se certificó identidad byte a byte de la copia con el recurso oficial. La [definición del BCE](https://contenido.bce.fin.ec/) corresponde al precio promedio ponderado mensual de exportaciones Oriente/Napo de EP Petroecuador; la serie del CSV no fue cotejada celda a celda con la publicación. El catálogo fue aportado sin metadatos de origen adicionales.

- 9 copias exactas y 13 filas redundantes en total; **789 claves únicas**.
- Agosto 2022: crudo de LA y gas de AM/AU presentan discrepancias. Se asigna NA solo a la medida contradictoria. Quedan **788 crudos y 787 gases válidos**.
- Diferencias binarias de Excel menores a `1e-6` se consideran equivalentes; la diferencia de `0,01` de LA no se oculta mediante redondeo.
- 18 huecos interiores: 17 en AV y uno en SH. Ausencia no equivale a producción cero ni demuestra paralización.
- AB16 conserva el código y una etiqueta de catálogo faltante; no se equipara con AIT.
- Agosto 2026 conserva 15 filas productivas sin precio. No se imputa.
- Se conservan 18 ceros de gas y todos los atípicos. IQR por activo marca 52 tasas de crudo y 42 tasas de gas para revisión.

**Los datos de producción no son simulados.** La semilla 2026 se utiliza para 2.000 remuestreos de pares temporales, con bloques circulares de 3 meses y sensibilidad de 6 meses. Es una simulación del diagnóstico, no una generación de observaciones petroleras.

## Siete pasos EDA y explicación técnica

Se reproduce el orden de **S3_P1_Ruano.ipynb**:

1. Pregunta y usuario.
2. Origen, estructura, tipos y diccionario.
3. Análisis univariado.
4. Análisis bivariado.
5. Faltantes, duplicados y atípicos.
6. Segmentación con n.
7. Hallazgos y decisiones.

El informe documenta **T1 carga, T2 tipos, T3 duplicados, T4 faltantes/atípicos, T5 uniones/variables, T6 análisis, T7 segmentación/n y T8 reproducibilidad**. Es una correspondencia propuesta: la rúbrica recibida nombra T1-T8, pero no contiene sus enunciados oficiales. Debe cotejarse si el docente facilita esa guía. La rúbrica suministrada suma **95 puntos**, y no se atribuye automáticamente una calificación.

## Resultados de referencia

- Enero-agosto 2026: **88.304.451,13 barriles** observados; **363.392,80 barriles/día** en 243 días calendario.
- Sacha, Auca y Shushufindi concentran **51,75%** del crudo de ese período.
- Cohorte comparable de 14 activos, enero-agosto en ambos años: tasa conjunta **+7,53%** respecto de 2025. IN cae **6,25%**, con ocho meses en cada año.
- Cohorte histórica fija de 11 activos: Pearson entre cambios mensuales **0,017**, n=54 pares; intervalo exploratorio por bloques de 3 meses **[-0,202; 0,192]**. No demuestra independencia ni causalidad.

La tasa de un período divide el volumen total entre los días calendario de sus meses distintos. El promedio del precio cuenta cada mes una vez, no cada activo. n<12 advierte cobertura inferior a un ciclo anual; no es un umbral universal de significación. Las decisiones del dashboard tienen período fijo explícito y no se recalculan con los filtros.

## Verificación

`python -m unittest discover -s tests -v` comprueba fuentes sin modificaciones, unicidad y conservación de filas, conflictos por medida, tolerancia, invariancia al orden, precios faltantes, catálogo desconocido, ceros, claves de uniones, calendario bisiesto, cohorte y semilla. El notebook se ejecuta desde un kernel nuevo.

`reportes/qa_dashboard.json` registra **17 comprobaciones locales** de filtros, cobertura, selección vacía, rango inverso, descarga CSV, pestañas, ejes numéricos y vista móvil de 390 px. `docs/dashboard.png` muestra la versión revisada. Las pruebas de navegador son opcionales y requieren Node y Playwright; las dependencias del análisis y la aplicación están en `requirements.txt`.

Para repetir las pruebas de interfaz en un entorno con Node:

```bash
npm install --no-save playwright
npx playwright install chromium
node tests/dashboard.cjs
```

En Windows puede usarse `PLAYWRIGHT_CHANNEL=msedge` si Microsoft Edge está instalado. WebMCP es una mejora opcional y se detecta por disponibilidad; no se certificó su registro en un navegador con soporte nativo. El dashboard funciona sin ella.

La carpeta de clase solo se usa como referencia metodológica. No se copiaron sus archivos privados, sales, entornos ni otros conjuntos de datos. Para actualizar fuentes: revisar permisos, reemplazar de forma deliberada las copias, actualizar hashes, ejecutar todo y revisar cada interpretación antes de volver a publicar.
