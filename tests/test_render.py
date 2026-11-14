"""Проверки SVG-диаграмм без сторонних библиотек"""

import tempfile
import unittest
import xml.etree.ElementTree as xml_tree
from pathlib import Path

from src.render import save_svg

SVG = "{http://www.w3.org/2000/svg}"


class SvgTests(unittest.TestCase):
    """Проверки сохранения и структуры SVG"""

    def save(self, graph, root):
        """Создать временную SVG-диаграмму"""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return save_svg(graph, root, temp.name)

    def test_file_created(self):
        """Граф сохраняется в SVG с именем пакета"""
        file = self.save({"A": ["B"], "B": []}, "A")
        self.assertTrue(file.is_file())
        self.assertEqual(file.suffix, ".svg")
        self.assertEqual(file.name, "A.svg")
        self.assertFalse((file.parent / "A.png").exists())

    def test_nodes_and_arrows(self):
        """SVG содержит два прямоугольника и стрелку"""
        file = self.save({"A": ["B"], "B": []}, "A")
        tree = xml_tree.parse(file)
        self.assertEqual(len(tree.findall(f".//{SVG}text")), 2)
        self.assertEqual(len(tree.findall(f".//{SVG}line")), 1)
        self.assertIsNotNone(tree.find(f".//{SVG}marker"))

    def test_cycle(self):
        """Цикл записывается как две направленные связи"""
        file = self.save({"A": ["B"], "B": ["A"]}, "A")
        tree = xml_tree.parse(file)
        self.assertEqual(len(tree.findall(f".//{SVG}line")), 2)

    def test_special_characters(self):
        """Специальные символы не повреждают XML"""
        file = self.save({"A&B": ['C<"D'], 'C<"D': []}, "A&B")
        tree = xml_tree.parse(file)
        text = [node.text for node in tree.findall(f".//{SVG}text")]
        self.assertIn("A&B", text)
        self.assertIn('C<"D', text)

    def test_empty_and_loop(self):
        """Пустой граф и петля создают корректный SVG"""
        empty = self.save({}, "G")
        self.assertEqual(xml_tree.parse(empty).getroot().tag, f"{SVG}svg")
        loop = self.save({"A": ["A"]}, "A")
        self.assertIsNotNone(xml_tree.parse(loop).find(f".//{SVG}path"))

    def test_filename(self):
        """Недопустимые символы заменяются в имени файла"""
        file = self.save({"Demo@1.0": []}, "Demo@1.0")
        self.assertEqual(file.name, "Demo_1.0.svg")


if __name__ == "__main__":
    unittest.main()
