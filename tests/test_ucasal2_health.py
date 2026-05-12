# -*- coding: utf-8 -*-
"""
Static health checks for the ucasal2 addon.
Runs without Athento core packages (core, file, operations, etc.).
"""
import ast
import re
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
UCASAL2 = REPO_ROOT / "ucasal2"


class TestPythonSyntax(unittest.TestCase):
    def test_all_py_files_parse(self):
        failures = []
        for path in sorted(UCASAL2.rglob("*.py")):
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as e:
                failures.append(f"{path.relative_to(REPO_ROOT)}: {e}")
        self.assertFalse(failures, "\n" + "\n".join(failures))

    def test_compileall_zero_exit(self):
        proc = subprocess.run(
            [sys.executable, "-m", "compileall", "-q", str(UCASAL2)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=(proc.stdout or "") + (proc.stderr or ""),
        )


class TestRenameConsistency(unittest.TestCase):
    def test_no_stale_package_imports(self):
        """Imports must target ucasal2, not top-level ucasal."""
        bad = []
        pattern = re.compile(r"^\s*from\s+ucasal\.|^\s*import\s+ucasal\s*$", re.MULTILINE)
        for path in UCASAL2.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if pattern.search(text):
                bad.append(str(path.relative_to(REPO_ROOT)))
        self.assertFalse(bad, "Stale ucasal imports:\n" + "\n".join(bad))

    def test_sac_keys_use_ucasal2_prefix(self):
        """UcasalConfig reads SAC keys with ucasal2. prefix."""
        utils = UCASAL2 / "utils.py"
        text = utils.read_text(encoding="utf-8")
        self.assertIn("SAC.get_", text)
        self.assertRegex(text, r"SAC\.get_\w+\(\s*'ucasal2\.")
        self.assertNotRegex(text, r"SAC\.get_\w+\(\s*'ucasal\.[^2]")

    def test_apps_urls_alignment(self):
        apps = (UCASAL2 / "apps.py").read_text(encoding="utf-8")
        urls = (UCASAL2 / "urls.py").read_text(encoding="utf-8")
        init = (UCASAL2 / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("name = 'ucasal2'", apps)
        self.assertIn(r"r'^ucasal2/api/'", apps)
        self.assertIn("include('ucasal2.urls'", apps)
        self.assertIn("namespace='ucasal2'", apps)
        self.assertIn("app_name = 'ucasal2'", urls)
        self.assertIn("from ucasal2.endpoints import", urls)
        self.assertIn("ucasal2.apps.Ucasal2AppConfig", init)


class TestDjangoAppConfig(unittest.TestCase):
    def test_ucasal2_app_config_importable(self):
        """Isolated subprocess so Django settings are not shared with other tests."""
        code = f"""import sys
sys.path.insert(0, {repr(str(REPO_ROOT))})
import django
from django.conf import settings
settings.configure(
    INSTALLED_APPS=[
        "django.contrib.contenttypes",
        "django.contrib.auth",
        "ucasal2",
    ],
    SECRET_KEY="test-health-check",
    USE_TZ=True,
)
django.setup()
from ucasal2.apps import Ucasal2AppConfig
assert Ucasal2AppConfig.name == "ucasal2"
"""
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=(proc.stdout or "") + (proc.stderr or ""),
        )


class TestMailTemplates(unittest.TestCase):
    def test_otp_template_file_exists(self):
        """Code references ucasal2_custom_otp_notification."""
        actas = (UCASAL2 / "endpoints" / "actas.py").read_text(encoding="utf-8")
        self.assertIn("'ucasal2_custom_otp_notification'", actas)
        tpl = UCASAL2 / "mail_templates" / "ucasal2_custom_otp_notification.html"
        self.assertTrue(tpl.is_file(), msg=f"Missing {tpl.name}")


if __name__ == "__main__":
    unittest.main()
