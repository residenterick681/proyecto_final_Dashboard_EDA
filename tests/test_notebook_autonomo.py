"""Verifica ejecución aislada y equivalencia del notebook con las fuentes auditadas."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import nbformat
import pandas as pd
from nbclient import NotebookClient
from jupyter_client import KernelManager
from IPython.core.inputtransformer2 import TransformerManager
from src.pipeline import ROOT, load_sources, clean_sources, analyze


class NotebookAutonomoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nb = nbformat.read(ROOT/'notebooks/01_EDA_petroleo.ipynb', as_version=4)
        cls.codes = [c for c in cls.nb.cells if c.cell_type == 'code']

    def test_no_project_code_imports_or_precomputed_images(self):
        allowed = {'pathlib','importlib','base64','hashlib','json','sys','numpy','pandas','matplotlib','IPython'}
        for c in self.codes:
            tree = ast.parse(TransformerManager().transform_cell(c.source))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertIn(alias.name.split('.')[0], allowed)
                if isinstance(node, ast.ImportFrom):
                    self.assertEqual(node.level, 0)
                    self.assertIn(node.module.split('.')[0], allowed)
            self.assertNotIn('inspect.getsource', c.source)
            self.assertNotIn('sys.path.insert', c.source)
            self.assertNotIn('Image(filename=', c.source)
        for cell in self.nb.cells:
            if cell.cell_type == 'markdown':
                self.assertFalse(any(line.startswith('    ') for line in cell.source.splitlines()))

    def test_embedded_bytes_equal_preserved_sources(self):
        cell = next(c for c in self.codes if 'datos-incorporados' in c.metadata.get('tags', []))
        assignment = ast.parse(cell.source).body[0]
        payload = ast.literal_eval(assignment.value)
        self.assertEqual(len(payload), 3)
        for filename, data in payload.items():
            raw = base64.b64decode(data['base64'], validate=True)
            self.assertEqual(raw, (ROOT/'data/crudos'/filename).read_bytes())
            self.assertEqual(hashlib.sha256(raw).hexdigest(), data['sha256'])

    def test_executed_outputs_and_inline_figures(self):
        nbformat.validate(self.nb)
        self.assertEqual([c.execution_count for c in self.codes], list(range(1, len(self.codes)+1)))
        errors = [o for c in self.codes for o in c.outputs if o.output_type == 'error']
        self.assertEqual(errors, [])
        pngs = [o.data['image/png'] for c in self.codes for o in c.outputs if 'image/png' in o.get('data', {})]
        self.assertEqual(len(pngs), 9)
        self.assertTrue(all(base64.b64decode(p).startswith(b'\x89PNG') for p in pngs))
        self.assertTrue(self.nb.metadata.grupo5.ejecutado_en_carpeta_vacia)
        self.assertIn('Declaración de uso de inteligencia artificial', self.nb.cells[-1].source)

    def test_isolated_execution_matches_audited_analysis(self):
        expected, prices, audit, *_ = clean_sources(*load_sources(ROOT))
        summary, _, _, _, _, comparison = analyze(expected, prices)
        with tempfile.TemporaryDirectory(prefix='test_eda_autonomo_') as tmp:
            # No se copian módulos, datos ni imágenes al directorio de ejecución.
            self.assertEqual(list(Path(tmp).iterdir()), [])
            notebook = nbformat.reads(nbformat.writes(self.nb), as_version=4)
            client = NotebookClient(notebook, timeout=240, kernel_name='python3', resources={'metadata': {'path': tmp}})
            client.km = KernelManager(kernel_name='python3')
            client.km.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
            client.execute()
            out = Path(tmp)/'salidas_EDA_notebook'
            actual = pd.read_csv(out/'produccion_limpia.csv', parse_dates=['fecha'])
            pd.testing.assert_frame_equal(actual, expected, check_dtype=False, rtol=1e-10, atol=1e-8)
            got_comparison = pd.read_csv(out/'comparacion_interanual.csv')
            pd.testing.assert_frame_equal(got_comparison, comparison.reset_index(drop=True), check_dtype=False, rtol=1e-10, atol=1e-8)
            result = json.loads((out/'resumen.json').read_text(encoding='utf-8'))
            self.assertAlmostEqual(result['crudo_actual'], summary['crudo_actual'], places=6)
            self.assertAlmostEqual(result['correlacion_bloque3']['r'], summary['correlacion']['r'], places=10)
            self.assertEqual(result['validaciones_correctas'], 23)
            self.assertAlmostEqual(result['cambio_sin_julio_pct'], -2.259238395228, places=8)
            self.assertEqual(len(list((out/'figuras').glob('*.png'))), 9)


if __name__ == '__main__':
    unittest.main()
