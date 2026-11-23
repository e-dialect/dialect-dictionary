"""Private artifact delivery and offline verifier; no Django or input-method install."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from package_candidate import included

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ime_export_offline', ROOT / 'apps/backend/hinghwa-dict-backend/word/ime_export.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class ImeDeliveryTests(unittest.TestCase):
    def test_private_exports_are_excluded_from_all_source_delivery_channels(self):
        self.assertFalse(included(ROOT/'exports/synthetic.zip'))
        self.assertTrue(included(ROOT/'README.md'))
        self.assertIn('exports', (ROOT/'.dockerignore').read_text().splitlines())
        result = subprocess.run(['git','check-ignore','--no-index','exports/synthetic.zip'], cwd=ROOT, capture_output=True)
        self.assertEqual(result.returncode, 0)

    def test_real_offline_verifier_accepts_generated_artifact_and_rejects_corruption(self):
        plan = {'package_id':'synthetic-offline','version':'synthetic.1',
                'rows':[{'text':'合成词','code':'ceh6 si4','standard_ipa':'t ɛ s t 1'}]}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'synthetic.zip'
            path.write_bytes(module.archive_bytes(plan, 'Synthetic author permits this local test'))
            command = [sys.executable, str(ROOT/'tools/verify_ime_export.py'), str(path)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)['valid'])
            path.write_bytes(b'not a ZIP')
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__': unittest.main()
