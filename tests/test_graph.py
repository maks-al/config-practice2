"""Проверки DFS, фильтра, глубины и тестового репозитория"""

import tempfile
import unittest
from pathlib import Path

from src.graph import build_graph, read_test_repo


class GraphTests(unittest.TestCase):
    """Проверки построения графа зависимостей"""

    def __init__(self, method_name="runTest"):
        """Создать тестовый граф с общими зависимостями"""
        super().__init__(method_name)
        self.repo = {
            "A": ["B", "C"], "B": ["D"], "C": ["F"],
            "D": ["F"], "F": ["G"], "G": []
        }

    def test_transitive(self):
        """Обходить зависимости дальше первого уровня"""
        graph = build_graph("A", self.repo.__getitem__, 4)
        self.assertEqual(graph["D"], ["F"])
        self.assertEqual(graph["F"], ["G"])
        self.assertIn("G", graph)

    def test_no_recursion(self):
        """Длинная цепочка обрабатывается без рекурсии"""
        nodes = {str(i): [str(i + 1)] for i in range(1200)}
        nodes[str(1200)] = []
        graph = build_graph("0", nodes.__getitem__, 1200)
        self.assertEqual(len(graph), 1201)

    def test_cycle(self):
        """Цикл не вызывает бесконечный обход"""
        repo = {"A": ["B"], "B": ["C"], "C": ["A"]}
        graph = build_graph("A", repo.__getitem__, 10)
        self.assertEqual(graph["C"], ["A"])
        self.assertEqual(len(graph), 3)

    def test_zero_depth(self):
        """При глубине ноль остаётся только исходный узел"""
        graph = build_graph("A", self.repo.__getitem__, 0)
        self.assertEqual(graph, {"A": []})

    def test_depth_limit(self):
        """Узлы на последнем уровне не раскрываются"""
        graph = build_graph("A", self.repo.__getitem__, 1)
        self.assertEqual(graph, {"A": ["B", "C"], "B": [], "C": []})

    def test_filter(self):
        """Исключённый узел не добавляется и не раскрывается"""
        graph = build_graph("A", self.repo.__getitem__, 4, "b")
        self.assertEqual(graph["A"], ["C"])
        self.assertNotIn("B", graph)
        self.assertNotIn("D", graph)

    def test_filter_root(self):
        """Фильтр не должен скрывать начальный пакет молча"""
        with self.assertRaisesRegex(ValueError, "фильтром"):
            build_graph("A", self.repo.__getitem__, 3, "a")

    def test_shorter_path(self):
        """Повторно раскрыть узел, найденный на меньшей глубине"""
        graph = build_graph("A", self.repo.__getitem__, 3)
        self.assertEqual(graph["F"], ["G"])
        self.assertIn("G", graph)

    def test_duplicate_edges(self):
        """Повторные зависимости одного узла удаляются"""
        repo = {"A": ["B", "B"], "B": []}
        self.assertEqual(build_graph("A", repo.__getitem__, 2)["A"], ["B"])


class TestFileTests(unittest.TestCase):
    """Проверки текстового формата тестовых графов"""

    def check_file(self, text):
        """Создать временный файл и прочитать его"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "graph.txt"
            path.write_text(text, encoding="utf-8")
            return read_test_repo(path)

    def test_valid_file(self):
        """Корректно прочитать группы заглавных букв"""
        graph = self.check_file("# пример\nA: B C\nB:\nC: A\n")
        self.assertEqual(graph["A"], ["B", "C"])
        self.assertEqual(graph["B"], [])

    def test_invalid_name(self):
        """Отвергать имена с маленькими буквами"""
        with self.assertRaisesRegex(ValueError, "узел"):
            self.check_file("a: B\nB:\n")

    def test_invalid_dependency(self):
        """Отвергать некорректные имена зависимостей"""
        with self.assertRaisesRegex(ValueError, "зависимость"):
            self.check_file("A: B1\nB:\n")

    def test_missing_node(self):
        """Отклонять ссылки на отсутствующие узлы"""
        with self.assertRaisesRegex(ValueError, "не описаны"):
            self.check_file("A: B\n")

    def test_duplicate_node(self):
        """Отклонять повторное объявление узла"""
        with self.assertRaisesRegex(ValueError, "повтор"):
            self.check_file("A:\nA:\n")

    def test_missing_colon(self):
        """Отклонять строку без двоеточия"""
        with self.assertRaisesRegex(ValueError, "узел"):
            self.check_file("A B\n")


if __name__ == "__main__":
    unittest.main()
