"""Проверки загрузки и разбора прямых зависимостей NuGet"""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError

from src.main import main
from src.nuget import (
    direct_dependencies, is_base, normalize_version, package_base,
    parse_nuspec, valid_url
)

BASE = "https://example.org/flat"
INDEX = json.dumps({"resources": [
    {"@type": ["PackageBaseAddress/3.0.0"], "@id": BASE}
]}).encode()
GROUPED = b"""<package xmlns="urn:nuget"><metadata><dependencies>
<group targetFramework="net6.0">
<dependency id="Package.One" version="[1.0.0,2.0.0)" />
</group><group targetFramework="net8.0" />
</dependencies></metadata></package>"""
FLAT = b"""<package><metadata><dependencies>
<dependency id="Package.Two" version="[3.0.0,)" />
</dependencies></metadata></package>"""
EMPTY = b"<package><metadata /></package>"


class NugetTests(unittest.TestCase):
    """Тесты официального формата сервисного индекса и nuspec"""

    def test_normalized_version(self):
        """Версия приводится к имени файла flat container"""
        self.assertEqual(normalize_version("1.2"), "1.2.0")
        self.assertEqual(normalize_version("1.2.3.0"), "1.2.3")
        self.assertEqual(normalize_version("01.2.3-RC+build"), "1.2.3-rc")

    def test_resource_types(self):
        """Ресурс может обозначаться строкой или списком"""
        self.assertTrue(is_base("PackageBaseAddress/3.0.0"))
        self.assertTrue(is_base(["other", "PackageBaseAddress/3.0.0"]))
        self.assertFalse(is_base("RegistrationsBaseUrl/3.6.0"))

    def test_resource_url(self):
        """Неверные URL источника отклоняются"""
        self.assertTrue(valid_url("https://example.org/flat"))
        self.assertFalse(valid_url("file:///tmp/flat"))
        self.assertFalse(valid_url(None))

    def test_grouped_dependencies(self):
        """Зависимости группируются по платформам"""
        groups = parse_nuspec(GROUPED)
        self.assertEqual(groups[0][0], "net6.0")
        self.assertEqual(groups[0][1], [("Package.One", "[1.0.0,2.0.0)")])
        self.assertEqual(groups[1], ("net8.0", []))

    def test_flat_dependencies(self):
        """Зависимости без группы остаются общими"""
        self.assertEqual(
            parse_nuspec(FLAT), [("общие", [("Package.Two", "[3.0.0,)")])]
        )

    def test_empty_dependencies(self):
        """Отсутствующие зависимости дают пустой список"""
        self.assertEqual(parse_nuspec(EMPTY), [("общие", [])])

    def test_invalid_xml(self):
        """Повреждённый манифест вызывает понятную ошибку"""
        with self.assertRaisesRegex(ValueError, "XML"):
            parse_nuspec(b"<package>")

    def test_missing_metadata(self):
        """Манифест без metadata отклоняется"""
        with self.assertRaisesRegex(ValueError, "metadata"):
            parse_nuspec(b"<package />")

    def test_missing_dependency_version(self):
        """Зависимость без версии отклоняется"""
        xml = b"<package><metadata><dependencies><dependency id='A' />"
        xml += b"</dependencies></metadata></package>"
        with self.assertRaisesRegex(ValueError, "version"):
            parse_nuspec(xml)

    def test_missing_service(self):
        """Неподдерживаемый тип NuGet-ресурса выдаёт ошибку"""
        data = b'{"resources": [{"@type": "Other", "@id": "x"}]}'
        with patch("src.nuget.download", return_value=data):
            with self.assertRaisesRegex(ValueError, "PackageBaseAddress"):
                package_base("https://example.org/index.json")

    def test_invalid_service(self):
        """Индекс без resources отклоняется"""
        with patch("src.nuget.download", return_value=b"{}"):
            with self.assertRaisesRegex(ValueError, "resources"):
                package_base("https://example.org/index.json")

    def test_direct_dependencies(self):
        """Адрес nuspec строится из URL текущего репозитория"""
        with patch("src.nuget.download", side_effect=[INDEX, GROUPED]) as get:
            groups = direct_dependencies(
                "https://example.org/index.json", "My.Package", "1.2.0"
            )
        self.assertEqual(groups[0][0], "net6.0")
        self.assertEqual(get.call_count, 2)
        self.assertEqual(
            get.call_args.args[0],
            "https://example.org/flat/my.package/1.2.0/my.package.nuspec"
        )

    def test_http_not_found(self):
        """HTTP 404 переводится в понятную ошибку"""
        error = HTTPError("url", 404, "Not Found", {}, None)
        with patch("src.nuget.urllib.request.urlopen", side_effect=error):
            from src.nuget import download
            with self.assertRaisesRegex(ValueError, "404"):
                download("https://example.org/absent")

    def test_cli_dependencies(self):
        """Ключ deps выводит полученные зависимости"""
        out = io.StringIO()
        path = "examples/config_nuget.csv"
        groups = [("net8.0", [("Package.One", "[1.0.0,)")])]
        with patch("src.main.direct_dependencies", return_value=groups):
            with redirect_stdout(out):
                code = main(["--config", path, "--deps"])
        self.assertEqual(code, 0)
        self.assertIn("Package.One: [1.0.0,)", out.getvalue())

    def test_test_mode_rejected(self):
        """Получение NuGet-зависимостей не запускается в тестовом режиме"""
        err = io.StringIO()
        with redirect_stderr(err):
            code = main(["--deps"])
        self.assertEqual(code, 1)
        self.assertIn("test_mode=false", err.getvalue())


if __name__ == "__main__":
    unittest.main()
