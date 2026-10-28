import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("site_config", ROOT / "apps/backend/hinghwa-dict-backend/HinghwaDict/site_config.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PublicConfigTests(unittest.TestCase):
    def test_two_distinct_deployments(self):
        coast = module.load_config(ROOT / "config/examples/coast.json")
        mountain = module.load_config(ROOT / "config/examples/mountain.json")
        self.assertNotEqual(coast["name"], mountain["name"])
        self.assertNotEqual(coast["dialect"]["code"], mountain["dialect"]["code"])
        self.assertFalse(any(coast["features"].values()))
        self.assertFalse(any(mountain["features"].values()))
        self.assertEqual(coast["apiBase"], mountain["apiBase"])

    def test_private_fields_and_credential_urls_rejected(self):
        base = module.load_config(ROOT / "config/examples/coast.json")
        mutations = [dict(base, SECRET_KEY="must-not-be-public"), dict(base, webUrl="https://user:password@example.test")]
        for config in mutations:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "site.json"
                path.write_text(json.dumps(config))
                with self.assertRaises(ValueError):
                    module.load_config(path)

    def test_flags_are_not_truthy_strings(self):
        config = module.load_config(ROOT / "config/examples/coast.json")
        config["features"]["pinyin"] = "false"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "site.json"
            path.write_text(json.dumps(config))
            with self.assertRaises(ValueError):
                module.load_config(path)

    def test_hinghwa_capabilities_preserved_in_instance_configuration(self):
        config = module.load_config(ROOT / "config/examples/hinghwa.json")
        for feature in ("pinyin", "kinship", "geography", "quiz", "music", "dailyExpressions"):
            self.assertTrue(config["features"][feature])
        self.assertTrue(config["phonologyAudioBase"])
        self.assertEqual(config["dialect"]["name"], "莆仙方言")


if __name__ == "__main__":
    unittest.main()
