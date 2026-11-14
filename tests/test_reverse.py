"""Проверки прямых и транзитивных обратных зависимостей"""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from src.main import main
from src.reverse import (
    filter_repo, find_target, invert_graph, reverse_dependencies
)

ROOT = Path(__file__).resolve().parent.parent


class ReverseTests(unittest.TestCase):
    """Тесты обратного графа и поиска DFS"""

    def setUp(self):
        """Создать граф с общими и независимыми ветвями"""
        self.repo = {
            "A": ["B", "C"], "B": ["D"], "C": ["D"],
            "D": [], "E": ["D"], "F": ["E"], "G": []
        }

    def test_invert(self):
        """У каждой зависимости находятся все прямые родители"""
        graph = invert_graph(self.repo)
        self.assertEqual(graph["D"], ["B", "C", "E"])
        self.assertEqual(graph["A"], [])

    def test_transitive(self):
        """DFS находит обратные зависимости нескольких уровней"""
        node, graph = reverse_dependencies(self.repo, "D", 4)
        self.assertEqual(node, "D")
        self.assertEqual(graph["D"], ["B", "C", "E"])
        self.assertEqual(graph["B"], ["A"])
        self.assertEqual(graph["E"], ["F"])
        self.assertEqual(graph["F"], [])

    def test_reverse_root(self):
        """Пакет без родителей не получает ложные зависимости"""
        _, graph = reverse_dependencies(self.repo, "G", 4)
        self.assertEqual(graph, {"G": []})

    def test_depth_zero(self):
        """Глубина ноль оставляет только выбранный пакет"""
        _, graph = reverse_dependencies(self.repo, "D", 0)
        self.assertEqual(graph, {"D": []})

    def test_depth_one(self):
        """Глубина один оставляет только прямых родителей"""
        _, graph = reverse_dependencies(self.repo, "D", 1)
        self.assertEqual(graph["D"], ["B", "C", "E"])
        self.assertEqual(graph["B"], [])
        self.assertEqual(graph["C"], [])
        self.assertEqual(graph["E"], [])

    def test_filtered(self):
        """Фильтр удаляет узел вместе со связями"""
        repo = filter_repo(self.repo, "b")
        _, graph = reverse_dependencies(repo, "D", 4)
        self.assertEqual(graph["D"], ["C", "E"])
        self.assertNotIn("B", graph)

    def test_cycle(self):
        """Наличие цикла не приводит к бесконечному обходу"""
        repo = {"A": ["B"], "B": ["C"], "C": ["A"]}
        _, graph = reverse_dependencies(repo, "A", 10)
        self.assertEqual(graph["A"], ["C"])
        self.assertEqual(graph["C"], ["B"])
        self.assertEqual(len(graph), 3)

    def test_long_chain(self):
        """Большой граф обходится без рекурсии"""
        repo = {str(i): [str(i + 1)] for i in range(1200)}
        repo[str(1200)] = []
        _, graph = reverse_dependencies(repo, "1200", 1200)
        self.assertEqual(len(graph), 1201)

    def test_version_name(self):
        """Пакет NuGet находится по имени без учёта регистра"""
        graph = {"Package.One@1.0.0": [], "Package.Two@2.0.0": []}
        self.assertEqual(find_target(graph, "package.one"),
                         "Package.One@1.0.0")

    def test_exact_version(self):
        """Пакет можно найти по имени и версии"""
        graph = {"A@1.0.0": [], "A@2.0.0": []}
        self.assertEqual(find_target(graph, "a@2.0.0"), "A@2.0.0")

    def test_ambiguous_version(self):
        """При нескольких версиях требуется уточнить номер"""
        graph = {"A@1.0.0": [], "A@2.0.0": []}
        with self.assertRaisesRegex(ValueError, "несколько версий"):
            find_target(graph, "A")

    def test_missing(self):
        """Отсутствующий пакет вызывает понятную ошибку"""
        with self.assertRaisesRegex(ValueError, "не найден"):
            reverse_dependencies(self.repo, "Z", 4)


class ReverseCliTests(unittest.TestCase):
    """Проверки нового режима и сохранения старых"""

    def test_default_target(self):
        """Флаг reverse без аргумента использует package из CSV"""
        path = ROOT / "examples/config_reverse.csv"
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--config", str(path), "--reverse"])
        self.assertEqual(code, 0)
        self.assertIn("D <- B, C, E", output.getvalue())

    def test_custom_target(self):
        """Режим reverse принимает отдельное имя пакета"""
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--reverse", "D"])
        self.assertEqual(code, 0)
        self.assertIn("D <- B, C", output.getvalue())

    def test_missing_target(self):
        """Ошибочный пакет даёт код возврата один"""
        output = io.StringIO()
        with redirect_stderr(output):
            code = main(["--reverse", "Z"])
        self.assertEqual(code, 1)
        self.assertIn("не найден", output.getvalue())

    def test_nuget_mode(self):
        """Поиск работает с узлами NuGet и номерами версий"""
        path = ROOT / "examples/config_dependencies.csv"
        graph = {"Main@1.0.0": ["Child@2.0.0"], "Child@2.0.0": []}
        output = io.StringIO()
        with patch("src.main.load_graph", return_value=("Main@1.0.0", graph)):
            with redirect_stdout(output):
                code = main(["--config", str(path), "--reverse", "Child"])
        self.assertEqual(code, 0)
        self.assertIn("Child@2.0.0 <- Main@1.0.0", output.getvalue())


if __name__ == "__main__":
    unittest.main()
