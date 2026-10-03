"""Integridad de comparaciones, denominadores y modelo de decisiones."""
import base64
import io
import json
import re
import unittest
import pandas as pd
from src.export_powerbi_decisiones import ROOT, OUT, REPORT, MODEL, get_tables


class DecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables=get_tables()
        cls.model=json.loads((OUT/MODEL/'model.bim').read_text(encoding='utf-8'))['model']

    def test_comparison_has_same_assets_months_and_days(self):
        comp=self.tables['Comparacion']; s=self.tables['SerieComparable']
        self.assertEqual(len(comp),14)
        self.assertTrue(comp.Activo.is_unique)
        self.assertTrue((comp[['N_2026','N_2025']]==8).all().all())
        self.assertEqual(set(s.Activo),set(comp.Activo))
        self.assertFalse(s.duplicated(['Activo','Mes_numero']).any())
        self.assertFalse(s[['Crudo_2025','Crudo_2026']].isna().any().any())
        for a,g in s.groupby('Activo'):
            self.assertEqual(set(g.Mes_numero),set(range(1,9)))
            self.assertEqual(g.Dias_mes.sum(),243)
            c=comp.set_index('Activo').loc[a]
            self.assertAlmostEqual(g.Crudo_2026.sum()/243,c.Bpd_2026,places=6)
            self.assertAlmostEqual(g.Crudo_2025.sum()/243,c.Bpd_2025,places=6)
        self.assertAlmostEqual(comp.Bpd_2026.sum()/comp.Bpd_2025.sum()-1,.075347193699,places=9)

    def test_july_sensitivity_keeps_all_source_observations(self):
        s=self.tables['SerieComparable']
        self.assertEqual(len(s),112)
        monthly=s.groupby('Mes_numero')[['Crudo_2025','Crudo_2026']].sum()
        self.assertEqual((monthly.Crudo_2026<monthly.Crudo_2025).sum(),7)
        without=s[s.Mes_numero.ne(7)]
        self.assertEqual(len(without),98)
        self.assertAlmostEqual(without.Crudo_2026.sum()/without.Crudo_2025.sum()-1,-.02259238395228,places=9)
        self.assertEqual(without.groupby('Activo').Dias_mes.sum().unique().tolist(),[212])

    def test_pairs_are_months_not_repeated_assets(self):
        d=self.tables['Cambios']
        self.assertEqual(len(d),54)
        self.assertTrue(d.Mes.is_unique)
        self.assertAlmostEqual(d.Cambio_crudo.corr(d.Cambio_precio),.0165681848,places=8)
        self.assertEqual(len(d[d.Mes.str.startswith('2026')]),7)

    def test_embedded_export_roundtrip_and_relations(self):
        for table in self.model['tables']:
            text='\n'.join(table['partitions'][0]['source']['expression'])
            payload=re.search(r'Binary.FromText\("([A-Za-z0-9+/=]+)"',text).group(1)
            actual=pd.read_csv(io.StringIO(base64.b64decode(payload).decode('utf-8')))
            pd.testing.assert_frame_equal(actual,self.tables[table['name']],check_dtype=False,atol=1e-8,rtol=1e-8)
        self.assertEqual(len(self.model['relationships']),9)
        for r in self.model['relationships']:
            dim=self.tables[r['toTable']][r['toColumn']]
            fact=self.tables[r['fromTable']][r['fromColumn']]
            self.assertTrue(dim.is_unique)
            self.assertTrue(set(fact)<=set(dim))
            self.assertEqual(r['crossFilteringBehavior'],'oneDirection')

    def test_visual_bindings_and_interactive_page_scopes(self):
        fields={t['name']:{'Column':{c['name'] for c in t['columns']},'Measure':{m['name'] for m in t.get('measures',[])}} for t in self.model['tables']}
        def check(obj):
            if isinstance(obj,dict):
                for kind in ('Column','Measure'):
                    if kind in obj:
                        ref=obj[kind]; table=ref.get('Expression',{}).get('SourceRef',{}).get('Entity')
                        if table:self.assertIn(ref['Property'],fields[table][kind])
                for x in obj.values():check(x)
            elif isinstance(obj,list):
                for x in obj:check(x)
        page_root=OUT/REPORT/'definition/pages'
        for p in page_root.glob('*/page.json'):
            page=json.loads(p.read_text(encoding='utf-8'))
            slicer_tables=[]
            for f in p.parent.glob('visuals/*/visual.json'):
                v=json.loads(f.read_text(encoding='utf-8'));check(v)
                q=v['position']
                self.assertLessEqual(q['x']+q['width'],page['width'])
                self.assertLessEqual(q['y']+q['height'],page['height'])
                if v['visual']['visualType']=='slicer':
                    proj=v['visual']['query']['queryState']['Values']['projections'][0]
                    slicer_tables.append(proj['field']['Column']['Expression']['SourceRef']['Entity'])
            if p.parent.name in ['Decidir','Priorizar','Proteger']:self.assertEqual(slicer_tables,['Activos'])
            if p.parent.name=='Tendencia':self.assertEqual(set(slicer_tables),{'Calendario'})


if __name__=='__main__':unittest.main()
