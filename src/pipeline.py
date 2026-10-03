"""T1-T7: carga, auditoría, limpieza conservadora y análisis descriptivo."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SEED = 2026
KEY = ['anio', 'mes', 'activo']
SMALL_N = 12  # Una vuelta anual; es una regla descriptiva, no un umbral estadístico universal.


def load_sources(root=ROOT):
    raw = root/'data/crudos'
    for item in json.loads((raw/'manifest.json').read_text(encoding='utf-8')):
        if hashlib.sha256((raw/item['archivo']).read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('La fuente cambió: '+item['archivo'])
    production = pd.read_excel(raw/'produccion_original.xlsx', sheet_name='Hoja1')
    prices = pd.read_csv(raw/'precios_original.csv')
    catalog = pd.read_csv(raw/'activos_original.csv')
    return production, prices, catalog


def clean_sources(production, prices, catalog):
    """No modifica entradas. No resuelve contradicciones seleccionando primera/última fila."""
    empty_cols = production.columns[production.isna().all()].tolist()
    d = production.drop(columns=empty_cols).rename(columns={
        'AÑO':'anio','MES':'mes','ACTIVO':'activo','CRUDO':'crudo','GAS':'gas'}).copy()
    if set(d.columns) != set(KEY+['crudo','gas']):
        raise ValueError('Esquema de producción inesperado')
    d['fila_excel'] = np.arange(2, len(d)+2)
    for col in ['anio','mes','crudo','gas']:
        d[col] = pd.to_numeric(d[col], errors='raise')
    if d[KEY].isna().any().any() or not d.mes.between(1,12).all():
        raise ValueError('Clave o mes inválido')
    if not (d[['anio','mes']] % 1 == 0).all().all():
        raise ValueError('Año/mes no entero')
    d[['anio','mes']]=d[['anio','mes']].astype('int64')
    d['activo'] = d.activo.astype('string').str.strip().str.upper()
    if (d[['crudo','gas']] < 0).any().any():
        raise ValueError('Volúmenes negativos: requiere revisión')
    exact = d.duplicated(KEY+['crudo','gas'])
    duplicate_detail = d[d.duplicated(KEY,keep=False)].sort_values(KEY+['fila_excel'])
    # La unicidad se define por activo-mes, conservando el número de fila de cada origen.
    unique = d.loc[~exact].copy()
    rows, conflicts = [], []
    for key,g in unique.groupby(KEY,sort=True,dropna=False):
        record = dict(zip(KEY,key))
        original_rows = d.loc[(d[KEY] == pd.Series(record)).all(axis=1),'fila_excel']
        record['filas_origen'] = '|'.join(map(str,original_rows))
        record['n_filas_origen'] = len(original_rows)
        for col in ['crudo','gas']:
            values = g[col].dropna().to_numpy(dtype=float)
            # 1e-6 unidades absorbe diferencias binarias de Excel, no la discrepancia de 0,01.
            equivalent = len(values)>0 and np.allclose(values,values[0],atol=1e-6,rtol=0)
            record[col] = float(np.mean(values)) if equivalent else np.nan
            record['conflicto_'+col] = bool(len(values)>1 and not equivalent)
            if record['conflicto_'+col]:
                conflicts.append({**dict(zip(KEY,key)),'variable':col,
                                  'valores':' | '.join(format(v,'.12g') for v in values),
                                  'filas_origen':record['filas_origen'],'tratamiento':'NA; pendiente de validar con fuente'})
        rows.append(record)
    clean = pd.DataFrame(rows)
    clean['fecha'] = pd.to_datetime(dict(year=clean.anio,month=clean.mes,day=1))
    p = prices.rename(columns={prices.columns[0]:'fecha',prices.columns[1]:'precio_usd_barril'}).copy()
    p['fecha'] = pd.to_datetime(p.fecha, errors='raise')
    p['precio_usd_barril'] = pd.to_numeric(p.precio_usd_barril,errors='raise')
    if p.fecha.duplicated().any() or (p.precio_usd_barril<=0).any():
        raise ValueError('Precio duplicado o no positivo')
    c = catalog.rename(columns={'Activo':'nombre_activo','Nomenclatura':'activo'}).copy()
    c['activo'] = c.activo.astype('string').str.strip().str.upper()
    if c.activo.duplicated().any():
        raise ValueError('Catálogo no es muchos-a-uno')
    clean = clean.merge(c,on='activo',how='left',validate='many_to_one')
    clean['catalogo_faltante'] = clean.nombre_activo.isna()
    clean['nombre_activo'] = clean.nombre_activo.fillna(clean.activo+' (sin catálogo)')
    clean = clean.merge(p,on='fecha',how='left',validate='many_to_one')
    clean['dias_mes'] = clean.fecha.dt.days_in_month
    clean['crudo_diario'] = clean.crudo / clean.dias_mes
    clean['gas_diario'] = clean.gas / clean.dias_mes
    clean['log1p_crudo'] = np.log1p(clean.crudo)
    clean['trimestre'] = clean.fecha.dt.quarter
    # IQR dentro de cada activo: no penaliza estructuralmente a productores grandes.
    fences=[]
    for asset,g in clean.groupby('activo',observed=True):
        for var in ['crudo_diario','gas_diario']:
            q1,q3=g[var].quantile([.25,.75]); iqr=q3-q1
            lo,hi=q1-1.5*iqr,q3+1.5*iqr
            flag=(g[var]<lo)|(g[var]>hi)
            clean.loc[g.index,'atipico_'+var] = flag
            fences.append({'activo':asset,'variable':var,'n':int(g[var].count()),
                           'q1':q1,'q3':q3,'limite_inferior':lo,'limite_superior':hi,'n_atipicos':int(flag.sum())})
    for col in ['atipico_crudo_diario','atipico_gas_diario']:
        clean[col]=clean[col].astype(bool)
    clean = clean.sort_values(['fecha','activo']).reset_index(drop=True)
    calendar=pd.date_range(clean.fecha.min(),clean.fecha.max(),freq='MS')
    gaps=[]
    for asset,g in clean.groupby('activo',observed=True):
        for dt in calendar:
            exists=dt in set(g.fecha)
            state='observado' if exists else ('sin registro interior' if g.fecha.min()<dt<g.fecha.max() else 'fuera de cobertura observada')
            row=g[g.fecha.eq(dt)]
            gaps.append({'fecha':dt,'activo':asset,'estado':state,
                         'crudo_valido':bool(len(row) and row.crudo.notna().all()),
                         'gas_valido':bool(len(row) and row.gas.notna().all())})
    coverage=pd.DataFrame(gaps)
    audit={
        'filas_produccion_original':len(d),'columnas_vacias_eliminadas':len(empty_cols),
        'duplicados_exactos_extra':int(exact.sum()),'claves_repetidas':int(d.loc[d.duplicated(KEY,keep=False),KEY].drop_duplicates().shape[0]),
        'filas_redundantes_total':len(d)-len(clean),'filas_limpias':len(clean),
        'celdas_conflictivas':len(conflicts),'claves_conflictivas':int(clean[['conflicto_crudo','conflicto_gas']].any(axis=1).sum()),
        'faltantes_crudo':int(clean.crudo.isna().sum()),'faltantes_gas':int(clean.gas.isna().sum()),
        'filas_sin_precio':int(clean.precio_usd_barril.isna().sum()),
        'meses_sin_precio':clean.loc[clean.precio_usd_barril.isna(),'fecha'].dt.strftime('%Y-%m').unique().tolist(),
        'codigos_sin_catalogo':clean.loc[clean.catalogo_faltante,'activo'].unique().tolist(),
        'filas_sin_catalogo':int(clean.catalogo_faltante.sum()),
        'huecos_interiores':int(coverage.estado.eq('sin registro interior').sum()),
        'ceros_gas_conservados':int(clean.gas.eq(0).sum()),
        'atipicos_crudo_diario':int(clean.atipico_crudo_diario.sum()),
        'atipicos_gas_diario':int(clean.atipico_gas_diario.sum()),
        'n_meses':len(calendar),'n_activos':clean.activo.nunique(),'n_precios':len(p),
        'precio_inicio':str(p.fecha.min().date()),'precio_fin':str(p.fecha.max().date()),
        'produccion_inicio':str(clean.fecha.min().date()),'produccion_fin':str(clean.fecha.max().date()),
        'semilla':SEED,'n_minimo_descriptivo':SMALL_N,
    }
    return clean,p,audit,pd.DataFrame(conflicts),duplicate_detail,coverage,pd.DataFrame(fences)


def monthly_series(df):
    """Precio se toma una vez por mes; suma observada y cobertura son explícitas."""
    return df.groupby('fecha').agg(crudo=('crudo',lambda s:s.sum(min_count=1)),
        gas=('gas',lambda s:s.sum(min_count=1)),n_activos=('activo','nunique'),
        n_crudo=('crudo','count'),n_gas=('gas','count'),dias_mes=('dias_mes','first'),
        precio_usd_barril=('precio_usd_barril','first')).assign(
            crudo_diario=lambda d:d.crudo/d.dias_mes,gas_diario=lambda d:d.gas/d.dias_mes).reset_index()


def block_bootstrap_correlation(x,y,seed=SEED,reps=2000,block=3):
    """IC percentil exploratorio por bloques móviles circulares de pares temporales."""
    x,y=np.asarray(x),np.asarray(y)
    if len(x)<12 or np.std(x)==0 or np.std(y)==0:
        return {'n':len(x),'r':None,'ic95':None,'bloque':block,'replicas':reps,'semilla':seed}
    rng=np.random.default_rng(seed); n=len(x); rs=[]
    for _ in range(reps):
        starts=rng.integers(0,n,size=int(np.ceil(n/block)))
        idx=((starts[:,None]+np.arange(block))%n).ravel()[:n]
        if np.std(x[idx])>0 and np.std(y[idx])>0: rs.append(np.corrcoef(x[idx],y[idx])[0,1])
    return {'n':n,'r':float(np.corrcoef(x,y)[0,1]),'ic95':np.quantile(rs,[.025,.975]).tolist(),
            'bloque':block,'replicas':reps,'semilla':seed}


def analyze(clean,prices):
    segments=clean.groupby(['activo','nombre_activo','anio'],observed=True).agg(
        n_registros=('fecha','size'),n_crudo=('crudo','count'),n_gas=('gas','count'),
        n_precio=('precio_usd_barril','count'),crudo_total=('crudo',lambda s:s.sum(min_count=1)),
        media_crudo_diario=('crudo_diario','mean'),mediana_crudo_diario=('crudo_diario','median'),
        gas_total=('gas',lambda s:s.sum(min_count=1))).reset_index()
    segments['grupo_pequeno']=segments.n_crudo<SMALL_N
    monthly=monthly_series(clean)
    full_n=clean.fecha.nunique()
    counts=clean.groupby('activo').crudo.count()
    cohort=sorted(counts[counts==full_n].index)
    balanced=monthly_series(clean[clean.activo.isin(cohort)])
    paired=balanced.dropna(subset=['crudo_diario','precio_usd_barril']).copy()
    paired['cambio_crudo_pct']=paired.crudo_diario.pct_change(fill_method=None)*100
    paired['cambio_precio_pct']=paired.precio_usd_barril.pct_change(fill_method=None)*100
    changes=paired.dropna(subset=['cambio_crudo_pct','cambio_precio_pct'])
    bootstrap=block_bootstrap_correlation(changes.cambio_crudo_pct,changes.cambio_precio_pct)
    bootstrap['sensibilidad_bloque_6']=block_bootstrap_correlation(changes.cambio_crudo_pct,changes.cambio_precio_pct,block=6)
    bootstrap['spearman']=float(changes[['cambio_crudo_pct','cambio_precio_pct']].corr(method='spearman').iloc[0,1])
    bootstrap['cohorte']=cohort
    bootstrap['r_niveles']=float(paired[['crudo_diario','precio_usd_barril']].corr().iloc[0,1])
    last_year=int(clean.anio.max()); last_month=int(clean.loc[clean.anio.eq(last_year),'mes'].max())
    a=clean[clean.anio.eq(last_year)&clean.mes.le(last_month)]
    b=clean[clean.anio.eq(last_year-1)&clean.mes.le(last_month)]
    # Misma cantidad de meses válidos por activo en ambos años.
    ca=a.groupby('activo').crudo.count(); cb=b.groupby('activo').crudo.count()
    common=sorted(set(ca[ca.eq(last_month)].index)&set(cb[cb.eq(last_month)].index))
    comp=[]
    for asset in common:
        ga=a[a.activo.eq(asset)]; gb=b[b.activo.eq(asset)]
        va=float(ga.crudo.sum()/ga.dias_mes.sum()); vb=float(gb.crudo.sum()/gb.dias_mes.sum())
        comp.append({'activo':asset,'n_actual':len(ga),'n_anterior':len(gb),
                     'diario_actual':va,'diario_anterior':vb,'cambio_pct':100*(va/vb-1),
                     'cambio_diario':va-vb})
    comparison=pd.DataFrame(comp).sort_values('cambio_diario')
    weights=a.groupby('activo').crudo.sum().sort_values(ascending=False)
    days_a=a[['fecha','dias_mes']].drop_duplicates().dias_mes.sum()
    days_b=b[['fecha','dias_mes']].drop_duplicates().dias_mes.sum()
    common_a=a[a.activo.isin(common)].crudo.sum()/days_a
    common_b=b[b.activo.isin(common)].crudo.sum()/days_b
    summary={'anio_actual':last_year,'mes_corte':last_month,'n_actual':len(a),
             'crudo_actual':float(a.crudo.sum()),'dias_actual':int(days_a),
             'crudo_diario_actual':float(a.crudo.sum()/days_a),
             'gas_actual':float(a.gas.sum()),'n_activos_actual':int(a.activo.nunique()),
             'precio_medio_actual':float(a[['fecha','precio_usd_barril']].drop_duplicates().precio_usd_barril.mean()),
             'n_meses_precio_actual':int(a.loc[a.precio_usd_barril.notna(),'fecha'].nunique()),
             'top3':weights.head(3).index.tolist(),'top3_pct':float(100*weights.head(3).sum()/weights.sum()),
             'activos_comparables':common,'cambio_comparable_pct':float(100*(common_a/common_b-1)),
             'diario_comparable_actual':float(common_a),'diario_comparable_anterior':float(common_b),
             'mayor_caida':comparison.iloc[0].to_dict(),'correlacion':bootstrap,
             'crudo_media':float(clean.crudo.mean()),'crudo_mediana':float(clean.crudo.median()),
             'crudo_std':float(clean.crudo.std()),'crudo_asimetria':float(clean.crudo.skew()),
             'n_crudo':int(clean.crudo.count()),'n_gas':int(clean.gas.count())}
    return summary,segments,monthly,balanced,changes,comparison


def write_json(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def run(root=ROOT):
    for folder in ['data/procesados','reportes','reportes/figuras','dashboard']:
        (root/folder).mkdir(parents=True,exist_ok=True)
    sources=load_sources(root)
    clean,prices,audit,conflicts,duplicates,coverage,fences=clean_sources(*sources)
    summary,segments,monthly,balanced,changes,comparison=analyze(clean,prices)
    tables={'data/procesados/produccion_limpia.csv':clean,'data/procesados/precios_limpios.csv':prices,
            'reportes/conflictos.csv':conflicts,'reportes/duplicados.csv':duplicates,
            'reportes/cobertura.csv':coverage,'reportes/limites_iqr.csv':fences,
            'reportes/segmentacion.csv':segments,'reportes/serie_mensual.csv':monthly,
            'reportes/serie_cohorte.csv':balanced,'reportes/cambios_mensuales.csv':changes,
            'reportes/comparacion_interanual.csv':comparison}
    for filename,table in tables.items(): table.to_csv(root/filename,index=False,float_format='%.9f',date_format='%Y-%m-%d')
    write_json(root/'reportes/auditoria.json',audit)
    write_json(root/'reportes/resumen.json',summary)
    return clean,prices,audit,summary


if __name__=='__main__':
    _,_,audit,summary=run()
    print(json.dumps({'auditoria':audit,'resumen':summary},ensure_ascii=False,indent=2))
