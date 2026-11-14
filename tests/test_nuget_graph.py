"""Проверки транзитивного получения NuGet-зависимостей"""

import json
import unittest
from unittest.mock import patch

from src.graph import build_graph
from src.nuget_graph import NugetGraph

BASE = "https://example.org/flat"
ROOT = "Root.Package@1.0.0"
XML = b"""<package><metadata><dependencies>
<group targetFramework="net6.0">
<dependency id="Package.One" version="[1.0.0,2.0.0)" />
</group><group targetFramework="net8.0">
<dependency id="Package.Two" version="[3.0.0]" />
</group></dependencies></metadata></package>"""


class NugetGraphTests(unittest.TestCase):
    """Проверки загрузки манифестов, версий и кеширования"""

    def __init__(self, method_name="runTest"):
        """Подготовить ответы тестового NuGet-репозитория"""
        super().__init__(method_name)
        self.data = {
            BASE + "/root.package/1.0.0/root.package.nuspec": XML,
            BASE + "/package.one/index.json": json.dumps({
                "versions": ["1.0.0", "2.0.0"]}).encode(),
            BASE + "/package.two/index.json": b'{"versions":["3.0.0"]}',
        }

    def get_data(self, url):
        """Вернуть документ по указанному адресу"""
        return self.data[url]

    def test_group_union(self):
        """Объединить группы платформ и выбрать версии"""
        with patch("src.nuget_graph.package_base", return_value=BASE):
            with patch("src.nuget_graph.download", side_effect=self.get_data):
                source = NugetGraph("https://example.org/index.json")
                items = source.children(ROOT)
        self.assertEqual(items, ["Package.One@1.0.0", "Package.Two@3.0.0"])

    def test_cache(self):
        """Не загружать одинаковые документы дважды"""
        with patch("src.nuget_graph.package_base", return_value=BASE):
            with patch("src.nuget_graph.download",
                       side_effect=self.get_data) as get:
                source = NugetGraph("https://example.org/index.json")
                source.children(ROOT)
                source.children(ROOT)
        self.assertEqual(get.call_count, 3)

    def test_filter_before_request(self):
        """Не загружать исключённый фильтром пакет"""
        with patch("src.nuget_graph.package_base", return_value=BASE):
            with patch("src.nuget_graph.download",
                       side_effect=self.get_data) as get:
                source = NugetGraph("https://example.org/index.json", "two")
                items = source.children(ROOT)
        self.assertEqual(items, ["Package.One@1.0.0"])
        self.assertEqual(get.call_count, 2)

    def test_zero_depth_without_requests(self):
        """Глубина ноль не требует подключения к NuGet"""
        with patch("src.nuget_graph.package_base") as get:
            source = NugetGraph("https://example.org/index.json")
            graph = build_graph(ROOT, source.children, 0)
        self.assertEqual(graph, {ROOT: []})
        get.assert_not_called()

    def test_case_insensitive_package(self):
        """Разные регистры имени не создают дубликат пакета"""
        self.data[BASE + "/root.package/1.0.0/root.package.nuspec"] = (
            b"<package><metadata><dependencies>"
            b"<dependency id='root.package' version='[1.0.0]' />"
            b"</dependencies></metadata></package>"
        )
        self.data[BASE + "/root.package/index.json"] = (
            b'{"versions":["1.0.0"]}'
        )
        with patch("src.nuget_graph.package_base", return_value=BASE):
            with patch("src.nuget_graph.download", side_effect=self.get_data):
                source = NugetGraph("https://example.org/index.json")
                items = source.children(ROOT)
        self.assertEqual(items, [ROOT])

    def test_bad_versions(self):
        """Ошибочный индекс версий обрабатывается без падения"""
        self.data[BASE + "/package.one/index.json"] = b"{}"
        with patch("src.nuget_graph.package_base", return_value=BASE):
            with patch("src.nuget_graph.download", side_effect=self.get_data):
                source = NugetGraph("https://example.org/index.json")
                with self.assertRaisesRegex(ValueError, "верси"):
                    source.children(ROOT)


if __name__ == "__main__":
    unittest.main()
