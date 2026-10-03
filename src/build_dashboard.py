"""Compila el dashboard estático desde el mismo CSV analizado por Python."""
from pathlib import Path
import json
import shutil
import pandas as pd
from plotly.offline import get_plotlyjs
from .pipeline import ROOT
from .content import decisions

def build(root=ROOT):
    clean=pd.read_csv(root/'data/procesados/produccion_limpia.csv')
    prices=pd.read_csv(root/'data/procesados/precios_limpios.csv')
    audit=json.loads((root/'reportes/auditoria.json').read_text(encoding='utf-8'))
    summary=json.loads((root/'reportes/resumen.json').read_text(encoding='utf-8'))
    payload={'rows':json.loads(clean.to_json(orient='records',double_precision=9)),
             'prices':json.loads(prices.to_json(orient='records')),
             'audit':audit,'summary':summary,'decisions':decisions(summary,audit)}
    target=root/'dashboard';target.mkdir(exist_ok=True)
    source=(root/'src/dashboard.html').read_text(encoding='utf-8')
    source=source.replace('__PAYLOAD__',json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('</','<\\/'))
    (target/'index.html').write_text(source,encoding='utf-8')
    (target/'plotly.min.js').write_text(get_plotlyjs(),encoding='utf-8')
    shutil.copy2(root/'src/dashboard.js',target/'dashboard.js')
    (target/'.nojekyll').write_text('',encoding='utf-8')
    return target

if __name__=='__main__': print(build())
