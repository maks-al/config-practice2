"""Проверки настоящего запуска консольной программы"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class CliTests(unittest.TestCase):
    """Проверки кода завершения и вывода в консоль"""

    def run_cli(self, *args):
        """Запустить программу отдельным процессом Python"""
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        return subprocess.run(
            [sys.executable, str(ROOT / "run.py"), *args],
            capture_output=True, text=True, encoding="utf-8", env=env
        )

    def test_default_config(self):
        """Без аргументов загружается встроенный тестовый CSV"""
        result = self.run_cli()
        self.assertEqual(result.returncode, 0)
        self.assertIn("package: A", result.stdout)
        self.assertIn("test_mode: true", result.stdout)

    def test_url_config(self):
        """Явно заданный CSV выводит все шесть параметров"""
        path = ROOT / "examples/config_nuget.csv"
        result = self.run_cli("--config", str(path))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.stdout.splitlines()), 6)
        self.assertIn("version: 13.0.3", result.stdout)

    def test_invalid_config(self):
        """Ошибочный CSV даёт код 1 и сообщение об ошибке"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "broken.csv"
            path.write_text("key,value\npackage,!?\n", encoding="utf-8")
            result = self.run_cli("--config", str(path))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Ошибка:", result.stderr)


if __name__ == "__main__":
    unittest.main()
