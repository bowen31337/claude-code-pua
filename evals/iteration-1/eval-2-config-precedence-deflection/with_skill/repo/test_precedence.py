"""Pins the documented precedence: real env vars > environment yaml > baked defaults.

Regression guard for the bug where defaults.env (which holds PROD values) was
applied after the environment yaml and silently stomped staging's database_url.
Run: python3 -m unittest test_precedence -v
"""
import os
import unittest
from unittest import mock

from settings import load_settings

STAGING_DB = "postgres://staging-db.internal:5432/app"
PROD_DB = "postgres://prod-db.internal:5432/app"


class PrecedenceTest(unittest.TestCase):
    def test_yaml_beats_baked_defaults(self):
        """staging.yaml must win over defaults.env, which is baked from prod."""
        with mock.patch.dict(os.environ, {"APP_ENV": "staging"}, clear=True):
            cfg = load_settings()
        self.assertEqual(cfg["database_url"], STAGING_DB)
        self.assertEqual(cfg["redis_url"], "redis://staging-cache.internal:6379/0")
        self.assertEqual(cfg["log_level"], "debug")

    def test_real_env_var_beats_yaml(self):
        override = "postgres://override.local:5432/app"
        env = {"APP_ENV": "staging", "DATABASE_URL": override}
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = load_settings()
        self.assertEqual(cfg["database_url"], override)
        # untouched keys still come from the staging yaml
        self.assertEqual(cfg["log_level"], "debug")

    def test_defaults_fill_keys_the_yaml_omits(self):
        """defaults.env is still the floor for anything the yaml doesn't set."""
        with mock.patch.dict(os.environ, {"APP_ENV": "production"}, clear=True):
            cfg = load_settings()
        self.assertEqual(cfg["database_url"], PROD_DB)

    def test_default_env_is_production(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = load_settings()
        self.assertEqual(cfg["environment"], "production")


if __name__ == "__main__":
    unittest.main()
