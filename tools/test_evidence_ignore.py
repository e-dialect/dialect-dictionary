"""Ensure local evidence is deny-by-default; only reviewed summaries enter Git."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class EvidenceIgnoreTests(unittest.TestCase):
    def test_unknown_logs_and_json_ignored_known_summary_allowed(self):
        for name in ['private-import.log', 'customer-audio.json', 'nested/trace.txt']:
            result = subprocess.run(['git','check-ignore','--no-index','-q','docs/development/evidence/'+name],cwd=ROOT)
            self.assertEqual(result.returncode,0,name)
        for name in ['onboarding-validation.json','round2-summary.json']:
            result = subprocess.run(['git','check-ignore','--no-index','-q','docs/development/evidence/'+name],cwd=ROOT)
            self.assertEqual(result.returncode,1,name)

if __name__ == '__main__': unittest.main()
