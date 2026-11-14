"""Проверки формата сравнений с официальным .NET CLI"""

import io
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout
from pathlib import Path

from scripts.compare_dotnet import (
    make_project, read_assets, read_packages, show_diff, show_edges
)


class CompareTests(unittest.TestCase):
    """Проверки чтения и сопоставления штатного вывода .NET"""

    def test_make_project(self):
        """Генерация .csproj сохраняет имя и версию пакета"""
        with tempfile.TemporaryDirectory() as temp:
            path = make_project(Path(temp), "Package.One", "2.1.0")
            root = ET.parse(path).getroot()
        self.assertEqual(root.attrib["Sdk"], "Microsoft.NET.Sdk")
        dep = root.find("./ItemGroup/PackageReference")
        self.assertEqual(dep.attrib["Include"], "Package.One")
        self.assertEqual(dep.attrib["Version"], "2.1.0")

    def test_read_packages(self):
        """Из JSON извлекаются прямые и транзитивные зависимости"""
        data = {"projects": [{"frameworks": [{
            "framework": "net8.0",
            "topLevelPackages": [{"id": "Package.One",
                                  "resolvedVersion": "1.0.0"}],
            "transitivePackages": [{"id": "Package.Two",
                                    "resolvedVersion": "2.0.0"}]
        }]}]}
        items, deps = read_packages(json.dumps(data))
        self.assertEqual(items["package.one"], "1.0.0")
        self.assertEqual(items["package.two"], "2.0.0")
        self.assertEqual(deps, ["Package.Two"])

    def test_empty_transitive(self):
        """Пакет без транзитивных зависимостей корректно разбирается"""
        data = {"projects": [{"frameworks": [{"topLevelPackages": []}]}]}
        items, deps = read_packages(json.dumps(data))
        self.assertEqual(items, {})
        self.assertEqual(deps, [])

    def test_invalid_json(self):
        """Неверный формат ответа от dotnet выдаёт ошибку"""
        with self.assertRaisesRegex(ValueError, "JSON"):
            read_packages("не json")

    def test_compare_equal(self):
        """Одинаковые списки пакетов считаются совпадением"""
        output = io.StringIO()
        with redirect_stdout(output):
            show_diff({"a": {"1.0.0"}}, {"a": "1.0.0"})
        self.assertIn("совпали", output.getvalue())

    def test_compare_mismatch(self):
        """Показываются лишние пакеты и несовпадающие версии"""
        output = io.StringIO()
        with redirect_stdout(output):
            show_diff({"a": {"1.0.0"}, "b": {"2.0.0"}},
                      {"a": "2.0.0", "c": "3.0.0"})
        self.assertIn("Только у нас: 1", output.getvalue())
        self.assertIn("Только в .NET: 1", output.getvalue())
        self.assertIn("Разные версии: 1", output.getvalue())


    def test_assets_graph(self):
        """В assets.json читаются фактически разрешённые рёбра"""
        data = {"targets": {"net8.0": {
            "A/1.0.0": {"type": "package", "dependencies": {"B": "2.0.0"}},
            "B/2.0.0": {"type": "package", "dependencies": {}},
            "net8.0/8.0.0": {"type": "project"}
        }}}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "project.assets.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            graph = read_assets(path)
        self.assertEqual(graph["A@1.0.0"], ["B@2.0.0"])
        self.assertEqual(graph["B@2.0.0"], [])

    def test_assets_invalid(self):
        """Отсутствующий файл assets.json вызывает понятную ошибку"""
        with self.assertRaisesRegex(ValueError, "project.assets.json"):
            read_assets(Path("absent.assets.json"))

    def test_edges_match(self):
        """Совпадающие рёбра не создают различий"""
        output = io.StringIO()
        graph = {"A@1.0": ["B@2.0"], "B@2.0": []}
        with redirect_stdout(output):
            show_edges(graph, graph)
        self.assertIn("Рёбра только у нас: 0", output.getvalue())
        self.assertIn("Рёбра только в .NET: 0", output.getvalue())

    def test_edges_differ(self):
        """Разные версии и направления рёбер замечаются при сравнении"""
        output = io.StringIO()
        with redirect_stdout(output):
            show_edges({"A@1.0": ["B@2.0"]},
                       {"A@1.0": ["C@3.0"]})
        self.assertIn("Рёбра только у нас: 1", output.getvalue())
        self.assertIn("Рёбра только в .NET: 1", output.getvalue())


if __name__ == "__main__":
    unittest.main()
