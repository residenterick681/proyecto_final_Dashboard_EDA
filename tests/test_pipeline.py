import unittest
import numpy as np
import pandas as pd
from src.pipeline import load_sources,clean_sources,analyze,block_bootstrap_correlation

class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw,cls.p,cls.c=load_sources()
        cls.result=clean_sources(cls.raw,cls.p,cls.c)
        cls.d,cls.prices,cls.audit,*_=cls.result

    def test_source_not_modified(self):
        before=self.raw.copy(deep=True);clean_sources(self.raw,self.p,self.c)
        pd.testing.assert_frame_equal(before,self.raw)

    def test_unique_key_and_row_conservation(self):
        self.assertFalse(self.d.duplicated(['anio','mes','activo']).any())
        self.assertEqual(len(self.d),len(self.raw[['AÑO','MES','ACTIVO']].drop_duplicates()))
        self.assertEqual(self.d.n_filas_origen.sum(),len(self.raw))

    def test_conflict_is_measure_specific(self):
        row=self.d.query('anio==2022 and mes==8 and activo=="AM"').iloc[0]
        self.assertTrue(pd.isna(row.gas));self.assertAlmostEqual(row.crudo,1253.7)
        row=self.d.query('anio==2022 and mes==8 and activo=="LA"').iloc[0]
        self.assertTrue(pd.isna(row.crudo));self.assertAlmostEqual(row.gas,176770.656)

    def test_precision_tolerance_preserves_itt(self):
        row=self.d.query('anio==2022 and mes==8 and activo=="ITT"').iloc[0]
        self.assertTrue(np.isfinite(row.gas));self.assertFalse(row.conflicto_gas)

    def test_conflicts_do_not_depend_on_file_order(self):
        other=clean_sources(self.raw.sample(frac=1,random_state=2026),self.p,self.c)[0]
        pd.testing.assert_frame_equal(self.d[['fecha','activo','crudo','gas']],other[['fecha','activo','crudo','gas']])

    def test_price_gap_retains_production(self):
        d=self.d.query('anio==2026 and mes==8')
        self.assertEqual(len(d),15);self.assertTrue(d.precio_usd_barril.isna().all());self.assertTrue(d.crudo.notna().all())

    def test_unknown_catalog_and_zero_preservation(self):
        d=self.d[self.d.activo.eq('AB16')]
        self.assertTrue(d.catalogo_faltante.all());self.assertEqual(len(d),36)
        self.assertEqual(int(self.d.gas.eq(0).sum()),18)

    def test_no_fake_independent_price_pairs(self):
        s,_,_,b,ch,co=analyze(self.d,self.prices)
        self.assertEqual(len(b),56);self.assertEqual(len(ch),54)
        self.assertEqual(len(s['correlacion']['cohorte']),11)
        self.assertTrue(co.n_actual.eq(8).all());self.assertTrue(co.n_anterior.eq(8).all())

    def test_duplicate_catalog_is_rejected(self):
        with self.assertRaises(ValueError):clean_sources(self.raw,self.p,pd.concat([self.c,self.c.iloc[[0]]]))

    def test_duplicate_price_is_rejected(self):
        with self.assertRaises(ValueError):clean_sources(self.raw,pd.concat([self.p,self.p.iloc[[0]]]),self.c)

    def test_leap_year_and_calendar_denominator(self):
        d=self.d.query('anio==2024 and mes==2');self.assertTrue(d.dias_mes.eq(29).all())
        s,*_=analyze(self.d,self.prices)
        expected=self.d.query('anio==2026').crudo.sum()/243
        self.assertAlmostEqual(s['crudo_diario_actual'],expected)

    def test_bootstrap_seed_and_insufficient_sample(self):
        x=np.arange(30);y=np.sin(x)+x/10
        self.assertEqual(block_bootstrap_correlation(x,y,reps=100),block_bootstrap_correlation(x,y,reps=100))
        self.assertIsNone(block_bootstrap_correlation(x[:5],y[:5])['r'])

if __name__=='__main__':unittest.main()
