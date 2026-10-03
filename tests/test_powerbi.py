"""Controles de integridad del paquete nativo de Power BI, sin requerir Desktop."""
import base64, io, json, re, unittest
from pathlib import Path
import pandas as pd
from src.export_powerbi import ROOT, MEASURES, get_tables

class PowerBITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = get_tables()
        cls.folder = ROOT / 'powerbi'
        cls.model = json.loads((cls.folder/'Petroleo_EDA.SemanticModel/model.bim').read_text(encoding='utf-8'))['model']

    def test_relations_unique_keys_and_referential_integrity(self):
        for rel in self.model['relationships']:
            fact = self.tables[rel['fromTable']][rel['fromColumn']]
            dim = self.tables[rel['toTable']][rel['toColumn']]
            self.assertFalse(dim.isna().any())
            self.assertTrue(dim.is_unique)
            self.assertTrue(set(fact) <= set(dim))
            self.assertEqual(rel['crossFilteringBehavior'], 'oneDirection')
        self.assertFalse(self.tables['Produccion'].duplicated(['Mes','Activo']).any())

    def test_embedded_queries_match_csv_and_cleaned_inputs(self):
        for table in self.model['tables']:
            m = '\n'.join(table['partitions'][0]['source']['expression'])
            payload = re.search(r'Binary.FromText\("([A-Za-z0-9+/=]+)"', m).group(1)
            embedded = pd.read_csv(io.StringIO(base64.b64decode(payload).decode('utf-8')))
            expected = pd.read_csv(self.folder/'datos'/f"{table['name']}.csv")
            pd.testing.assert_frame_equal(embedded, expected)
            pd.testing.assert_frame_equal(embedded, self.tables[table['name']], check_dtype=False, rtol=1e-8, atol=1e-8)
            self.assertNotIn('File.Contents', m)
            self.assertNotIn('Web.Contents', m)

    def test_conflicts_and_quality_survive_export(self):
        d = self.tables['Produccion']
        self.assertEqual(d.Crudo_bbl.isna().sum(),1)
        self.assertEqual(d.Gas_miles_pies3.isna().sum(),2)
        self.assertEqual(d.Conflicto_crudo.sum()+d.Conflicto_gas.sum(),3)
        self.assertEqual((d.Gas_miles_pies3 == 0).sum(),18)
        self.assertEqual(d.Atipico_crudo.sum(),52)
        cov=self.tables['Cobertura']
        self.assertEqual((cov.Estado=='sin registro interior').sum(),18)
        expr=next(e for n,e,*_ in MEASURES if n=='Huecos internos')
        self.assertIn('"sin registro interior"',expr)

    def test_2026_kpis_and_calendar_denominator(self):
        d = self.tables['Produccion'].loc[lambda x:x.Mes.str.startswith('2026')]
        days=self.tables['Calendario'].loc[lambda x:(x.Anio==2026)&(x.Con_produccion==1),'Dias_mes'].sum()
        self.assertEqual(len(d),120)
        self.assertEqual(days,243)
        self.assertAlmostEqual(d.Crudo_bbl.sum(),88304451.13,places=2)
        self.assertAlmostEqual(d.Crudo_bbl.sum()/days,363392.803004115,places=6)
        price=self.tables['Precios'].loc[lambda x:x.Mes.str.startswith('2026')]
        self.assertEqual(len(price),7)
        self.assertAlmostEqual(price.Precio_USD_bbl.mean(),75.897142857,places=7)
        self.assertFalse((price.Mes=='2026-08-01').any())
        self.assertNotIn('Precio_USD_bbl',d.columns)
        self.assertEqual(next(e for n,e,*_ in MEASURES if n=='Precio promedio (USD/bbl)'), 'AVERAGE(Precios[Precio_USD_bbl])')

    def test_report_fields_exist_and_visuals_fit_pages(self):
        names={t['name']:{'Column':{c['name'] for c in t['columns']},'Measure':{m['name'] for m in t.get('measures',[])}} for t in self.model['tables']}
        def check(obj):
            if isinstance(obj,dict):
                for kind in ('Column','Measure'):
                    if kind in obj and isinstance(obj[kind],dict):
                        value=obj[kind]; table=value.get('Expression',{}).get('SourceRef',{}).get('Entity')
                        if table:self.assertIn(value['Property'],names[table][kind])
                for v in obj.values():check(v)
            elif isinstance(obj,list):
                for v in obj:check(v)
        pages=self.folder/'Petroleo_EDA.Report/definition/pages'
        count=0
        for p in pages.glob('*/page.json'):
            page=json.loads(p.read_text(encoding='utf-8'))
            for path in p.parent.glob('visuals/*/visual.json'):
                v=json.loads(path.read_text(encoding='utf-8'));check(v);pos=v['position'];count+=1
                self.assertGreaterEqual(pos['x'],0);self.assertGreaterEqual(pos['y'],0)
                self.assertLessEqual(pos['x']+pos['width'],page['width'])
                self.assertLessEqual(pos['y']+pos['height'],page['height'])
        self.assertEqual(count,28)

if __name__=='__main__':unittest.main()
