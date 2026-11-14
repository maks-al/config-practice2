"""Проверки построения диаграмм PlantUML"""

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from src.main import main
from src.uml import to_plantuml

ROOT = Path(__file__).resolve().parent.parent


class PlantUmlTests(unittest.TestCase):
    """Проверки узлов, рёбер и особых случаев"""

    def test_empty_graph(self):
        """Пустой граф образует корректный блок PlantUML"""
        self.assertEqual(to_plantuml({}),
                         "@startuml\nleft to right direction\n@enduml")

    def test_simple_graph(self):
        """В диаграмме присутствуют узлы и их направление"""
        text = to_plantuml({"A": ["B"], "B": []})
        self.assertIn('rectangle "A" as N0', text)
        self.assertIn('rectangle "B" as N1', text)
        self.assertIn("N0 --> N1", text)
        self.assertNotIn("N1 --> N0", text)

    def test_cycle(self):
        """Циклические рёбра сохраняются без повторного обхода"""
        text = to_plantuml({"A": ["B"], "B": ["A"]})
        self.assertIn("N0 --> N1", text)
        self.assertIn("N1 --> N0", text)
        self.assertEqual(text.count("rectangle"), 2)

    def test_shared_dependency(self):
        """Общая зависимость объявляется один раз"""
        text = to_plantuml({"A": ["C"], "B": ["C"], "C": []})
        self.assertEqual(text.count('rectangle "C"'), 1)
        self.assertEqual(text.count("-->"), 2)

    def test_duplicate_edges(self):
        """Повторное ребро не дублируется"""
        text = to_plantuml({"A": ["B", "B"], "B": []})
        self.assertEqual(text.count("N0 --> N1"), 1)

    def test_implicit_node(self):
        """Пакет без отдельной записи также отображается"""
        text = to_plantuml({"A": ["B"]})
        self.assertIn('rectangle "B" as N1', text)

    def test_escaped_label(self):
        """Кавычки и переводы строк не ломают диаграмму"""
        text = to_plantuml({'A"\nB': []})
        self.assertIn('rectangle "A\\"\\nB"', text)

    def test_version_nodes(self):
        """Различные версии NuGet получают разные узлы"""
        nodes = {"A@1.0.0": ["B@2.0.0"], "B@2.0.0": []}
        text = to_plantuml(nodes)
        self.assertIn('rectangle "A@1.0.0" as N0', text)
        self.assertIn('rectangle "B@2.0.0" as N1', text)


class PlantUmlCliTests(unittest.TestCase):
    """Проверки вывода PlantUML из командной строки"""

    def run_uml(self, name: str):
        """Запустить CLI на заданном тестовом пакете"""
        path = ROOT / f"examples/config_uml_{name.lower()}.csv"
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--config", str(path), "--uml"])
        return code, output.getvalue()

    def test_three_packages(self):
        """Диаграммы строятся для трёх разных пакетов"""
        for name in ("A", "C", "G"):
            with self.subTest(package=name):
                code, text = self.run_uml(name)
                self.assertEqual(code, 0)
                self.assertTrue(text.startswith("@startuml"))
                self.assertIn(f'rectangle "{name}" as N0', text)
                self.assertTrue(text.strip().endswith("@enduml"))

    def test_no_dependencies(self):
        """Пакет G без зависимостей не имеет стрелок"""
        _, text = self.run_uml("G")
        self.assertNotIn("-->", text)

    def test_cycle_output(self):
        """Существующее ребро цикла попадает в PlantUML"""
        path = ROOT / "examples/config_graph_cycle.csv"
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--config", str(path), "--uml"])
        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue().count("-->"), 4)

    def test_filter_depth(self):
        """Режим UML использует прежний DFS с глубиной и фильтром"""
        path = ROOT / "examples/config_graph_filter.csv"
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--config", str(path), "--uml"])
        self.assertEqual(code, 0)
        self.assertNotIn('rectangle "B"', output.getvalue())

    def test_nuget(self):
        """Вывод поддерживает версии из графа NuGet"""
        graph = {"Demo@1.0.0": ["Child@2.0.0"], "Child@2.0.0": []}
        output = io.StringIO()
        path = ROOT / "examples/config_dependencies.csv"
        with patch("src.main.load_graph", return_value=("Demo@1.0.0", graph)):
            with redirect_stdout(output):
                code = main(["--config", str(path), "--uml"])
        self.assertEqual(code, 0)
        self.assertIn('rectangle "Child@2.0.0"', output.getvalue())


if __name__ == "__main__":
    unittest.main()
