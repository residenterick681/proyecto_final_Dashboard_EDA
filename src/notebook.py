"""Genera un notebook autónomo, didáctico y ejecutado, con sus fuentes incluidas."""
from pathlib import Path
import base64
import hashlib
import json
import sys
import tempfile
import textwrap
import uuid
import nbformat as nbf
from nbclient import NotebookClient
from jupyter_client import KernelManager
from .content import QUESTION, DICTIONARY

ROOT = Path(__file__).resolve().parents[1]


def embedded_source(embedded):
    """Presenta las mismas fuentes literales con comentarios, sin alterar sus bytes."""
    field_comments = {
        'archivo': 'Se registra el nombre interno con el que se recuperará este archivo.',
        'nombre_entregado': 'Se conserva el nombre que tenía el archivo entregado por el usuario.',
        'bytes': 'Se registra el tamaño original del archivo, medido en bytes.',
        'sha256': 'Se conserva la huella esperada para comprobar la identidad de la copia recuperada.',
        'origen': 'Se documenta la procedencia declarada de esta copia de los datos.',
        'base64': 'Se guardan los bytes originales codificados como texto Base64; no son datos simulados.',
    }
    lines = ['DATOS_INCORPORADOS = {  # Se crea el contenedor de las tres fuentes originales incorporadas.']
    for filename, data in embedded.items():
        lines.append(f'    {filename!r}: {{  # Se inicia el registro de la fuente {filename}.')
        for key, value in data.items():
            lines.append(f'        {key!r}: {value!r},  # {field_comments[key]}')
        lines.append('    },  # Se completa el registro de esta fuente y su contenido original.')
    lines.append('}  # Se completa el contenedor de los tres archivos que se abrirán en la siguiente celda.')
    return '\n'.join(lines)


def dictionary_source(dictionary):
    lines = ['DICCIONARIO = [  # Se define el significado, tipo, unidad y regla de los campos usados en el análisis.']
    for entry in dictionary:
        lines.append(f'    {entry!r},  # Se documenta el campo {entry[1]} de la tabla {entry[0]}.')
    lines += [
        ']  # Se completa la lista de definiciones del diccionario de datos.',
        'display(pd.DataFrame(DICCIONARIO, columns=["tabla", "campo", "tipo", "unidad", "regla"]))  # Se muestra el diccionario como una tabla de cinco columnas.',
    ]
    return '\n'.join(lines)


def build(root=ROOT, execute=True):
    root = Path(root)
    cells = []

    def md(text):
        first, separator, body = text.strip('\n').partition('\n')
        clean = first.lstrip() + separator + textwrap.dedent(body).rstrip()
        cells.append(nbf.v4.new_markdown_cell(clean))

    def code(text, *, tag=None, hidden=False):
        metadata = {}
        if tag:
            metadata['tags'] = [tag]
        if hidden:
            metadata['jupyter'] = {'source_hidden': True}
            metadata['tags'] = ['datos-incorporados', 'hide-input']
        cells.append(nbf.v4.new_code_cell(textwrap.dedent(text).strip(), metadata=metadata))

    md(f'''# EDA de producción petrolera: todo el proceso paso a paso
    **GRUPO 5 · MIACD02P01 · Notebook autónomo**

    **Pregunta principal:** {QUESTION}

    Este archivo contiene las fuentes originales incorporadas, el código de lectura y limpieza, los cálculos, la construcción de todas las gráficas, las interpretaciones, cinco preguntas adicionales y las decisiones. No importa código del proyecto ni lee resultados o imágenes elaborados previamente.

    **Cómo utilizarlo:** guarda este `.ipynb` en una carpeta de tu elección, ábrelo con Jupyter o VS Code, selecciona Python y ejecuta **Reiniciar kernel y ejecutar todo**, de arriba abajo. Para leer las explicaciones y salidas ya guardadas no necesitas volver a ejecutar.

    **Dependencias de ejecución:** Python 3.12; pandas 3.0.1, numpy 2.3.5, openpyxl 3.1.5, matplotlib 3.11.2 e ipykernel 7.4.0. Si tu entorno no las tiene, puedes instalarlas en su terminal con `python -m pip install pandas==3.0.1 numpy==2.3.5 openpyxl==3.1.5 matplotlib==3.11.2 ipykernel==7.4.0`. El notebook no instala programas automáticamente.

    Al ejecutar se crea `salidas_EDA_notebook/` con copias verificadas de las fuentes, tablas y gráficos. Esa carpeta es una **salida generada**; no necesitas descargarla ni preparar otros archivos para comenzar.

    **Comentarios por línea:** cada línea de código incluye una explicación en español después de `#`. Los comentarios no se ejecutan. Las líneas de cierre también indican qué estructura terminan.

    ## Mapa de lectura
    | Orden de ejecución | Qué aprenderás | Relación con la rúbrica |
    |---|---|---|
    | 0–1 | Herramientas, contexto y pregunta | EDA 1 |
    | 2.1–2.4 | Abrir los tres archivos y describirlos | EDA 2; T1–T2 |
    | 2.5–2.12 | Limpiar, unir, crear variables y auditar | Preparación para el EDA; T2–T5 |
    | 3 | Estadísticas y distribución | EDA 3; T6 |
    | 4 | Series, cohortes, correlación e incertidumbre | EDA 4; T6, T8 |
    | 5 | Interpretar la calidad encontrada | EDA 5; T3–T4 |
    | 6 | Segmentar, comparar y comprobar sensibilidad | EDA 6; T7 |
    | 7 | Cinco preguntas y decisiones | EDA 7 |
    | 8 | Validaciones, exportación y reproducibilidad | T8 |

    La limpieza se ejecuta antes de calcular estadísticas. El paso EDA 5 vuelve sobre sus resultados para interpretarlos; no oculta una limpieza ejecutada en otro archivo. T1–T8 es una correspondencia propuesta, porque la rúbrica recibida no incluye sus enunciados oficiales.
    ''')
    md('''## 0. Preparar herramientas y parámetros
    Importamos bibliotecas generales. `pd` es pandas, para tablas; `np` es NumPy, para cálculos; `plt` es Matplotlib, para construir las gráficas aquí mismo. `Path` maneja rutas y `hashlib` verifica las fuentes. La semilla 2026 controla el remuestreo, no genera producción ficticia.
    ''')
    code(r'''
    from pathlib import Path  # Se importa Path para construir rutas de carpetas y archivos.
    from importlib.metadata import version  # Se importa version para consultar qué versión de cada biblioteca está instalada.
    import base64  # Se importa base64 para recuperar los archivos originales guardados como texto en este notebook.
    import hashlib  # Se importa hashlib para comprobar la identidad de los archivos mediante una huella SHA-256.
    import json  # Se importa json para guardar resultados estructurados en archivos JSON.
    import sys  # Se importa sys para consultar la versión de Python que ejecuta el análisis.
    import numpy as np  # Se importa NumPy como np para realizar cálculos numéricos y remuestreos.
    import pandas as pd  # Se importa pandas como pd para leer, limpiar, unir y analizar tablas.
    import matplotlib.pyplot as plt  # Se importa pyplot como plt para crear y mostrar las gráficas.
    from matplotlib.colors import ListedColormap, BoundaryNorm  # Se importan herramientas que asignan un color concreto a cada categoría del mapa de calidad.
    from matplotlib.patches import Patch  # Se importa Patch para dibujar los recuadros de colores de la leyenda.
    from IPython.display import display, Markdown  # Se importan display y Markdown para mostrar tablas y explicaciones con formato.
    get_ipython().run_line_magic('matplotlib', 'inline')  # Se activa la visualización de las gráficas dentro del notebook; equivale a %matplotlib inline.

    SEED = 2026  # Se fija la semilla en 2026 para reproducir el mismo remuestreo aleatorio.
    KEY = ['anio', 'mes', 'activo']  # Se define la clave que identifica un registro: año, mes y activo.
    SMALL_N = 12  # Se fija en 12 observaciones el umbral de precaución para grupos con menos de un ciclo anual.
    SALIDAS = Path.cwd() / 'salidas_EDA_notebook'  # Se define la carpeta de resultados dentro del directorio desde el que se ejecuta el notebook.
    FUENTES = SALIDAS / 'fuentes'  # Se define la subcarpeta donde se recuperarán los tres archivos originales.
    FIGURAS = SALIDAS / 'figuras'  # Se define la subcarpeta donde se guardarán las gráficas creadas.
    for carpeta in [FUENTES, FIGURAS]:  # Se recorren las rutas FUENTES y FIGURAS, una carpeta a la vez.
        carpeta.mkdir(parents=True, exist_ok=True)  # Se crea cada carpeta y sus directorios superiores si hacen falta; si ya existe, se conserva.

    pd.set_option('display.max_columns', 25)  # Se permite mostrar hasta 25 columnas al presentar tablas de pandas.
    pd.set_option('display.max_rows', 20)  # Se permite mostrar hasta 20 filas por defecto para evitar salidas demasiado largas.
    plt.rcParams.update({  # Se comienza la configuración del aspecto general de todas las gráficas.
        'font.family': 'DejaVu Sans', 'font.size': 10,  # Se elige la fuente DejaVu Sans y un tamaño de letra de 10 puntos.
        'axes.spines.top': False, 'axes.spines.right': False,  # Se ocultan los bordes superior y derecho de los ejes.
        'figure.facecolor': 'white', 'axes.titleweight': 'bold',  # Se establece el fondo blanco de las figuras y los títulos en negrita.
    })  # Se cierra el diccionario y se aplica la configuración visual.
    AZUL, VERDE, CORAL, AMBAR = '#2079B0', '#098F75', '#D54163', '#DBA229'  # Se guardan cuatro códigos de color para reutilizarlos de forma consistente.
    print('Python:', sys.version.split()[0], '| Semilla:', SEED)  # Se muestran la versión de Python y la semilla utilizada.
    display(pd.DataFrame({  # Se prepara y muestra una tabla con las bibliotecas del análisis y sus versiones.
        'biblioteca': ['pandas', 'numpy', 'openpyxl', 'matplotlib', 'ipykernel'],  # Se define la lista de bibliotecas cuya versión se consultará.
        'version': [version(x) for x in ['pandas', 'numpy', 'openpyxl', 'matplotlib', 'ipykernel']],  # Se recorre esa lista y se obtiene la versión instalada de cada biblioteca.
    }))  # Se completa la tabla de versiones y se presenta en la salida de la celda.
    ''', tag='preparacion')
    md('''## 1. Contexto, pregunta y usuario · EDA 1
    **Usuario:** analista de planificación y supervisión de producción. Necesita distinguir variaciones productivas, cambios de cobertura y problemas de medición para priorizar revisiones.

    **Unidad de la tabla principal:** un activo en un mes. Las conclusiones describen los archivos aportados, no toda la producción nacional. Mayor volumen por día calendario no demuestra mayor eficiencia: faltan costos, pozos, paradas y días operativos.
    ''')
    code(r'''
    objetivos = pd.DataFrame([  # Se construye una tabla con las preguntas que orientan el análisis.
        {'pregunta': '¿Cómo evoluciona la producción?', 'unidad': 'activo-mes', 'salida': 'volumen, tasa diaria y n válido'},  # Se registra el objetivo de estudiar la evolución productiva a nivel de activo y mes.
        {'pregunta': '¿Qué activos conviene revisar?', 'unidad': 'activo y período equivalente', 'salida': 'cambio absoluto y porcentual'},  # Se registra el objetivo de priorizar activos comparando períodos equivalentes.
        {'pregunta': '¿El precio acompaña esos cambios?', 'unidad': 'mes de una cohorte fija', 'salida': 'correlación e incertidumbre descriptivas'},  # Se registra el objetivo de explorar la asociación del precio con una cohorte constante.
    ])  # Se cierra la lista de objetivos y se convierte en una tabla de pandas.
    display(objetivos)  # Se muestra la tabla de objetivos dentro del notebook.
    ''')
    md('''## 2. Origen, estructura y preparación · EDA 2
    ### 2.1. Los tres archivos originales incorporados · T1
    Se conserva una copia exacta de **un XLSX y dos CSV** aportados por el usuario. La celda siguiente es un contenedor de datos en Base64: convierte bytes en texto para transportarlos dentro del `.ipynb`. **No contiene una limpieza ni un análisis ocultos.** Puede aparecer plegada porque su contenido es largo; se puede expandir.

    Las huellas SHA-256 certifican identidad con las copias entregadas; no certifican que estas sean idénticas a una descarga oficial. El nombre «acumulada» del XLSX se interpreta como historia de volúmenes mensuales; no se aplica una diferencia como si cada fila fuera un acumulado anual. Las unidades adoptadas son barriles/mes para crudo y miles de pies cúbicos/mes para gas, según la documentación del proyecto; el XLSX no explicita estas unidades. Precio: USD/barril de referencia agregado, no precio por activo. El catálogo no tiene metadatos de procedencia adicionales.
    ''')
    manifest = json.loads((root/'data/crudos/manifest.json').read_text(encoding='utf-8'))
    embedded = {}
    for item in manifest:
        raw = (root/'data/crudos'/item['archivo']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('La fuente cambió: ' + item['archivo'])
        embedded[item['archivo']] = {**item, 'base64': base64.b64encode(raw).decode('ascii')}
    code(embedded_source(embedded), hidden=True)
    md('''### 2.2. Recuperar las fuentes y abrir los archivos · T1
    Primero decodificamos cada copia, verificamos su huella y la guardamos en la carpeta de salidas. Después usamos **`pd.read_excel()`** y **`pd.read_csv()`**. Aquí ocurre la lectura real de los datos.

    Si ya existe una copia con contenido diferente, el código se detiene para no reemplazarla inadvertidamente. `raw`, `prices_raw` y `catalog_raw` conservarán las tablas originales durante el análisis.
    ''')
    code(r'''
    trazabilidad = []  # Se crea una lista vacía para registrar la procedencia y las huellas de las fuentes.
    for nombre, datos in DATOS_INCORPORADOS.items():  # Se recorre cada nombre de archivo y su información incorporada en el notebook.
        contenido = base64.b64decode(datos['base64'], validate=True)  # Se decodifica el texto Base64 a sus bytes originales y se rechaza un formato inválido.
        huella = hashlib.sha256(contenido).hexdigest()  # Se calcula la huella SHA-256 del contenido recuperado, expresada en hexadecimal.
        assert huella == datos['sha256'], f'Copia incorporada alterada: {nombre}'  # Se detiene la ejecución si la huella no coincide con la copia original registrada.
        ruta = FUENTES / nombre  # Se construye la ruta donde se guardará este archivo original.
        if ruta.exists() and hashlib.sha256(ruta.read_bytes()).hexdigest() != huella:  # Se comprueba si ya existe un archivo en esa ruta con un contenido diferente.
            raise ValueError(f'Existe una copia distinta en {ruta}. Usa otra carpeta de ejecución.')  # Se genera un error para evitar sobrescribir una copia distinta sin advertirlo.
        ruta.write_bytes(contenido)  # Se guardan los bytes recuperados en la carpeta de fuentes.
        trazabilidad.append({'archivo': nombre, 'nombre_entregado': datos['nombre_entregado'],  # Se añade a la trazabilidad el nombre interno y el nombre con que se entregó el archivo.
                             'bytes': len(contenido), 'sha256': huella})  # Se añaden el tamaño en bytes y la huella; se completa el registro de esta fuente.

    raw = pd.read_excel(FUENTES / 'produccion_original.xlsx', sheet_name='Hoja1', engine='openpyxl')  # Se abre la hoja Hoja1 del Excel de producción usando openpyxl y se guarda la tabla en raw.
    prices_raw = pd.read_csv(FUENTES / 'precios_original.csv')  # Se abre el CSV de precios y se conserva su tabla original en prices_raw.
    catalog_raw = pd.read_csv(FUENTES / 'activos_original.csv')  # Se abre el CSV de nombres y códigos de activos y se conserva en catalog_raw.
    display(pd.DataFrame(trazabilidad))  # Se muestra una tabla con los archivos recuperados, sus tamaños y sus huellas.
    display(pd.DataFrame([  # Se prepara una tabla para comparar el tamaño de las tres fuentes.
        {'fuente': 'Producción', 'filas': raw.shape[0], 'columnas': raw.shape[1]},  # Se registra el número de filas y columnas de la fuente de producción.
        {'fuente': 'Precios', 'filas': prices_raw.shape[0], 'columnas': prices_raw.shape[1]},  # Se registra el número de filas y columnas de la fuente de precios.
        {'fuente': 'Catálogo', 'filas': catalog_raw.shape[0], 'columnas': catalog_raw.shape[1]},  # Se registra el número de filas y columnas del catálogo de activos.
    ]))  # Se completa y muestra la tabla de dimensiones de las fuentes.
    display(raw.head(), prices_raw.head(), catalog_raw.head())  # Se muestran las primeras cinco filas de cada fuente para revisar su estructura.
    ''', tag='T1-carga')
    md('''### 2.3. Inspeccionar antes de transformar · T2
    `info()` muestra tipos y valores no vacíos; `describe()` resume columnas. `isna().sum()` cuenta faltantes, incluidos los de columnas completamente vacías. Esta inspección ocurre antes de eliminarlas.
    ''')
    code(r'''
    raw.info()  # Se muestran las columnas, los tipos de datos y los conteos no nulos del Excel original.
    display(raw.describe(include='all'))  # Se muestran estadísticas descriptivas de todas las columnas, incluidas las no numéricas.
    display(raw.isna().sum().rename('faltantes').to_frame())  # Se cuentan los valores faltantes por columna y se presentan en una tabla llamada faltantes.
    ''', tag='T2-inspeccion')
    md('''### 2.4. Diccionario de los campos usados
    La siguiente tabla queda definida dentro del notebook. Los campos derivados se construirán en las celdas posteriores.
    ''')
    code(dictionary_source(DICTIONARY))
    md('''### 2.5. Normalizar columnas, códigos y tipos · T2
    Eliminamos únicamente columnas totalmente vacías. `copy()` evita modificar `raw`. Convertimos números con `errors='raise'`: un valor inválido debe generar un aviso. Los códigos se limpian de espacios y se pasan a mayúsculas. `fila_excel` permite volver al registro original, considerando el encabezado en la fila 1.
    ''')
    code(r'''
    columnas_vacias = raw.columns[raw.isna().all()].tolist()  # Se identifican las columnas cuyos valores están todos vacíos y se guardan sus nombres.
    d = raw.drop(columns=columnas_vacias).rename(columns={  # Se eliminan esas columnas vacías y se inicia el cambio de nombres de las columnas restantes.
        'AÑO': 'anio', 'MES': 'mes', 'ACTIVO': 'activo',  # Se renombran año, mes y activo con nombres uniformes para utilizarlos en el código.
        'CRUDO': 'crudo', 'GAS': 'gas',  # Se renombran las medidas CRUDO y GAS como crudo y gas.
    }).copy()  # Se termina el cambio de nombres y se crea una copia independiente de la tabla original.
    if set(d.columns) != set(KEY + ['crudo', 'gas']):  # Se comprueba si las columnas encontradas difieren de la estructura esperada.
        raise ValueError('La estructura de producción no coincide con la esperada.')  # Se detiene la ejecución si faltan columnas requeridas o aparecen columnas inesperadas.
    d['fila_excel'] = np.arange(2, len(d) + 2)  # Se registra el número de fila del Excel; se empieza en 2 porque la fila 1 contiene encabezados.
    for columna in ['anio', 'mes', 'crudo', 'gas']:  # Se recorren las cuatro columnas que deben contener valores numéricos.
        d[columna] = pd.to_numeric(d[columna], errors='raise')  # Se convierte cada columna a números y se genera un error si algún valor no es interpretable.
    if d[KEY].isna().any().any() or not d['mes'].between(1, 12).all():  # Se comprueba si faltan claves o si algún mes está fuera del intervalo de 1 a 12.
        raise ValueError('Falta una clave o hay un mes fuera de 1–12.')  # Se detiene la ejecución si una clave o un mes no es válido.
    if not (d[['anio', 'mes']] % 1 == 0).all().all():  # Se comprueba que año y mes no tengan decimales usando el residuo de dividir entre 1.
        raise ValueError('Año y mes deben ser enteros.')  # Se genera un error si año o mes contiene una parte decimal.
    d[['anio', 'mes']] = d[['anio', 'mes']].astype('int64')  # Se almacenan el año y el mes como números enteros de 64 bits.
    d['activo'] = d['activo'].astype('string').str.strip().str.upper()  # Se convierten los códigos de activo a texto, se quitan espacios externos y se usan mayúsculas.
    if d['activo'].eq('').any() or (d[['crudo', 'gas']] < 0).any().any():  # Se detectan códigos vacíos o volúmenes negativos de crudo o gas.
        raise ValueError('Hay códigos vacíos o volúmenes negativos que requieren revisión.')  # Se detiene la ejecución para revisar esos códigos o volúmenes inválidos.
    print('Columnas completamente vacías eliminadas:', len(columnas_vacias))  # Se informa cuántas columnas totalmente vacías se eliminaron.
    display(d.head(), d.dtypes.rename('tipo_final').to_frame())  # Se muestran las primeras filas normalizadas y el tipo final de cada columna.
    ''', tag='T2-tipos')
    md('''### 2.6. Identificar duplicados antes de consolidar · T3
    La clave válida es `(anio, mes, activo)`. Distinguimos copias exactas adicionales de claves que tienen varios registros potencialmente contradictorios. `keep=False` muestra todos los miembros de una clave repetida. Se conserva el detalle para auditar.
    ''')
    code(r'''
    exactos = d.duplicated(KEY + ['crudo', 'gas'])  # Se marcan las copias adicionales con la misma clave, crudo y gas; se conserva la primera.
    duplicates = d[d.duplicated(KEY, keep=False)].sort_values(KEY + ['fila_excel']).copy()  # Se extraen todas las filas de claves repetidas y se ordenan por clave y fila de origen.
    claves_repetidas = duplicates[KEY].drop_duplicates()  # Se obtiene una sola aparición de cada clave que tenía más de un registro.
    unicos = d.loc[~exactos].copy()  # Se crea una copia sin las repeticiones exactas marcadas; el símbolo ~ invierte la selección.
    print('Copias exactas adicionales:', int(exactos.sum()))  # Se muestra cuántas copias exactas adicionales se encontraron.
    print('Claves con más de una fila:', len(claves_repetidas))  # Se muestra cuántas combinaciones de año, mes y activo estaban repetidas.
    display(duplicates)  # Se presentan todas las filas con claves repetidas para poder auditarlas.
    ''', tag='T3-duplicados')
    md('''### 2.7. Consolidar una fila por activo-mes y registrar conflictos · T3–T4
    Revisamos crudo y gas por separado. Si los valores disponibles son equivalentes con tolerancia absoluta `1e-6`, usamos su media; si son contradictorios, dejamos esa medida como `NaN`. Si no hay valores, también permanece faltante. No elegimos arbitrariamente la primera fila ni anulamos la otra medida válida.

    `np.allclose(..., rtol=0)` no permite una tolerancia relativa adicional. Una discrepancia de 0,01 no se absorbe. Se conservan ceros legítimos y la lista de filas de origen.
    ''')
    code(r'''
    filas_consolidadas = []  # Se crea la lista donde se guardará un registro consolidado por activo y mes.
    lista_conflictos = []  # Se crea una lista separada para documentar las medidas contradictorias.
    for clave, grupo in unicos.groupby(KEY, sort=True, dropna=False):  # Se recorren los grupos que comparten año, mes y activo, ordenados por esa clave.
        registro = dict(zip(KEY, clave))  # Se asocian los nombres de la clave con sus valores para construir el registro del grupo.
        origen = d.loc[(d[KEY] == pd.Series(registro)).all(axis=1), 'fila_excel']  # Se recuperan todas las filas originales que coinciden con la clave, incluidas las copias exactas.
        registro['filas_origen'] = '|'.join(map(str, origen))  # Se unen los números de fila con el separador | para conservar su trazabilidad.
        registro['n_filas_origen'] = len(origen)  # Se cuenta cuántas filas originales dieron lugar a este registro consolidado.
        for variable in ['crudo', 'gas']:  # Se revisan por separado las medidas de crudo y de gas del mismo grupo.
            valores = grupo[variable].dropna().to_numpy(dtype=float)  # Se toman los valores no faltantes de la medida y se convierten en un arreglo numérico.
            equivalentes = len(valores) > 0 and np.allclose(valores, valores[0], atol=1e-6, rtol=0)  # Se verifica que existan valores y que todos coincidan con tolerancia absoluta de 0,000001, sin tolerancia relativa.
            registro[variable] = float(valores.mean()) if equivalentes else np.nan  # Se utiliza la media de los valores equivalentes; si faltan o se contradicen, se conserva NaN.
            registro['conflicto_' + variable] = len(valores) > 1 and not equivalentes  # Se marca como conflicto cuando hay varios valores disponibles que no son equivalentes.
            if registro['conflicto_' + variable]:  # Se comprueba si la medida que se está revisando presenta un conflicto.
                lista_conflictos.append({  # Se comienza un registro de auditoría para documentar este conflicto.
                    **dict(zip(KEY, clave)), 'variable': variable,  # Se guardan el año, el mes, el activo y el nombre de la medida contradictoria.
                    'valores': ' | '.join(format(v, '.12g') for v in valores),  # Se guardan los valores en conflicto como texto, con hasta 12 cifras significativas y separados por |.
                    'filas_origen': registro['filas_origen'],  # Se guardan las filas del Excel que permiten localizar los valores originales.
                    'tratamiento': 'NA; pendiente de validar con la fuente',  # Se documenta que la medida queda faltante y pendiente de validación con la fuente.
                })  # Se completa y añade el registro de conflicto a la lista de auditoría.
        filas_consolidadas.append(registro)  # Se añade el registro consolidado del grupo, después de revisar crudo y gas.

    df = pd.DataFrame(filas_consolidadas)  # Se convierte la lista de registros consolidados en la tabla principal df.
    conflicts = pd.DataFrame(lista_conflictos)  # Se convierte la lista de conflictos en una tabla para su revisión.
    df['fecha'] = pd.to_datetime(dict(year=df['anio'], month=df['mes'], day=1))  # Se crea una fecha mensual a partir del año y mes, usando el día 1 como referencia.
    assert not df.duplicated(KEY).any()  # Se comprueba que ya no existan dos filas con la misma clave.
    assert len(df) == len(d[KEY].drop_duplicates())  # Se comprueba que la consolidación conserve todas las claves distintas de las fuentes.
    print('Filas originales:', len(d), '| Claves consolidadas:', len(df))  # Se muestran los conteos de filas originales y de registros consolidados.
    display(conflicts)  # Se muestra la tabla de conflictos encontrados y su tratamiento.
    ''', tag='T3-conflictos')
    md('''### 2.8. Preparar precios y catálogo · T2–T5
    Cada mes debe tener un solo precio y cada código un solo nombre. Comprobar esa unicidad antes de unir evita multiplicar filas. Los precios deben ser positivos. La clave `activo` es un código nominal: no se convierte en número.
    ''')
    code(r'''
    prices = prices_raw.rename(columns={  # Se inicia la normalización de nombres de las columnas de precios.
        prices_raw.columns[0]: 'fecha', prices_raw.columns[1]: 'precio_usd_barril',  # Se renombra la primera columna como fecha y la segunda como precio_usd_barril.
    }).copy()  # Se termina el cambio de nombres y se crea una copia independiente de los precios originales.
    prices['fecha'] = pd.to_datetime(prices['fecha'], errors='raise')  # Se convierten las fechas a un tipo temporal y se avisa si alguna no es válida.
    prices['precio_usd_barril'] = pd.to_numeric(prices['precio_usd_barril'], errors='raise')  # Se convierten los precios a números y se rechazan valores no interpretables.
    if prices['fecha'].isna().any() or prices['fecha'].duplicated().any():  # Se comprueba si hay fechas vacías o más de un registro para una misma fecha.
        raise ValueError('Hay fechas de precio vacías o repetidas.')  # Se detiene la ejecución si la clave temporal de precios no es válida o única.
    if prices['precio_usd_barril'].isna().any() or (prices['precio_usd_barril'] <= 0).any():  # Se comprueba si faltan precios o si hay precios menores o iguales que cero.
        raise ValueError('Hay precios vacíos o no positivos.')  # Se genera un error para revisar los precios vacíos o no positivos.
    catalog = catalog_raw.rename(columns={'Activo': 'nombre_activo', 'Nomenclatura': 'activo'}).copy()  # Se renombran las columnas del catálogo y se conserva una copia independiente.
    catalog['activo'] = catalog['activo'].astype('string').str.strip().str.upper()  # Se uniforman los códigos del catálogo como texto en mayúsculas y sin espacios externos.
    if catalog['activo'].isna().any() or catalog['activo'].duplicated().any():  # Se comprueba si falta algún código del catálogo o si un código aparece más de una vez.
        raise ValueError('La clave del catálogo debe ser única y no vacía.')  # Se detiene la ejecución si la clave del catálogo no cumple la unicidad y presencia requeridas.
    display(prices.head(), catalog)  # Se muestran los primeros precios y el catálogo normalizado de activos.
    ''')
    md('''### 2.9. Unir sin perder producción · T5
    `how='left'` conserva todas las claves de producción aunque no tengan nombre o precio. `validate='many_to_one'` comprueba la relación muchos-a-uno. Si falta un nombre, etiquetamos el código para advertirlo; **no inferimos que AB16 y AIT sean el mismo activo**. El volumen y el precio faltantes no se rellenan.
    ''')
    code(r'''
    filas_antes = len(df)  # Se guarda la cantidad de registros antes de realizar las uniones.
    df = df.merge(catalog, on='activo', how='left', validate='many_to_one')  # Se añade el catálogo por código de activo conservando la producción y validando una relación muchos a uno.
    df['catalogo_faltante'] = df['nombre_activo'].isna()  # Se marca cada registro cuyo activo no encontró nombre en el catálogo.
    df['nombre_activo'] = df['nombre_activo'].fillna(df['activo'] + ' (sin catálogo)')  # Se etiqueta el nombre faltante con su propio código y la advertencia sin catálogo.
    df = df.merge(prices, on='fecha', how='left', validate='many_to_one')  # Se añaden los precios por fecha conservando todas las filas y validando un solo precio por fecha.
    assert len(df) == filas_antes  # Se comprueba que las uniones no hayan eliminado ni multiplicado registros de producción.
    display(df.loc[df['catalogo_faltante'], ['activo', 'nombre_activo']].drop_duplicates())  # Se muestran los códigos sin nombre validado, una sola vez por activo.
    display(df.loc[df['precio_usd_barril'].isna(), ['fecha', 'activo', 'crudo']])  # Se muestran la fecha, el activo y el crudo de los registros que no tienen precio asociado.
    ''', tag='T5-uniones')
    md('''### 2.10. Crear variables comparables · T5
    Dividimos el volumen mensual entre sus días calendario reales. Eso controla la duración de febrero y los meses de 30/31 días; no estima la tasa durante los días realmente operados. `log1p` calcula `ln(1+x)` para explorar la asimetría y admite cero. No se suman crudo y gas porque tienen unidades distintas.
    ''')
    code(r'''
    df['dias_mes'] = df['fecha'].dt.days_in_month  # Se calcula el número real de días de cada mes, incluidos los años bisiestos.
    df['crudo_diario'] = df['crudo'] / df['dias_mes']  # Se divide el crudo mensual entre los días calendario para obtener barriles por día.
    df['gas_diario'] = df['gas'] / df['dias_mes']  # Se divide el gas mensual entre los días calendario para obtener su tasa diaria.
    df['log1p_crudo'] = np.log1p(df['crudo'])  # Se calcula el logaritmo natural de 1 más el crudo para explorar la distribución sin excluir ceros.
    df['trimestre'] = df['fecha'].dt.quarter  # Se obtiene el trimestre del año al que pertenece cada registro mensual.
    display(df[['fecha', 'activo', 'crudo', 'dias_mes', 'crudo_diario', 'log1p_crudo']].head())  # Se muestran las primeras filas con el volumen y las variables derivadas para comprobar los cálculos.
    ''')
    md('''### 2.11. Marcar atípicos por activo · T4
    Se calculan Q1, Q3 e IQR dentro de cada activo para no confundir tamaños distintos de producción. Los valores fuera de `Q1 − 1,5·IQR` y `Q3 + 1,5·IQR` se marcan, pero se conservan. Cuando IQR es cero, cualquier desviación puede marcarse: no justifica eliminarla automáticamente.
    ''')
    code(r'''
    limites = []  # Se crea una lista para guardar los límites y conteos del análisis de atípicos.
    for activo, grupo in df.groupby('activo', observed=True):  # Se recorre cada activo con sus propios registros para comparar valores de una misma escala productiva.
        for variable in ['crudo_diario', 'gas_diario']:  # Se analizan por separado las tasas diarias de crudo y de gas.
            q1, q3 = grupo[variable].quantile([0.25, 0.75])  # Se calculan el primer y tercer cuartil, correspondientes al 25% y al 75% de los valores.
            iqr = q3 - q1  # Se calcula el rango intercuartílico restando el primer cuartil al tercero.
            inferior, superior = q1 - 1.5*iqr, q3 + 1.5*iqr  # Se calculan los límites inferior y superior mediante la regla de 1,5 veces el rango intercuartílico.
            marcas = (grupo[variable] < inferior) | (grupo[variable] > superior)  # Se marcan los valores que están por debajo o por encima de los límites del activo.
            df.loc[grupo.index, 'atipico_' + variable] = marcas  # Se guardan esas marcas en las filas correspondientes de la tabla principal sin eliminar los valores.
            limites.append({'activo': activo, 'variable': variable, 'n': int(grupo[variable].count()),  # Se inicia un registro con el activo, la medida y su número de valores no faltantes.
                            'q1': q1, 'q3': q3, 'limite_inferior': inferior,  # Se añaden los dos cuartiles y el límite inferior del grupo.
                            'limite_superior': superior, 'n_atipicos': int(marcas.sum())})  # Se añaden el límite superior y la cantidad de valores marcados; se completa el registro.
    fences = pd.DataFrame(limites)  # Se convierte la lista de límites en una tabla de auditoría.
    for columna in ['atipico_crudo_diario', 'atipico_gas_diario']:  # Se recorren las dos columnas creadas para identificar atípicos.
        df[columna] = df[columna].astype(bool)  # Se convierte cada columna de marcas a valores booleanos: verdadero o falso.
    df = df.sort_values(['fecha', 'activo']).reset_index(drop=True)  # Se ordenan los datos por fecha y activo y se crea un índice consecutivo desde cero.
    display(fences)  # Se muestran los límites, tamaños de grupo y cantidades de atípicos.
    ''', tag='T4-atipicos')
    md('''### 2.12. Revisar cobertura y construir la auditoría · T4
    Una fila vacía y un mes sin fila son problemas diferentes. Generamos el calendario y verificamos cada combinación activo-mes. Un hueco entre el primer y último registro es «sin registro interior»; antes o después de ese intervalo se clasifica como «fuera de cobertura observada». Ninguna categoría significa automáticamente producción cero o cierre operativo.
    ''')
    code(r'''
    calendario = pd.date_range(df['fecha'].min(), df['fecha'].max(), freq='MS')  # Se crea un calendario con el primer día de cada mes entre las fechas mínima y máxima de producción.
    cobertura = []  # Se crea la lista donde se registrará la cobertura de cada activo y mes.
    for activo, grupo in df.groupby('activo', observed=True):  # Se recorre cada activo junto con sus registros disponibles.
        fechas_presentes = set(grupo['fecha'])  # Se guardan las fechas observadas del activo en un conjunto para comprobar su presencia.
        for fecha in calendario:  # Se recorre cada mes del calendario completo del análisis.
            existe = fecha in fechas_presentes  # Se comprueba si ese activo tiene un registro en el mes examinado.
            if existe:  # Se elige este caso cuando el registro existe.
                estado = 'observado'  # Se clasifica la combinación como observada.
            elif grupo['fecha'].min() < fecha < grupo['fecha'].max():  # Se comprueba si un mes ausente queda entre el primer y el último registro del activo.
                estado = 'sin registro interior'  # Se clasifica la ausencia dentro de ese intervalo como hueco interior.
            else:  # Se elige el caso restante: el mes ausente está antes o después de la cobertura del activo.
                estado = 'fuera de cobertura observada'  # Se clasifica el mes como fuera de la cobertura observada, sin suponer producción cero.
            fila = grupo.loc[grupo['fecha'].eq(fecha)]  # Se selecciona la fila del activo correspondiente al mes; puede resultar vacía.
            cobertura.append({'fecha': fecha, 'activo': activo, 'estado': estado,  # Se inicia el registro de cobertura con la fecha, el activo y su clasificación.
                              'crudo_valido': bool(len(fila) and fila['crudo'].notna().all()),  # Se marca crudo válido solo si existe una fila y su medida de crudo no está vacía.
                              'gas_valido': bool(len(fila) and fila['gas'].notna().all())})  # Se aplica la misma comprobación al gas y se completa el registro de cobertura.
    coverage = pd.DataFrame(cobertura)  # Se transforma la lista de cobertura en una tabla.
    audit = {  # Se inicia un diccionario para reunir los resultados de la auditoría.
        'filas_originales': len(raw), 'filas_limpias': len(df),  # Se guardan las cantidades de filas originales y consolidadas.
        'copias_exactas_extra': int(exactos.sum()), 'claves_repetidas': len(claves_repetidas),  # Se guardan los conteos de copias exactas adicionales y de claves repetidas.
        'filas_redundantes': len(raw)-len(df), 'celdas_conflictivas': len(conflicts),  # Se registran las filas reducidas por consolidación y las medidas con conflicto.
        'faltantes_crudo': int(df['crudo'].isna().sum()), 'faltantes_gas': int(df['gas'].isna().sum()),  # Se cuentan y guardan los valores faltantes de crudo y de gas.
        'huecos_interiores': int(coverage['estado'].eq('sin registro interior').sum()),  # Se cuentan las combinaciones activo-mes clasificadas como huecos interiores.
        'filas_sin_catalogo': int(df['catalogo_faltante'].sum()),  # Se cuentan los registros que no encontraron un nombre validado en el catálogo.
        'meses_sin_precio': df.loc[df['precio_usd_barril'].isna(), 'fecha'].dt.strftime('%Y-%m').unique().tolist(),  # Se enumeran, sin repetir, los meses sin precio en formato año-mes.
        'ceros_gas_conservados': int(df['gas'].eq(0).sum()),  # Se cuenta cuántos valores de gas iguales a cero se conservaron.
        'atipicos_crudo': int(df['atipico_crudo_diario'].sum()),  # Se cuenta cuántas tasas de crudo quedaron marcadas como atípicas.
        'atipicos_gas': int(df['atipico_gas_diario'].sum()),  # Se cuenta cuántas tasas de gas quedaron marcadas como atípicas.
    }  # Se completa el diccionario de auditoría.
    display(pd.DataFrame(audit.items(), columns=['control', 'resultado']))  # Se muestran los controles de calidad junto con sus resultados.
    ''')
    md('''## 3. Análisis univariado · EDA 3 · T6
    ### 3.1. Estadísticas de una variable a la vez
    `count` cuenta valores válidos; `mean` y `median` describen centro; `std`, dispersión; `skew`, asimetría. Son estadísticas de registros activo-mes, no de una empresa ficticia promedio. El conjunto mezcla activos de tamaños distintos.
    ''')
    code(r'''
    estadisticas = df[['crudo', 'gas', 'crudo_diario']].agg(  # Se seleccionan crudo, gas y crudo diario para resumir sus valores por separado.
        ['count', 'mean', 'median', 'std', 'skew', 'min', 'max']  # Se solicitan el conteo válido, media, mediana, desviación estándar, asimetría, mínimo y máximo.
    )  # Se completa el cálculo y se guarda la tabla de estadísticas descriptivas.
    display(estadisticas)  # Se muestra la tabla de estadísticas de las tres medidas.
    display(Markdown(  # Se inicia una explicación con formato Markdown basada en los resultados calculados.
        f"**Lectura:** crudo tiene n={df['crudo'].count()} valores válidos. "  # Se incorpora al texto el número de registros con crudo válido.
        f"Media: {df['crudo'].mean():,.2f}; mediana: {df['crudo'].median():,.2f} bbl/activo-mes. "  # Se incorporan la media y la mediana del crudo con dos decimales y separador de miles.
        f"Asimetría: {df['crudo'].skew():.3f}. Comparar media y mediana ayuda a detectar una cola superior; "  # Se añade la asimetría con tres decimales y se explica cómo interpretar la diferencia entre media y mediana.
        "no describe por sí solo crecimiento temporal."  # Se añade la aclaración de que una distribución no demuestra crecimiento a lo largo del tiempo.
    ))  # Se unen los fragmentos de texto y se muestra la interpretación completa.
    ''')
    md('''### 3.2. Construir histogramas dentro del notebook
    `plt.subplots()` crea los ejes y `hist()` cuenta valores en intervalos. La gráfica izquierda usa barriles; la derecha muestra la transformación logarítmica. La función pequeña `mostrar_figura()` solo ajusta márgenes, guarda una copia y muestra la figura que acabamos de crear. Ninguna gráfica se lee de otro archivo.
    ''')
    code(r'''
    figuras_creadas = []  # Se crea una lista donde se registrarán los nombres de las figuras elaboradas.
    def mostrar_figura(fig, nombre):  # Se define una función reutilizable que recibe una figura y el nombre con que se guardará.
        """Guardar y mostrar la figura que se acaba de calcular en este notebook."""  # Se documenta el propósito de la función: guardar y mostrar la figura recién calculada.
        fig.tight_layout()  # Se ajustan automáticamente los márgenes para reducir solapamientos de títulos y etiquetas.
        fig.savefig(FIGURAS / nombre, dpi=150, bbox_inches='tight')  # Se guarda la figura como imagen a 150 puntos por pulgada y se recortan márgenes sobrantes.
        figuras_creadas.append(nombre)  # Se añade el nombre de la figura a la lista de gráficas generadas.
        plt.show()  # Se muestra la figura dentro de la salida del notebook.
        plt.close(fig)  # Se cierra la figura en memoria después de mostrarla para liberar recursos.

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))  # Se crea una figura de 12 por 4 pulgadas con dos gráficos en una misma fila.
    axes[0].hist(df['crudo'].dropna(), bins=25, color=AZUL, edgecolor='white')  # Se dibuja el histograma del crudo válido con 25 intervalos, barras azules y bordes blancos.
    axes[0].set(title='Distribución del crudo mensual', xlabel='Barriles por activo-mes', ylabel='Frecuencia')  # Se asignan el título y los nombres de los ejes al histograma del crudo mensual.
    axes[1].hist(df['log1p_crudo'].dropna(), bins=25, color=VERDE, edgecolor='white')  # Se dibuja el histograma del logaritmo transformado con 25 intervalos y barras verdes.
    axes[1].set(title='Distribución de ln(1 + crudo)', xlabel='Logaritmo transformado', ylabel='Frecuencia')  # Se asignan el título y los ejes al histograma de ln(1 + crudo).
    mostrar_figura(fig, '01_distribucion.png')  # Se ajusta, guarda y muestra la figura de las dos distribuciones usando la función definida.
    ''', tag='grafico-histograma')
    md('''### 3.3. Comparar distribuciones por activo con un diagrama de cajas
    Cada caja utiliza tasas diarias del mismo activo y muestra su mediana, dispersión y extremos. Los puntos fuera de los bigotes son observaciones que merecen revisión, no errores demostrados. La escala logarítmica permite ver activos grandes y pequeños; todos los valores válidos de crudo diario de estas fuentes son positivos.
    ''')
    code(r'''
    orden_activos = df.groupby('activo')['crudo_diario'].median().sort_values().index.tolist()  # Se ordenan los activos de menor a mayor mediana de crudo diario para facilitar su comparación.
    muestras = [df.loc[df['activo'].eq(a), 'crudo_diario'].dropna() for a in orden_activos]  # Se crea una muestra de tasas válidas para cada activo, respetando ese orden.
    assert all((muestra > 0).all() for muestra in muestras), 'La escala logarítmica exige valores positivos.'  # Se verifica que todas las tasas sean positivas antes de utilizar una escala logarítmica.
    fig, ax = plt.subplots(figsize=(12, 5))  # Se crea una figura de 12 por 5 pulgadas con un único eje.
    ax.boxplot(muestras, orientation='horizontal', tick_labels=orden_activos)  # Se dibuja una caja horizontal por activo, con su etiqueta correspondiente.
    ax.set_xscale('log')  # Se usa una escala logarítmica en el eje horizontal para comparar magnitudes muy diferentes.
    ax.set(title='Distribución del crudo diario por activo', xlabel='bbl/día calendario · escala logarítmica', ylabel='Activo')  # Se asignan el título, las unidades de crudo diario y la etiqueta de activos.
    ax.grid(axis='x', alpha=.15)  # Se añaden líneas verticales de cuadrícula en las marcas del eje x, con poca intensidad.
    mostrar_figura(fig, '02_cajas_activos.png')  # Se guarda y muestra la figura de distribuciones por activo.
    ''')
    md('''## 4. Análisis bivariado y temporal · EDA 4 · T6
    ### 4.1. Agregar por mes sin repetir el precio ni los días
    La función `serie_mensual()` se define aquí. Suma volúmenes disponibles y cuenta activos y valores válidos. `min_count=1` conserva NA si falta todo el grupo. Los días y el precio se toman una vez por mes: cada mes tiene un único precio porque ya se validó la tabla original.

    Una suma de todos los activos puede cambiar por cambios en su composición; por eso se acompaña de cobertura y después se construye una cohorte fija.
    ''')
    code(r'''
    def serie_mensual(tabla):  # Se define una función que resume por mes cualquier tabla de producción compatible.
        mensual = tabla.groupby('fecha').agg(  # Se agrupan las filas de la tabla por fecha y se comienzan a calcular sus resúmenes.
            crudo=('crudo', lambda s: s.sum(min_count=1)),  # Se suma el crudo disponible; si todos los valores faltan, se conserva un resultado faltante.
            gas=('gas', lambda s: s.sum(min_count=1)),  # Se suma el gas disponible aplicando la misma regla para grupos completamente vacíos.
            n_activos=('activo', 'nunique'), n_crudo=('crudo', 'count'), n_gas=('gas', 'count'),  # Se cuentan los activos distintos y los valores válidos de crudo y gas de cada mes.
            dias_mes=('dias_mes', 'first'), precio_usd_barril=('precio_usd_barril', 'first'),  # Se toman una vez los días y el precio del mes para no sumarlos por cada activo.
        ).reset_index()  # Se termina el resumen y se devuelve la fecha del índice a una columna normal.
        mensual['crudo_diario'] = mensual['crudo'] / mensual['dias_mes']  # Se calcula la tasa mensual conjunta de crudo por día calendario.
        mensual['gas_diario'] = mensual['gas'] / mensual['dias_mes']  # Se calcula la tasa mensual conjunta de gas por día calendario.
        return mensual  # Se devuelve la tabla mensual resultante para reutilizarla fuera de la función.

    monthly = serie_mensual(df)  # Se ejecuta la función sobre toda la producción limpia y se guarda la serie mensual.
    display(monthly.head())  # Se muestran las primeras cinco filas de la serie mensual calculada.
    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)  # Se crean dos gráficos verticales de 12 por 6 pulgadas que comparten el eje de fechas.
    axes[0].plot(monthly['fecha'], monthly['crudo_diario'], color=AZUL, linewidth=2)  # Se dibuja en azul la evolución del crudo diario agregado de los activos observados.
    axes[0].set(title='Crudo diario observado y cobertura mensual', ylabel='bbl/día calendario')  # Se asignan el título general y la unidad de medida al gráfico superior.
    axes[1].plot(monthly['fecha'], monthly['n_activos'], label='Activos con fila', color=VERDE)  # Se dibuja en verde el número mensual de activos que tienen un registro.
    axes[1].plot(monthly['fecha'], monthly['n_crudo'], label='Activos con crudo válido', color=CORAL, linestyle='--')  # Se dibuja con una línea coral discontinua el número de activos con crudo válido.
    axes[1].set(ylabel='Número de activos', xlabel='Mes')  # Se identifican los ejes del gráfico inferior como número de activos y mes.
    axes[1].legend()  # Se muestra la leyenda para diferenciar cobertura de registros y cobertura de crudo válido.
    for ax in axes:  # Se recorren los dos ejes de la figura.
        ax.grid(alpha=.15)  # Se añade una cuadrícula tenue a cada gráfico.
    mostrar_figura(fig, '03_serie_cobertura.png')  # Se guarda y muestra la figura que combina producción y cobertura mensual.
    ''')
    md('''### 4.2. Construir una cohorte fija y calcular cambios mensuales
    Seleccionamos activos con crudo válido en todos los meses. `pct_change(fill_method=None)` calcula `(valor actual / valor anterior − 1)` sin rellenar faltantes. Lo aplicamos sobre el calendario mensual completo **antes** de quitar los pares sin precio, para evitar saltar un hueco y tratar dos meses no consecutivos como vecinos.

    Un precio por mes no se convierte en muchas observaciones por repetirse entre activos. La unidad de esta asociación es un par mensual.
    ''')
    code(r'''
    n_meses_historia = df['fecha'].nunique()  # Se cuenta cuántos meses distintos contiene toda la historia de producción.
    conteos = df.groupby('activo')['crudo'].count()  # Se cuenta el número de registros con crudo válido de cada activo.
    cohorte = sorted(conteos[conteos.eq(n_meses_historia)].index.tolist())  # Se seleccionan y ordenan los activos con crudo válido en todos los meses de la historia.
    balanced = serie_mensual(df[df['activo'].isin(cohorte)])  # Se calcula la serie mensual utilizando únicamente esos activos constantes.
    assert balanced['fecha'].tolist() == list(calendario)  # Se verifica que la cohorte conserve todo el calendario mensual sin saltos.
    pares_niveles = balanced.dropna(subset=['crudo_diario', 'precio_usd_barril']).copy()  # Se seleccionan los meses con crudo diario y precio disponibles para comparar sus niveles.
    balanced['cambio_crudo_pct'] = balanced['crudo_diario'].pct_change(fill_method=None) * 100  # Se calcula la variación porcentual del crudo diario frente al mes previo sin rellenar faltantes.
    balanced['cambio_precio_pct'] = balanced['precio_usd_barril'].pct_change(fill_method=None) * 100  # Se calcula de igual forma la variación porcentual mensual del precio sobre el calendario completo.
    changes = balanced.dropna(subset=['cambio_crudo_pct', 'cambio_precio_pct']).copy()  # Se conservan los meses que tienen ambos cambios disponibles para formar pares válidos.
    pearson_niveles = pares_niveles[['crudo_diario', 'precio_usd_barril']].corr().iloc[0, 1]  # Se obtiene el coeficiente de Pearson entre los niveles de crudo diario y precio.
    pearson_cambios = changes[['cambio_crudo_pct', 'cambio_precio_pct']].corr().iloc[0, 1]  # Se obtiene el coeficiente de Pearson entre las variaciones porcentuales de ambas medidas.
    spearman_cambios = changes[['cambio_crudo_pct', 'cambio_precio_pct']].corr(method='spearman').iloc[0, 1]  # Se calcula Spearman sobre los cambios para explorar su asociación por rangos.
    print('Activos de la cohorte:', ', '.join(cohorte))  # Se muestran los códigos de los activos incluidos en la cohorte histórica.
    display(pd.DataFrame([{  # Se prepara una tabla de una fila con cobertura y asociaciones de la cohorte.
        'activos_constantes': len(cohorte), 'meses_productivos': len(balanced),  # Se incluyen el número de activos constantes y el número de meses productivos.
        'meses_con_precio': len(pares_niveles), 'n_cambios_pareados': len(changes),  # Se incluyen el número de meses con precio y el número efectivo de cambios mensuales pareados.
        'Pearson_niveles': pearson_niveles, 'Pearson_cambios': pearson_cambios,  # Se añaden las correlaciones de Pearson calculadas en niveles y en cambios.
        'Spearman_cambios': spearman_cambios,  # Se añade la correlación de Spearman calculada en los cambios.
    }]))  # Se completa y muestra la tabla de cobertura y correlaciones.
    ''')
    md('''### 4.3. Crear el gráfico de dispersión y explicar la asociación
    Cada punto es un mes: X muestra el cambio del precio y Y el cambio de la producción diaria de la cohorte. Las líneas en cero ayudan a distinguir aumentos y descensos. Los valores extremos se conservan y pueden influir en Pearson; Spearman ofrece una descripción adicional basada en rangos.
    ''')
    code(r'''
    fig, ax = plt.subplots(figsize=(10, 5))  # Se crea una figura de 10 por 5 pulgadas para el diagrama de dispersión.
    ax.scatter(changes['cambio_precio_pct'], changes['cambio_crudo_pct'], color=AZUL, alpha=.8, edgecolor='white', s=50)  # Se dibuja un punto por mes pareado: cambio del precio en x y cambio del crudo en y.
    ax.axhline(0, color='gray', linewidth=.8)  # Se dibuja una línea horizontal en cero para separar aumentos y descensos de producción.
    ax.axvline(0, color='gray', linewidth=.8)  # Se dibuja una línea vertical en cero para separar aumentos y descensos del precio.
    ax.set(title=f'Cohorte fija: n={len(changes)} meses pareados; Pearson r={pearson_cambios:.3f}',  # Se prepara el título indicando el número de pares y la correlación de Pearson con tres decimales.
           xlabel='Cambio mensual del precio (%)', ylabel='Cambio mensual del crudo diario (%)')  # Se identifican los ejes como cambios porcentuales mensuales del precio y del crudo diario.
    ax.grid(alpha=.15)  # Se añade una cuadrícula tenue para facilitar la lectura de los puntos.
    mostrar_figura(fig, '04_cambios_precio_produccion.png')  # Se guarda y muestra el diagrama de dispersión de los cambios mensuales.
    display(Markdown(  # Se comienza una interpretación escrita de las correlaciones calculadas.
        f'**Interpretación:** Pearson en cambios = {pearson_cambios:.3f}; Spearman = {spearman_cambios:.3f}. '  # Se incorporan al texto los coeficientes de Pearson y Spearman con tres decimales.
        'En estas fuentes no aparece una asociación lineal contemporánea fuerte. '  # Se añade la lectura de que estas fuentes no muestran una asociación lineal contemporánea fuerte.
        'Esto no demuestra independencia, no descarta rezagos y no identifica causas operativas. '  # Se aclara que la correlación no descarta relaciones con retraso ni identifica causas.
        'El precio es una referencia agregada: multiplicarlo por producción no estima ingresos efectivos.'  # Se aclara que el precio de referencia no permite calcular ingresos efectivos por simple multiplicación.
    ))  # Se completan y muestran los fragmentos de la interpretación.
    ''')
    md('''### 4.4. Programar el remuestreo por bloques · T6–T8
    La siguiente función también está escrita íntegramente aquí. Toma bloques circulares de meses y selecciona juntos los valores X e Y. Se repite 2.000 veces con semilla fija. Los percentiles 2,5 y 97,5 forman un intervalo exploratorio del 95 %.

    Los bloques preservan parte de la dependencia local; no garantizan estacionariedad ni cobertura estadística nominal. Se prueba longitud 3 y, como sensibilidad, 6. Con menos de 12 pares o una variable constante, la función no presenta una correlación utilizable. No se usa un p-valor que presuponga meses independientes.
    ''')
    code(r'''
    def correlacion_por_bloques(x, y, semilla=SEED, replicas=2000, bloque=3):  # Se define un remuestreo de correlación con semilla fija, 2000 réplicas y bloques de 3 meses por defecto.
        x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)  # Se convierten las dos series recibidas en arreglos numéricos de tipo flotante.
        if len(x) != len(y) or not (np.isfinite(x).all() and np.isfinite(y).all()):  # Se comprueba si difieren en longitud o contienen valores faltantes o infinitos.
            raise ValueError('Se necesitan pares completos de la misma longitud.')  # Se genera un error porque el cálculo requiere pares completos y válidos.
        if len(x) < SMALL_N or np.std(x) == 0 or np.std(y) == 0:  # Se comprueba si hay menos de 12 pares o alguna serie es constante, casos que impiden este análisis.
            return {'n': len(x), 'r': None, 'ic95': None, 'bloque': bloque,  # Se devuelve el tamaño del grupo sin estimar correlación ni intervalo cuando no se cumple la condición.
                    'replicas': replicas, 'semilla': semilla}  # Se completa esa respuesta registrando las réplicas y la semilla solicitadas.
        rng = np.random.default_rng(semilla)  # Se crea un generador aleatorio independiente con la semilla especificada para repetir el resultado.
        n = len(x)  # Se guarda la cantidad de pares mensuales disponibles.
        correlaciones = []  # Se crea una lista para almacenar las correlaciones de las muestras válidas.
        for _ in range(replicas):  # Se repite el remuestreo el número indicado de veces; el guion bajo señala que no se necesita el contador.
            inicios = rng.integers(0, n, size=int(np.ceil(n / bloque)))  # Se sortean posiciones iniciales suficientes para formar bloques que cubran n observaciones.
            indices = ((inicios[:, None] + np.arange(bloque)) % n).ravel()[:n]  # Se forman bloques consecutivos y circulares con el módulo n, se aplanan y se conservan n posiciones.
            if np.std(x[indices]) > 0 and np.std(y[indices]) > 0:  # Se comprueba que las dos series remuestreadas tengan variación antes de calcular su correlación.
                correlaciones.append(np.corrcoef(x[indices], y[indices])[0, 1])  # Se calcula y guarda Pearson usando los mismos índices para mantener emparejadas ambas series.
        return {'n': n, 'r': float(np.corrcoef(x, y)[0, 1]),  # Se devuelve el número de pares y la correlación observada en los datos originales.
                'ic95': np.quantile(correlaciones, [.025, .975]).tolist(),  # Se toman los percentiles 2,5% y 97,5% de las correlaciones remuestreadas como intervalo exploratorio.
                'bloque': bloque, 'replicas': replicas, 'semilla': semilla}  # Se completan los resultados con el tamaño de bloque, las réplicas solicitadas y la semilla.

    bootstrap3 = correlacion_por_bloques(changes['cambio_crudo_pct'], changes['cambio_precio_pct'])  # Se ejecuta el remuestreo de los cambios con bloques de 3 meses y los valores por defecto.
    bootstrap6 = correlacion_por_bloques(changes['cambio_crudo_pct'], changes['cambio_precio_pct'], bloque=6)  # Se repite con bloques de 6 meses para examinar la sensibilidad al tamaño de bloque.
    display(pd.DataFrame([bootstrap3, bootstrap6]))  # Se muestran los resultados de ambos tamaños de bloque en una tabla.
    display(Markdown(  # Se inicia la explicación del resultado del remuestreo con bloques de 3 meses.
        f"**Resultado:** r = {bootstrap3['r']:.3f}, n = {bootstrap3['n']}. "  # Se incorporan la correlación observada y el número de pares mensuales.
        f"Intervalo con bloques de 3 meses: [{bootstrap3['ic95'][0]:.3f}, {bootstrap3['ic95'][1]:.3f}]. "  # Se incorporan los extremos del intervalo exploratorio con tres decimales.
        'El intervalo incluye cero y valores de ambos signos. La evidencia disponible no permite sostener una relación lineal fuerte.'  # Se interpreta la inclusión de cero y de ambos signos sin afirmar una relación lineal fuerte.
    ))  # Se completa y muestra la explicación del intervalo obtenido.
    ''', tag='T8-remuestreo')
    md('''## 5. Interpretar la calidad encontrada · EDA 5 · T3–T4
    La limpieza ya se ejecutó en las celdas 2.5–2.12. Ahora interpretamos su auditoría y construimos un mapa de cobertura. Cada celda del mapa representa un activo-mes; el color no mide producción.

    Gris significa fuera de cobertura observada; ámbar, ausencia interior; coral, conflicto en una medida de un registro presente. No se imputan ceros, no se inventan nombres y no se eliminan atípicos para mejorar la apariencia de los resultados.
    ''')
    code(r'''
    display(conflicts)  # Se muestra el detalle de las medidas contradictorias que permanecen pendientes de validación.
    display(coverage.loc[coverage['estado'].eq('sin registro interior')])  # Se muestran los meses ausentes que están dentro de la cobertura de cada activo.
    display(Markdown(  # Se prepara una explicación de los resultados de calidad encontrados.
        f"**Auditoría:** {audit['copias_exactas_extra']} copias exactas adicionales; "  # Se incorpora el número de copias exactas adicionales detectadas.
        f"{audit['filas_redundantes']} filas redundantes en total; {len(df)} claves únicas. "  # Se incorporan las filas redundantes totales y las claves únicas que conserva la tabla.
        f"Persisten {audit['celdas_conflictivas']} celdas conflictivas y {audit['huecos_interiores']} huecos interiores. "  # Se incluyen los conteos de celdas conflictivas y de huecos interiores.
        f"Se conservaron {audit['ceros_gas_conservados']} ceros de gas, "  # Se informa cuántos valores de gas iguales a cero fueron conservados.
        f"{audit['atipicos_crudo']} marcas IQR de crudo y {audit['atipicos_gas']} de gas. "  # Se informa cuántas tasas de crudo y gas quedaron marcadas por la regla IQR.
        'AB16 queda identificado como sin catálogo; agosto de 2026 permanece sin precio.'  # Se recuerdan las carencias concretas del catálogo y del precio al cierre del período.
    ))  # Se completa y muestra el resumen de auditoría.
    estados = {'fuera de cobertura observada': 0, 'observado': 1, 'sin registro interior': 2}  # Se asigna un código numérico a cada categoría de cobertura para representarla con un color.
    mapa = coverage.assign(valor=coverage['estado'].map(estados)).pivot(index='activo', columns='fecha', values='valor')  # Se convierten las categorías a números y se construye una matriz de activos por meses.
    for fila in df.loc[df['conflicto_crudo'] | df['conflicto_gas']].itertuples():  # Se recorren los registros que presentan un conflicto en crudo o en gas.
        mapa.loc[fila.activo, fila.fecha] = 3  # Se asigna el código 3 a la celda del activo y mes con conflicto para destacarla.
    colores = ['#E2E8F0', VERDE, AMBAR, CORAL]  # Se define la paleta: gris para fuera de cobertura, verde para observado, ámbar para hueco y coral para conflicto.
    fig, ax = plt.subplots(figsize=(12, 6))  # Se crea una figura de 12 por 6 pulgadas para el mapa de calidad.
    ax.imshow(mapa.to_numpy(), aspect='auto', cmap=ListedColormap(colores),  # Se representa la matriz con una paleta discreta y celdas adaptadas al tamaño del gráfico.
              norm=BoundaryNorm([-.5, .5, 1.5, 2.5, 3.5], 4), interpolation='nearest')  # Se delimitan las cuatro categorías numéricas y se evita suavizar sus colores entre celdas.
    ax.set_yticks(range(len(mapa)), mapa.index)  # Se coloca una etiqueta por activo en el eje vertical.
    marcas_x = sorted(set(list(range(0, len(mapa.columns), 6)) + [len(mapa.columns)-1]))  # Se selecciona una etiqueta temporal cada seis meses y se incluye el último mes.
    if len(marcas_x) > 1 and marcas_x[-1] - marcas_x[-2] < 3:  # Se comprueba si las dos últimas etiquetas quedarían separadas por menos de tres meses.
        marcas_x.pop(-2)  # Se retira la penúltima etiqueta para evitar que su texto se solape con la última.
    ax.set_xticks(marcas_x, [mapa.columns[i].strftime('%Y-%m') for i in marcas_x], rotation=35, ha='right')  # Se escriben las fechas como año-mes, inclinadas 35 grados y alineadas a la derecha.
    ax.set(title=f'Cobertura y conflictos: {len(mapa)} activos × {len(mapa.columns)} meses', xlabel='Mes', ylabel='Activo')  # Se asigna el título con los tamaños de la matriz y se identifican los ejes.
    ax.legend(handles=[Patch(facecolor=c, label=t) for c, t in zip(colores,  # Se comienza una leyenda creando un recuadro por cada combinación de color y categoría.
              ['Fuera de cobertura', 'Registro observado', 'Hueco interior', 'Conflicto'])],  # Se asignan los nombres legibles de las cuatro categorías de calidad.
              loc='upper center', bbox_to_anchor=(.5, -.24), ncol=4, frameon=False)  # Se sitúa la leyenda centrada debajo del gráfico, en cuatro columnas y sin marco.
    mostrar_figura(fig, '05_mapa_calidad.png')  # Se guarda y muestra el mapa de cobertura y conflictos.
    ''', tag='grafico-calidad')
    md('''## 6. Segmentación y comparación · EDA 6 · T7
    ### 6.1. Agrupar por activo y año con n explícito
    `size` cuenta filas y `count` valores no vacíos. La media mensual de tasas diarias y su mediana son resúmenes de distribución; la tasa del período que usaremos para comparar años se calcula aparte como volumen total dividido entre días del período.

    **n < 12** activa una precaución por cobertura menor a un ciclo anual. No es un umbral universal de significación ni garantiza que con 12 meses las observaciones sean independientes.
    ''')
    code(r'''
    groups = df.groupby(['activo', 'nombre_activo', 'anio'], observed=True).agg(  # Se agrupan los registros por código de activo, nombre y año para describir cada segmento.
        n_registros=('fecha', 'size'), n_crudo=('crudo', 'count'), n_gas=('gas', 'count'),  # Se cuentan las filas totales y los valores válidos de crudo y gas de cada grupo.
        n_precio=('precio_usd_barril', 'count'),  # Se cuenta cuántos registros del grupo tienen un precio disponible.
        crudo_total=('crudo', lambda s: s.sum(min_count=1)),  # Se suma el crudo del grupo, conservando un faltante si no existe ningún valor válido.
        media_crudo_diario=('crudo_diario', 'mean'), mediana_crudo_diario=('crudo_diario', 'median'),  # Se calculan la media y la mediana de las tasas diarias mensuales del grupo.
        gas_total=('gas', lambda s: s.sum(min_count=1)),  # Se suma el gas del grupo con la misma protección para grupos sin valores válidos.
    ).reset_index()  # Se completa el resumen y se convierten las claves de agrupación en columnas.
    groups['grupo_pequeno'] = groups['n_crudo'] < SMALL_N  # Se advierte como grupo pequeño al que tiene menos de 12 medidas de crudo válidas.
    with pd.option_context('display.max_rows', None):  # Se habilita temporalmente la visualización de todas las filas para mostrar cada segmento.
        display(groups)  # Se muestra la tabla completa con el n de cada medida y la advertencia de grupos pequeños.
    ''', tag='T7-segmentacion')
    md('''### 6.2. Comparar los mismos meses y los mismos activos
    El último año observado llega hasta agosto. Seleccionamos enero-agosto de ambos años y conservamos solo activos con crudo válido en todos esos meses. Cada activo tiene su n actual y anterior.

    Para el total de la cohorte, **los días se cuentan una sola vez por mes**, no una vez por activo. Porcentajes de varios activos no se suman ni se promedian sin considerar el volumen.
    ''')
    code(r'''
    anio_actual = int(df['anio'].max())  # Se identifica el año más reciente disponible en la tabla de producción.
    mes_corte = int(df.loc[df['anio'].eq(anio_actual), 'mes'].max())  # Se identifica el último mes disponible de ese año para fijar el corte de comparación.
    actual = df[df['anio'].eq(anio_actual) & df['mes'].le(mes_corte)].copy()  # Se seleccionan los registros del año actual hasta el mes de corte y se crea una copia.
    anterior = df[df['anio'].eq(anio_actual - 1) & df['mes'].le(mes_corte)].copy()  # Se seleccionan los mismos meses del año anterior y se crea una copia.
    n_actual = actual.groupby('activo')['crudo'].count()  # Se cuenta cuántos meses de crudo válido tiene cada activo en el período actual.
    n_anterior = anterior.groupby('activo')['crudo'].count()  # Se cuenta cuántos meses de crudo válido tiene cada activo en el período anterior.
    comunes = sorted(set(n_actual[n_actual.eq(mes_corte)].index) & set(n_anterior[n_anterior.eq(mes_corte)].index))  # Se conservan los activos con todos los meses válidos en ambos períodos mediante la intersección de conjuntos.
    comparaciones = []  # Se crea una lista para guardar las comparaciones individuales de esos activos.
    for activo in comunes:  # Se recorre cada activo con cobertura completa en los dos años.
        ga = actual[actual['activo'].eq(activo)]  # Se seleccionan los registros de ese activo en el período actual.
        gb = anterior[anterior['activo'].eq(activo)]  # Se seleccionan sus registros del período anterior.
        tasa_actual = ga['crudo'].sum(min_count=1) / ga['dias_mes'].sum()  # Se divide el volumen actual del activo entre sus días calendario totales para obtener la tasa del período.
        tasa_anterior = gb['crudo'].sum(min_count=1) / gb['dias_mes'].sum()  # Se calcula la tasa del mismo activo en el período anterior de igual manera.
        comparaciones.append({'activo': activo, 'n_actual': len(ga), 'n_anterior': len(gb),  # Se empieza el registro de comparación con el código y los tamaños de ambos grupos.
                              'diario_actual': tasa_actual, 'diario_anterior': tasa_anterior,  # Se guardan las tasas diarias actual y anterior del activo.
                              'cambio_pct': 100*(tasa_actual/tasa_anterior-1) if tasa_anterior > 0 else np.nan,  # Se calcula el cambio porcentual relativo al año anterior; si su tasa no es positiva, se deja NaN.
                              'cambio_diario': tasa_actual-tasa_anterior})  # Se guarda la diferencia absoluta de tasas y se completa el registro del activo.
    comparison = pd.DataFrame(comparaciones).sort_values('cambio_diario').reset_index(drop=True)  # Se crea una tabla ordenada desde la mayor pérdida absoluta hasta el mayor aumento.
    actual_comun = actual[actual['activo'].isin(comunes)].copy()  # Se seleccionan los registros actuales de todos los activos comparables.
    anterior_comun = anterior[anterior['activo'].isin(comunes)].copy()  # Se seleccionan los registros anteriores de esos mismos activos.
    dias_actual = actual_comun[['fecha', 'dias_mes']].drop_duplicates()['dias_mes'].sum()  # Se suman los días del período actual una sola vez por mes, sin repetirlos por activo.
    dias_anterior = anterior_comun[['fecha', 'dias_mes']].drop_duplicates()['dias_mes'].sum()  # Se suman los días del período anterior aplicando la misma regla.
    diario_actual_comun = actual_comun['crudo'].sum() / dias_actual  # Se calcula la tasa diaria conjunta de la cohorte comparable en el período actual.
    diario_anterior_comun = anterior_comun['crudo'].sum() / dias_anterior  # Se calcula la tasa diaria conjunta de la misma cohorte en el período anterior.
    cambio_comparable_pct = 100*(diario_actual_comun/diario_anterior_comun - 1)  # Se calcula la variación porcentual de la tasa conjunta entre ambos períodos.
    print('Activos comparables:', ', '.join(comunes))  # Se muestran los códigos de los activos utilizados en la comparación.
    print('Días actuales/anterior:', dias_actual, '/', dias_anterior)  # Se muestran los días calendario de cada período para verificar su comparabilidad.
    print('n activo-mes actual/anterior:', len(actual_comun), '/', len(anterior_comun))  # Se muestran las cantidades de registros activo-mes de ambos períodos.
    display(comparison)  # Se presenta la comparación individual de tasas, variaciones y tamaños de grupo.
    ''', tag='T7-comparacion')
    md('''### 6.3. Graficar la comparación conjunta
    Usamos barras que parten de cero, con la misma unidad y el mismo período. El título especifica n y cobertura. Un aumento de esta tasa es un cambio descriptivo del volumen por día; su estabilidad se comprobará en la sección 6.6.
    ''')
    code(r'''
    fig, ax = plt.subplots(figsize=(9, 4.5))  # Se crea una figura de 9 por 4,5 pulgadas para comparar los dos años.
    barras = ax.bar([str(anio_actual-1), str(anio_actual)], [diario_anterior_comun, diario_actual_comun], color=[AZUL, VERDE], width=.55)  # Se dibuja una barra por año con su tasa diaria conjunta, usando azul para el anterior y verde para el actual.
    ax.bar_label(barras, labels=[f'{diario_anterior_comun:,.2f}', f'{diario_actual_comun:,.2f}'], padding=6)  # Se añaden a las barras las tasas con dos decimales y espacio para facilitar la lectura.
    ax.set(title=f'Mismos {len(comunes)} activos y {mes_corte} meses/año · cambio {cambio_comparable_pct:+.2f}%',  # Se construye el título con el número de activos, meses por año y cambio porcentual.
           ylabel='Barriles por día calendario', xlabel='Año', ylim=(0, max(diario_actual_comun, diario_anterior_comun)*1.18))  # Se etiquetan los ejes y se deja un 18% de espacio por encima de la barra más alta.
    ax.grid(axis='y', alpha=.12)  # Se añade una cuadrícula tenue a partir de los valores del eje vertical.
    ax.set_axisbelow(True)  # Se sitúa la cuadrícula por debajo de las barras para que no tape sus colores.
    mostrar_figura(fig, '06_comparacion_conjunta.png')  # Se guarda y muestra la comparación conjunta de los mismos activos y meses.
    ''')
    md('''### 6.4. Identificar el impacto absoluto y relativo por activo
    Las barras muestran bbl/día ganados o perdidos, y las etiquetas añaden el porcentaje. Esto evita priorizar únicamente un porcentaje grande de un activo de volumen pequeño. Se conserva la tabla anterior para consultar diferencias demasiado pequeñas para verse a esta escala.
    ''')
    code(r'''
    fig, ax = plt.subplots(figsize=(12, 6))  # Se crea una figura de 12 por 6 pulgadas para comparar los aportes de cada activo.
    colores_impacto = [VERDE if x >= 0 else CORAL for x in comparison['cambio_diario']]  # Se asigna verde a cambios no negativos y coral a descensos de producción diaria.
    barras = ax.barh(comparison['activo'], comparison['cambio_diario'], color=colores_impacto)  # Se dibuja una barra horizontal por activo con su cambio absoluto en barriles por día.
    etiquetas = [f'{r.cambio_diario:+,.1f} | {r.cambio_pct:+.1f}%' for r in comparison.itertuples()]  # Se construye una etiqueta por activo con su cambio absoluto y su porcentaje, ambos con signo.
    ax.bar_label(barras, labels=etiquetas, padding=5, fontsize=9)  # Se añaden esas etiquetas junto a las barras con un tamaño de letra de 9 puntos.
    ax.set(xlim=(-3000, 7000), title='¿Qué activos aportan aumentos y cuáles requieren revisión?',  # Se fija un rango horizontal adecuado para estas fuentes y se plantea la pregunta de priorización en el título.
           xlabel='Cambio absoluto en bbl/día; etiqueta: cambio absoluto y porcentual', ylabel='Activo')  # Se identifican el cambio absoluto, el contenido de las etiquetas y los activos del eje vertical.
    ax.axvline(0, color='gray', linewidth=.8)  # Se dibuja una línea en cero para distinguir aportes positivos y negativos.
    ax.grid(axis='x', alpha=.12)  # Se añade una cuadrícula tenue referida al eje de cambios absolutos.
    ax.set_axisbelow(True)  # Se coloca la cuadrícula detrás de las barras.
    mostrar_figura(fig, '07_impacto_activos.png')  # Se guarda y muestra la figura de aumentos y descensos por activo.
    mayor_caida = comparison.iloc[0]  # Se toma la primera fila de la comparación ordenada, correspondiente a la mayor caída absoluta.
    print('Mayor descenso absoluto:', mayor_caida['activo'], '| bbl/día:', round(mayor_caida['cambio_diario'], 2))  # Se muestran el código de ese activo y su pérdida diaria redondeada a dos decimales.
    print('Activos con aumento:', int(comparison['cambio_diario'].gt(0).sum()),  # Se empieza a mostrar el conteo de activos cuyo cambio diario es estrictamente positivo.
          '| con descenso:', int(comparison['cambio_diario'].lt(0).sum()))  # Se añade el conteo de activos cuyo cambio diario es estrictamente negativo.
    ''')
    md('''### 6.5. Medir concentración del volumen observado
    Aquí se usa todo el período actual observado, incluidos los activos que no entraron en la comparación interanual. La participación es volumen del activo dividido entre volumen observado total. No mide rentabilidad, reservas o probabilidad de falla.
    ''')
    code(r'''
    volumenes = actual.groupby('activo')['crudo'].sum(min_count=1).sort_values(ascending=False)  # Se suma el crudo actual de cada activo y se ordenan los volúmenes de mayor a menor.
    participaciones = 100*volumenes/volumenes.sum()  # Se calcula el porcentaje que representa cada activo sobre el volumen total del período.
    top3 = volumenes.head(3).index.tolist()  # Se obtienen los códigos de los tres activos con mayor volumen observado.
    top3_pct = float(participaciones.loc[top3].sum())  # Se suman las participaciones de esos tres activos para medir su concentración conjunta.
    dias_periodo_actual = actual[['fecha', 'dias_mes']].drop_duplicates()['dias_mes'].sum()  # Se cuentan los días del período actual una sola vez por mes, sin multiplicarlos por activo.
    crudo_actual = float(volumenes.sum())  # Se guarda el volumen total del período actual como número de tipo flotante.
    concentracion = pd.DataFrame({'crudo_bbl': volumenes, 'participacion_pct': participaciones,  # Se prepara una tabla de concentración con el volumen y la participación por activo.
                                 'n_meses_crudo': actual.groupby('activo')['crudo'].count()})  # Se añade el número de meses con crudo válido de cada activo y se completa la tabla.
    display(concentracion)  # Se muestra la tabla de concentración y cobertura del período actual.
    grafico = participaciones.sort_values()  # Se ordenan las participaciones de menor a mayor para dibujarlas horizontalmente.
    fig, ax = plt.subplots(figsize=(11, 6))  # Se crea una figura de 11 por 6 pulgadas para el gráfico de concentración.
    barras = ax.barh(grafico.index, grafico.values, color=[VERDE if a in top3 else AZUL for a in grafico.index])  # Se dibujan las participaciones y se destacan en verde los tres mayores aportantes.
    ax.bar_label(barras, labels=[f'{v:.2f}%' for v in grafico.values], padding=4)  # Se añaden etiquetas con el porcentaje de cada activo, expresado con dos decimales.
    ax.set(title=f'Concentración en {anio_actual}: {", ".join(top3)} reúnen {top3_pct:.2f}%',  # Se construye el título con el año, los tres códigos y su participación conjunta.
           xlabel='Porcentaje del crudo observado', ylabel='Activo', xlim=(0, grafico.max()+5))  # Se etiquetan los ejes y se deja espacio a la derecha para los porcentajes.
    ax.grid(axis='x', alpha=.12)  # Se añade una cuadrícula tenue en el eje de participaciones.
    ax.set_axisbelow(True)  # Se coloca la cuadrícula detrás de las barras.
    mostrar_figura(fig, '08_concentracion.png')  # Se guarda y muestra la figura de concentración del volumen observado.
    ''')
    md('''### 6.6. Comprobar si el aumento depende de un mes excepcional
    La comparación conjunta puede ocultar diferencias mensuales. Comparamos la misma cohorte en cada mes y agregamos una sensibilidad: excluir **julio de ambos años**, manteniendo los demás meses y días equivalentes.

    Esta comprobación se añadió al profundizar en la toma de decisiones. No borra julio de las fuentes ni reemplaza la comparación principal. Permite separar un aumento acumulado de una mejora sostenida y evita atribuir causas que no están en los datos.
    ''')
    code(r'''
    mensual_actual = actual_comun.groupby('mes').agg(crudo_actual=('crudo', 'sum'), dias_actual=('dias_mes', 'first'))  # Se agrupa la cohorte actual por mes, sumando el crudo y tomando los días del mes una sola vez.
    mensual_anterior = anterior_comun.groupby('mes').agg(crudo_anterior=('crudo', 'sum'), dias_anterior=('dias_mes', 'first'))  # Se realiza el mismo resumen para la cohorte del año anterior.
    comparacion_meses = mensual_actual.join(mensual_anterior, how='inner')  # Se unen ambos resúmenes por número de mes y se conservan los meses presentes en los dos años.
    comparacion_meses['diario_actual'] = comparacion_meses['crudo_actual']/comparacion_meses['dias_actual']  # Se calcula la tasa diaria conjunta de cada mes del año actual.
    comparacion_meses['diario_anterior'] = comparacion_meses['crudo_anterior']/comparacion_meses['dias_anterior']  # Se calcula la tasa diaria conjunta de cada mes del año anterior.
    comparacion_meses['cambio_pct'] = 100*(comparacion_meses['diario_actual']/comparacion_meses['diario_anterior']-1)  # Se calcula la variación porcentual interanual de cada mes comparable.
    sin_julio = comparacion_meses.loc[comparacion_meses.index != 7]  # Se prepara una comparación alternativa que excluye julio, mes 7, en ambos años.
    tasa_sin_julio_actual = sin_julio['crudo_actual'].sum()/sin_julio['dias_actual'].sum()  # Se calcula la tasa del período actual sin julio a partir de sus volúmenes y días restantes.
    tasa_sin_julio_anterior = sin_julio['crudo_anterior'].sum()/sin_julio['dias_anterior'].sum()  # Se calcula la tasa del período anterior excluyendo también julio.
    cambio_sin_julio_pct = 100*(tasa_sin_julio_actual/tasa_sin_julio_anterior-1)  # Se calcula el cambio porcentual entre las dos tasas sin julio para estudiar la sensibilidad.
    meses_en_descenso = int(comparacion_meses['cambio_pct'].lt(0).sum())  # Se cuentan los meses cuyo cambio interanual es negativo.
    display(comparacion_meses)  # Se muestra el detalle de volúmenes, días, tasas y cambios por mes.
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))  # Se crea una figura con dos gráficos en una fila para comparar evolución y sensibilidad.
    axes[0].plot(comparacion_meses.index, comparacion_meses['diario_anterior'], marker='o', color=AZUL, label=str(anio_actual-1))  # Se dibuja la tasa mensual del año anterior con puntos y una línea azul.
    axes[0].plot(comparacion_meses.index, comparacion_meses['diario_actual'], marker='o', color=VERDE, label=str(anio_actual))  # Se dibuja la tasa mensual del año actual con puntos y una línea verde.
    axes[0].set(title='Cohorte idéntica, mes por mes', xlabel='Mes', ylabel='bbl/día calendario', xticks=comparacion_meses.index)  # Se asignan título, unidades y una marca por mes al primer gráfico.
    axes[0].legend()  # Se muestra la leyenda que identifica cada año en las dos líneas.
    barras = axes[1].bar(['Todos los meses', 'Sin julio en ambos años'], [cambio_comparable_pct, cambio_sin_julio_pct], color=[VERDE, CORAL])  # Se dibujan dos barras para contrastar el cambio con todos los meses y el cambio sin julio.
    axes[1].bar_label(barras, labels=[f'{cambio_comparable_pct:+.2f}%', f'{cambio_sin_julio_pct:+.2f}%'], padding=5)  # Se etiquetan las barras con su variación porcentual y signo, usando dos decimales.
    axes[1].axhline(0, color='gray', linewidth=.8)  # Se dibuja una línea en cero para distinguir mejora y descenso en esta comparación.
    axes[1].set(title='Sensibilidad de la comparación', ylabel='Variación interanual (%)', ylim=(-4, 10))  # Se asignan el título, la unidad porcentual y un rango vertical apropiado para estos resultados.
    mostrar_figura(fig, '09_sensibilidad_julio.png')  # Se guarda y muestra la figura de sensibilidad al mes de julio.
    display(Markdown(  # Se prepara la interpretación escrita de la comparación mensual.
        f'**Lectura:** el cambio conjunto es {cambio_comparable_pct:+.2f}%, pero {meses_en_descenso} de '  # Se incorpora el cambio acumulado y se comienza a indicar cuántos meses presentan descenso.
        f'{len(comparacion_meses)} meses muestran descenso. Sin julio en ambos años, el cambio es '  # Se añade el total de meses comparados y se introduce el resultado de excluir julio.
        f'{cambio_sin_julio_pct:+.2f}%: n={len(sin_julio)} meses por activo/año y '  # Se incorporan el cambio sin julio y el número de meses que quedan por activo y año.
        f'{int(sin_julio["dias_actual"].sum())} días actuales. El resultado depende de la baja base de julio de 2025. '  # Se añaden los días actuales del período reducido y la advertencia sobre la baja base de julio de 2025.
        'Antes de afirmar mejora sostenida, se debe conciliar ese mes y consultar información operativa.'  # Se propone conciliar ese mes y consultar información operativa antes de afirmar una mejora sostenida.
    ))  # Se completa y muestra la interpretación de la sensibilidad.
    ''', tag='sensibilidad-julio')
    md('''## 7. Hallazgos, cinco preguntas y decisiones · EDA 7
    ### 7.1. Responder la pregunta principal
    Las respuestas se construyen con las variables calculadas en este notebook. Las referencias a figuras indican celdas anteriores del mismo archivo, no documentos externos.
    ''')
    code(r'''
    display(Markdown(  # Se inicia una respuesta con formato a la pregunta principal del proyecto.
        '**¿Qué mejoras y oportunidades se identifican mediante las variaciones?** '  # Se escribe como encabezado la pregunta sobre mejoras y oportunidades de producción.
        f'La cohorte comparable aumenta {cambio_comparable_pct:.2f}% en el acumulado, pero la sensibilidad sin julio '  # Se incorpora el cambio acumulado de la cohorte comparable con dos decimales.
        f'es {cambio_sin_julio_pct:.2f}%. No se puede afirmar una mejora sostenida solo con el acumulado. '  # Se incorpora la sensibilidad sin julio y se advierte que el acumulado no prueba una mejora sostenida.
        f'La revisión prioritaria por pérdida absoluta corresponde a {mayor_caida["activo"]}; '  # Se identifica mediante su código el activo con mayor pérdida absoluta de tasa diaria.
        f'la continuidad de {", ".join(top3)} merece atención por su {top3_pct:.2f}% del volumen. '  # Se nombran los tres mayores aportantes y su porcentaje conjunto del volumen observado.
        'Conciliar datos y consultar causas operativas son oportunidades verificables. '  # Se añade la propuesta de conciliar datos y consultar las causas operativas.
        'No se demuestra eficiencia, rentabilidad ni el efecto de una intervención.'  # Se precisan los límites: este análisis no demuestra eficiencia, rentabilidad ni efectos de intervenciones.
    ))  # Se completa y muestra la respuesta principal.
    preguntas = [  # Se crea una lista para reunir las cinco preguntas adicionales con sus evidencias y límites.
        {'numero': 1, 'pregunta': '¿Mejoró la producción al comparar los mismos activos y meses?',  # Se registra la primera pregunta, centrada en comparar los mismos activos y meses.
         'justificacion': f'Basada en los datos: {len(comunes)} activos con {mes_corte} meses válidos por año; {len(actual_comun)} activo-mes actuales y {int(dias_actual)} días.',  # Se justifica la comparación con los activos, meses válidos, registros y días calculados.
         'respuesta': f'La tasa pasa de {diario_anterior_comun:,.2f} a {diario_actual_comun:,.2f} bbl/día ({cambio_comparable_pct:+.2f}%). Sin julio en ambos años: {cambio_sin_julio_pct:+.2f}%.',  # Se responde con las tasas de ambos años, su cambio porcentual y la sensibilidad sin julio.
         'grafica': '6.3: comparación conjunta; 6.6: sensibilidad mensual.',  # Se indican las secciones de las gráficas que apoyan esta primera respuesta.
         'limite': 'n=8 por activo y año; n=7 en la sensibilidad. Mayor tasa no equivale a eficiencia ni a mejora sostenida.'},  # Se explicitan los tamaños de grupo y los límites para interpretar el aumento de la tasa.
        {'numero': 2, 'pregunta': '¿Qué activos conviene revisar por sus descensos?',  # Se registra la segunda pregunta, centrada en priorizar activos con descensos.
         'justificacion': 'Basada en los datos: cada activo comparable tiene un cambio absoluto, un porcentaje y n de ambos períodos.',  # Se justifica usar cambios absolutos, porcentajes y tamaños de ambos períodos.
         'respuesta': f'{mayor_caida["activo"]} tiene la mayor pérdida absoluta: {mayor_caida["cambio_diario"]:+,.2f} bbl/día ({mayor_caida["cambio_pct"]:+.2f}%).',  # Se responde con el activo de mayor caída y sus variaciones absoluta y porcentual.
         'grafica': '6.4: impacto absoluto y porcentual por activo.',  # Se señala la gráfica de impacto por activo que permite comprobar la respuesta.
         'limite': 'La prioridad considera volumen. No se conocen costos, paradas ni causas del descenso.'},  # Se advierte que la prioridad usa volumen y que faltan costos, paradas y causas.
        {'numero': 3, 'pregunta': '¿Dónde se concentra el volumen observado?',  # Se registra la tercera pregunta, centrada en la concentración del volumen observado.
         'justificacion': f'Basada en los datos: {len(actual)} registros del período actual, distribuidos en {actual["activo"].nunique()} activos.',  # Se justifica con el número de registros y de activos del período actual.
         'respuesta': f'{", ".join(top3)} concentran {top3_pct:.2f}% de {crudo_actual:,.2f} barriles observados.',  # Se responde con los tres mayores aportantes, su participación y el volumen total.
         'grafica': '6.5: participación por activo.',  # Se señala la gráfica de participaciones donde se observa la concentración.
         'limite': 'Esta selección incluye 15 activos y difiere de los 14 comparables. Concentración no mide riesgo de falla.'},  # Se aclara que esta selección incluye 15 activos y que concentración no equivale a probabilidad de falla.
        {'numero': 4, 'pregunta': '¿Los cambios del precio acompañan los cambios de producción?',  # Se registra la cuarta pregunta, centrada en la asociación entre cambios de precio y producción.
         'justificacion': f'Basada en los datos: {len(cohorte)} activos constantes y {len(changes)} cambios mensuales pareados; un precio por mes.',  # Se justifica con el tamaño de la cohorte fija y el número de pares mensuales disponibles.
         'respuesta': f'Pearson={pearson_cambios:.3f}; Spearman={spearman_cambios:.3f}. Intervalo exploratorio: [{bootstrap3["ic95"][0]:.3f}, {bootstrap3["ic95"][1]:.3f}].',  # Se responde con Pearson, Spearman y los extremos del intervalo exploratorio calculado.
         'grafica': '4.3: dispersión; 4.4: remuestreo e intervalo.',  # Se indican las secciones de dispersión y remuestreo que apoyan esa respuesta.
         'limite': 'La asociación es débil en estas fuentes. No demuestra independencia, ausencia de rezagos ni causalidad.'},  # Se advierte que una asociación débil no demuestra independencia ni descarta rezagos o causas.
        {'numero': 5, 'pregunta': '¿Qué calidad debe revisarse antes de declarar una mejora real?',  # Se registra la quinta pregunta, centrada en los problemas de calidad pendientes.
         'justificacion': f'Basada en los datos: {len(conflicts)} celdas conflictivas, {audit["huecos_interiores"]} huecos y {audit["filas_sin_catalogo"]} filas sin nombre validado.',  # Se justifica con los conteos calculados de conflictos, huecos y registros sin nombre validado.
         'respuesta': 'Conciliar crudo de LA y gas de AM/AU en agosto 2022; revisar ausencias, AB16 sin catálogo y agosto 2026 sin precio.',  # Se enumeran las medidas y carencias concretas que deben conciliarse con las fuentes.
         'grafica': '5: mapa de calidad y tablas de auditoría.',  # Se señalan el mapa de calidad y las tablas de auditoría como evidencia.
         'limite': 'No rellenar ceros, inventar equivalencias ni eliminar extremos para que el resultado parezca mejor.'},  # Se establece que no deben inventarse datos ni eliminarse extremos para favorecer una conclusión.
    ]  # Se completa la lista de cinco preguntas documentadas.
    for p in preguntas:  # Se recorre cada pregunta con sus campos de justificación, respuesta, gráfica y límite.
        display(Markdown(f"### Pregunta {p['numero']}. {p['pregunta']}\n\n"  # Se inicia su presentación con un título numerado y dos saltos de línea.
                         f"**Justificación:** {p['justificacion']}\n\n**Respuesta:** {p['respuesta']}\n\n"  # Se añaden la justificación y la respuesta, separadas y resaltadas mediante Markdown.
                         f"**Gráfica en este archivo:** {p['grafica']}\n\n**Límite:** {p['limite']}"))  # Se añaden la referencia a la gráfica y el límite, y se muestra la pregunta completa.
    ''', tag='cinco-preguntas')
    md('''### 7.2. Convertir resultados en acciones verificables
    Cada decisión incluye evidencia, acción, responsable, indicador y límite. Los plazos y metas son propuestas de gestión; no son normas técnicas ni resultados estadísticos. El notebook no ejecuta acciones operativas.
    ''')
    code(r'''
    decisiones = [  # Se crea una lista para reunir decisiones respaldadas por los resultados del notebook.
        {'decision': 'Validar el efecto de la base de julio 2025',  # Se registra la decisión de validar la base de comparación de julio de 2025.
         'evidencia': f'Acumulado {cambio_comparable_pct:+.2f}%; sin julio {cambio_sin_julio_pct:+.2f}%; {meses_en_descenso}/8 meses caen.',  # Se documentan como evidencia el cambio acumulado, la sensibilidad sin julio y los meses con descenso.
         'accion': 'Conciliar julio 2025 con medición y bitácoras en 30 días.',  # Se propone conciliar julio de 2025 con mediciones y bitácoras en un plazo de 30 días.
         'responsable': 'Planificación y supervisión de medición.',  # Se asigna la revisión a planificación y supervisión de medición.
         'indicador': 'Cambio con/sin julio y proporción de registros de julio conciliados; meta de revisión: 100%.',  # Se define un indicador de sensibilidad y conciliación con una meta propuesta del 100%.
         'limite': 'El plazo y meta son propuestas; no se conoce la causa de la baja base.'},  # Se aclara que el plazo y la meta son propuestas y que la causa de la baja base no se conoce.
        {'decision': 'Investigar la mayor caída absoluta',  # Se registra la decisión de investigar el activo con mayor caída absoluta.
         'evidencia': f'{mayor_caida["activo"]}: {mayor_caida["cambio_diario"]:+,.2f} bbl/día; n=8 por año.',  # Se documentan su código, la pérdida diaria y el tamaño de grupo de ocho meses por año.
         'accion': 'Revisar disponibilidad, paradas y conciliación de los ocho meses en 30 días.',  # Se propone revisar disponibilidad, paradas y conciliación de los ocho meses en 30 días.
         'responsable': 'Ingeniería de producción del activo.',  # Se asigna esta revisión a ingeniería de producción del activo.
         'indicador': 'Brecha interanual de bbl/día y meses conciliados; meta de revisión: 8 de 8.',  # Se define el seguimiento de la brecha diaria y una meta de conciliar ocho de ocho meses.
         'limite': 'No atribuir a fallas o agotamiento sin información operativa.'},  # Se exige información operativa antes de atribuir el descenso a fallas o agotamiento.
        {'decision': 'Priorizar continuidad de los tres mayores aportantes',  # Se registra la decisión de revisar la continuidad de los tres mayores aportantes.
         'evidencia': f'{", ".join(top3)} concentran {top3_pct:.2f}% del volumen actual; n=8 por activo.',  # Se documentan sus códigos, participación conjunta y ocho meses observados por activo.
         'accion': 'Revisar mensualmente contingencias y disponibilidad antes de reasignar recursos.',  # Se propone revisar contingencias y disponibilidad cada mes antes de reasignar recursos.
         'responsable': 'Coordinación de operaciones y mantenimiento.',  # Se asigna esta acción a operaciones y mantenimiento.
         'indicador': 'Participación y tasa diaria; revisión propuesta si cae más de 5% en períodos equivalentes.',  # Se propone vigilar participación y tasa diaria, revisando caídas superiores al 5% en períodos equivalentes.
         'limite': '5% es un criterio propuesto. No hay datos de costos, seguridad o reservas para recomendar inversiones.'},  # Se aclara que el 5% es una propuesta y que los datos no sustentan recomendaciones de inversión.
        {'decision': 'Resolver brechas antes de certificar resultados',  # Se registra la decisión de resolver las brechas de calidad antes de certificar resultados.
         'evidencia': f'{len(conflicts)} celdas conflictivas y {audit["huecos_interiores"]} huecos interiores.',  # Se documentan los conteos de celdas conflictivas y de huecos interiores.
         'accion': 'Conciliar conflictos, confirmar cobertura y completar catálogo y precio faltantes.',  # Se propone conciliar medidas, confirmar cobertura y completar catálogo y precios.
         'responsable': 'Administrador de datos y supervisor de medición.',  # Se asigna la acción al administrador de datos y al supervisor de medición.
         'indicador': 'Pendientes confirmados: meta 0 antes de certificar; catálogo: meta 100% validado.',  # Se proponen cero pendientes confirmados y un catálogo completamente validado antes de certificar.
         'limite': 'No imputar ceros ni inventar datos para cumplir la meta; diferenciar faltante de error.'},  # Se impide justificar datos inventados o ceros imputados como forma de alcanzar esas metas.
        {'decision': 'Usar precio como contexto, no como única meta productiva',  # Se registra la decisión de utilizar el precio como contexto para interpretar la producción.
         'evidencia': f'r={pearson_cambios:.3f}, n={len(changes)} pares; intervalo incluye cero.',  # Se documentan la correlación, el número de pares y la inclusión de cero en el intervalo.
         'accion': 'Actualizar la comparación al recibir nuevos meses e incorporar variables operativas.',  # Se propone actualizar la comparación e incorporar variables operativas cuando estén disponibles.
         'responsable': 'Analista de planificación y analista comercial.',  # Se asigna el seguimiento a los analistas de planificación y comercial.
         'indicador': 'n de pares y cobertura de la cohorte; no cuantificar con n<12.',  # Se definen como controles el número de pares y la cobertura, evitando cuantificar con menos de 12 pares.
         'limite': 'No es un pronóstico ni un efecto causal; precio por producción no representa ingreso efectivo.'},  # Se aclara que el análisis no es un pronóstico ni permite estimar efectos causales o ingresos efectivos.
    ]  # Se completa la lista de decisiones con evidencia, responsables, indicadores y límites.
    for numero, decision in enumerate(decisiones, 1):  # Se recorre cada decisión con una numeración que empieza en 1.
        display(Markdown(f"### Decisión {numero}. {decision['decision']}\n\n" +  # Se prepara el título numerado de la decisión y se añade espacio antes de sus detalles.
                        '\n\n'.join(f"**{clave.capitalize()}:** {valor}" for clave, valor in decision.items() if clave != 'decision')))  # Se unen y muestran sus otros campos con etiquetas resaltadas, sin repetir el título de la decisión.
    ''')
    md('''## 8. Reproducibilidad, verificaciones y exportación · T8
    ### 8.1. Comprobar que la ejecución conserva las reglas y reproduce la entrega
    Estos controles se ejecutan; no son una lista de comprobación manual. Primero validan reglas (unicidad, trazabilidad y calendario). Después contrastan los resultados esperados para **estas tres copias de fuentes**, cuyas huellas ya se verificaron. Si se cambia deliberadamente el conjunto de datos, también deben revisarse estos resultados de referencia.

    Repetimos el remuestreo con la misma semilla para comprobar que produce el mismo intervalo. Los controles de n pequeño y variable constante verifican que la función no emita resultados engañosos.
    ''')
    code(r'''
    comprobaciones = {  # Se crea un diccionario de controles que deben cumplirse con las tres fuentes incorporadas.
        'Una fila por activo-mes': not df.duplicated(KEY).any(),  # Se comprueba que no existan claves de activo-mes duplicadas en la tabla final.
        'Se conservan todas las claves originales': len(df) == len(d[KEY].drop_duplicates()),  # Se comprueba que estén representadas todas las claves originales distintas.
        'Se trazan todas las filas originales': int(df['n_filas_origen'].sum()) == len(raw),  # Se verifica que la suma de filas de origen corresponda al número de filas originales.
        'Las fuentes mantienen 802 filas y 789 claves': len(raw) == 802 and len(df) == 789,  # Se contrastan las 802 filas originales y las 789 claves consolidadas de estas fuentes.
        'Se mantienen 1 crudo y 2 gases faltantes': df['crudo'].isna().sum() == 1 and df['gas'].isna().sum() == 2,  # Se comprueba que permanezcan un crudo faltante y dos gases faltantes, sin imputarlos.
        'Tres celdas conflictivas': len(conflicts) == 3,  # Se verifica que se conserven los tres conflictos documentados.
        'Se mantienen 18 ceros legítimos de gas': int(df['gas'].eq(0).sum()) == 18,  # Se comprueba que los 18 ceros legítimos de gas sigan presentes.
        '18 huecos internos': audit['huecos_interiores'] == 18,  # Se verifica el resultado auditado de 18 huecos interiores.
        '52 y 42 marcas IQR conservadas': audit['atipicos_crudo'] == 52 and audit['atipicos_gas'] == 42,  # Se contrastan las 52 marcas de crudo y las 42 de gas para la regla IQR.
        'El calendario incluye febrero bisiesto': df.loc[df['fecha'].eq(pd.Timestamp('2024-02-01')), 'dias_mes'].eq(29).all(),  # Se comprueba que febrero de 2024 tenga 29 días en el calendario utilizado.
        'Un precio por mes': not prices['fecha'].duplicated().any(),  # Se verifica que la tabla de precios tenga una sola fila por fecha.
        'Agosto 2026 sigue sin precio': df.loc[df['fecha'].eq(pd.Timestamp('2026-08-01')), 'precio_usd_barril'].isna().all(),  # Se comprueba que agosto de 2026 continúe sin precio, respetando la ausencia en la fuente.
        'Comparación: 14 activos y 112 filas por año': len(comunes) == 14 and len(actual_comun) == len(anterior_comun) == 112,  # Se verifica que la comparación utilice 14 activos y 112 registros activo-mes en cada año.
        'Días sin duplicar por activo': dias_actual == dias_anterior == 243,  # Se comprueba que cada período tenga 243 días contados sin duplicar por activo.
        'Volumen 2026 de referencia': np.isclose(crudo_actual, 88304451.13, rtol=0, atol=.01),  # Se contrasta el volumen actual con el valor auditado, admitiendo hasta 0,01 barriles de diferencia.
        'Tasa de la cohorte de referencia': np.isclose(diario_actual_comun, 352214.8383950617, rtol=0, atol=1e-6),  # Se contrasta la tasa diaria de la cohorte con el valor auditado y una tolerancia absoluta de 0,000001.
        'Sensibilidad sin julio': np.isclose(cambio_sin_julio_pct, -2.259238395228, rtol=0, atol=1e-8),  # Se verifica el cambio porcentual sin julio contra la referencia, con una tolerancia de 0,00000001.
        '54 pares reales, una fila por mes': len(changes) == 54 and changes['fecha'].is_unique,  # Se comprueba que existan 54 pares de cambios y una sola observación por fecha.
        'Correlación de referencia': np.isclose(pearson_cambios, .0165681847985, rtol=0, atol=1e-8),  # Se contrasta la correlación de los cambios con la referencia usando una tolerancia absoluta pequeña.
        'Semilla reproducible': bootstrap3 == correlacion_por_bloques(changes['cambio_crudo_pct'], changes['cambio_precio_pct']),  # Se repite el remuestreo con la misma semilla y se verifica que devuelva exactamente el mismo resultado.
        'Se controla n menor a 12': correlacion_por_bloques(np.arange(5), np.arange(5))['r'] is None,  # Se prueba que la función no entregue una correlación cuando solo hay cinco pares.
        'Se controla variable constante': correlacion_por_bloques(np.ones(12), np.arange(12))['r'] is None,  # Se prueba que tampoco entregue correlación cuando una serie es constante.
        'Se construyeron nueve figuras': len(figuras_creadas) == 9,  # Se comprueba que el notebook haya construido las nueve figuras esperadas.
    }  # Se completa el diccionario de condiciones de validación.
    for nombre, correcto in comprobaciones.items():  # Se recorre cada nombre de control junto con su resultado booleano.
        assert correcto, f'No se cumple: {nombre}'  # Se detiene la ejecución con el nombre del control si alguna condición no se cumple.
    display(pd.DataFrame([{'control': k, 'resultado': 'OK' if v else 'REVISAR'} for k, v in comprobaciones.items()]))  # Se muestran todos los controles con la etiqueta OK si se cumplen, o REVISAR si no se cumplen.
    print(f'{len(comprobaciones)} comprobaciones correctas. El análisis se ejecutó desde las fuentes incorporadas.')  # Se informa el número de comprobaciones correctas y que el análisis partió de las fuentes incorporadas.
    ''', tag='T8-validacion')
    md('''### 8.2. Guardar copias de los resultados para revisión
    Las tablas y figuras ya están visibles en este notebook. Las copias CSV/JSON son salidas opcionales para inspección y reutilización; el notebook no depende de ellas para ejecutarse otra vez. Los números se conservan sin redondear internamente; el formato de exportación CSV usa nueve decimales.
    ''')
    code(r'''
    tablas_exportadas = {  # Se prepara un diccionario que relaciona cada nombre de archivo con la tabla que se exportará.
        'produccion_limpia': df, 'precios_limpios': prices, 'conflictos': conflicts,  # Se incluyen la producción limpia, los precios normalizados y el detalle de conflictos.
        'duplicados': duplicates, 'cobertura': coverage, 'limites_iqr': fences,  # Se incluyen los duplicados, la cobertura y los límites de detección de atípicos.
        'segmentacion': groups, 'serie_mensual': monthly, 'serie_cohorte': balanced,  # Se incluyen la segmentación, la serie mensual completa y la serie de la cohorte histórica.
        'cambios_mensuales': changes, 'comparacion_interanual': comparison,  # Se incluyen los cambios mensuales y la comparación interanual por activo.
        'comparacion_por_mes': comparacion_meses.reset_index(), 'concentracion': concentracion.reset_index(),  # Se incluyen las comparaciones por mes y la concentración, convirtiendo sus índices en columnas.
    }  # Se completa la selección de tablas para exportación.
    for nombre, tabla in tablas_exportadas.items():  # Se recorre cada nombre de salida junto con su tabla de resultados.
        tabla.to_csv(SALIDAS / f'{nombre}.csv', index=False, float_format='%.9f', date_format='%Y-%m-%d', lineterminator='\n')  # Se guarda cada CSV sin índice, con nueve decimales, fechas año-mes-día y saltos de línea estándar.
    resumen = {  # Se inicia un resumen con los principales resultados y parámetros de la entrega.
        'grupo': 'GRUPO 5', 'anio_actual': anio_actual, 'mes_corte': mes_corte,  # Se guardan el nombre GRUPO 5, el año actual y el mes de corte utilizado.
        'filas_limpias': len(df), 'crudo_actual': crudo_actual,  # Se guardan el número de filas limpias y el volumen total actual.
        'crudo_diario_actual': crudo_actual / int(dias_periodo_actual),  # Se calcula y guarda la tasa diaria de todos los activos del período actual.
        'cohorte_historica': cohorte, 'activos_comparables': comunes,  # Se guardan los códigos de la cohorte histórica y de los activos de la comparación interanual.
        'diario_comparable_actual': float(diario_actual_comun),  # Se guarda la tasa diaria actual de los activos comparables como número flotante estándar.
        'diario_comparable_anterior': float(diario_anterior_comun),  # Se guarda la tasa diaria anterior de esos mismos activos.
        'cambio_comparable_pct': float(cambio_comparable_pct),  # Se guarda su variación porcentual entre ambos años.
        'cambio_sin_julio_pct': float(cambio_sin_julio_pct),  # Se guarda la variación de la comparación alternativa que excluye julio.
        'top3': top3, 'top3_pct': top3_pct,  # Se guardan los tres mayores aportantes y su participación conjunta.
        'correlacion_bloque3': bootstrap3, 'correlacion_bloque6': bootstrap6,  # Se guardan los resultados del remuestreo con bloques de tres y seis meses.
        'spearman_cambios': float(spearman_cambios),  # Se guarda el coeficiente de Spearman de los cambios mensuales.
        'validaciones_correctas': len(comprobaciones), 'figuras': figuras_creadas,  # Se guardan la cantidad de controles correctos y los nombres de las figuras creadas.
    }  # Se completa el resumen estructurado del análisis.
    for nombre, objeto in [('resumen', resumen), ('auditoria', audit), ('fuentes', trazabilidad),  # Se inicia el recorrido de las salidas JSON para resumen, auditoría y trazabilidad de fuentes.
                            ('preguntas', preguntas), ('decisiones', decisiones)]:  # Se añaden las preguntas y decisiones a ese mismo recorrido de exportación.
        (SALIDAS / f'{nombre}.json').write_text(json.dumps(objeto, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')  # Se escribe cada objeto como JSON UTF-8 legible, conservando tildes y rechazando NaN no válido en JSON.
    display(pd.DataFrame({'tabla_exportada': list(tablas_exportadas), 'filas': [len(t) for t in tablas_exportadas.values()]}))  # Se muestra una tabla con los nombres exportados y el número de filas de cada tabla.
    print('Copias generadas en salidas_EDA_notebook/. El código, los resultados y las gráficas quedan en este único notebook.')  # Se informa dónde están las copias generadas y que el proceso completo permanece en este notebook.
    ''', tag='T8-exportacion')
    md('''### 8.3. Dónde está cada explicación técnica
    | Punto | Código ejecutado y explicado en este mismo archivo |
    |---|---|
    | T1 · Carga y trazabilidad | 2.1–2.2: Base64, SHA-256, `read_excel`, `read_csv` |
    | T2 · Estructura y tipos | 2.3–2.5 y 2.8: `info`, `describe`, conversiones y validación |
    | T3 · Duplicados y contradicciones | 2.6–2.7: claves, tolerancia, consolidación y conflictos |
    | T4 · Faltantes, ceros y atípicos | 2.7, 2.11–2.12 y 5: NA, IQR y cobertura |
    | T5 · Uniones y variables | 2.8–2.10: relaciones muchos-a-uno, días, tasas y logaritmo |
    | T6 · Resumen y asociación | 3–4: estadísticas, series, correlaciones y gráficas |
    | T7 · Segmentación y n | 6: grupos, períodos equivalentes, concentración y sensibilidad |
    | T8 · Reproducibilidad | 0, 4.4 y 8: versiones, semilla, controles y exportación |

    **Cómo explicar el flujo:** «Primero importé herramientas y recuperé los tres archivos incorporados. Los abrí con pandas, inspeccioné columnas y tipos, consolidé duplicados y separé contradicciones. Después uní catálogo y precios, calculé tasas diarias, marqué atípicos y revisé cobertura. Con la tabla depurada construí estadísticas y gráficos, comparé cohortes y períodos equivalentes, comprobé la sensibilidad a julio y propuse decisiones. Finalmente ejecuté los controles de integridad y guardé las salidas».

    ## Fuentes y alcance
    Se utilizan exclusivamente las tres copias aportadas: `eppec_prd_petroleo_acumulada_2026 (2).xlsx`, `precio-petrleo-crudo-ecu (1).csv` y `activos_nomenclatura.csv`. Sus nombres y huellas están en la sección 2.2. La carpeta de clase se tomó como referencia metodológica del EDA, no como fuente adicional de observaciones.

    Referencias documentales del proyecto: [producción mensual, Datos Abiertos Ecuador](https://www.datosabiertos.gob.ec/dataset/produccion-mensual-petroecuador) y [Banco Central del Ecuador](https://contenido.bce.fin.ec/). Estas referencias no se descargan al ejecutar. No se certificó identidad byte a byte con recursos oficiales ni se cotejó cada precio con la publicación. Las unidades adoptadas y límites se explican en 2.1 y en el diccionario.

    ## Declaración de uso de inteligencia artificial
    Para realizar este trabajo se utilizó inteligencia artificial (Codex/OpenAI) como apoyo en la programación, análisis, elaboración de gráficas y redacción de explicaciones. No se generaron registros ficticios de producción ni se inventaron ubicaciones o causas operativas. **GRUPO 5** debe revisar la interpretación y asume la responsabilidad académica de la entrega.
    ''')
    for index, cell in enumerate(cells):
        cell['id'] = uuid.uuid5(uuid.NAMESPACE_URL, f'grupo5/notebook-autonomo/{index}/{cell.source}').hex[:12]
    nb = nbf.v4.new_notebook(cells=cells, metadata={
        'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'},
        'language_info': {'name': 'python', 'version': '3.12'},
        'grupo5': {'autonomo': True, 'fuentes_incorporadas': len(embedded), 'sin_modulos_del_proyecto': True, 'codigo_comentado_linea_por_linea': True},
    })
    path = root/'notebooks/01_EDA_petroleo.ipynb'
    path.parent.mkdir(parents=True, exist_ok=True)
    if execute:
        # Ejecutar en una carpeta vacía demuestra que no lee src, reportes ni datos externos.
        with tempfile.TemporaryDirectory(prefix='grupo5_notebook_') as sandbox:
            client = NotebookClient(nb, timeout=240, kernel_name='python3', resources={'metadata': {'path': sandbox}})
            client.km = KernelManager(kernel_name='python3')
            client.km.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
            client.execute()
            generated = Path(sandbox)/'salidas_EDA_notebook'
            result = json.loads((generated/'resumen.json').read_text(encoding='utf-8'))
            nb.metadata['grupo5']['ejecutado_en_carpeta_vacia'] = True
            nb.metadata['grupo5']['comprobaciones_correctas'] = result['validaciones_correctas']
            nb.metadata['grupo5']['figuras_generadas'] = len(result['figuras'])
    nbf.validate(nb)
    nbf.write(nb, path)
    return path


if __name__ == '__main__':
    print(build())
