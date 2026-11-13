"""Проверки выбора опубликованной версии по диапазону NuGet"""

import unittest

from src.versions import in_range, range_bounds, select_version, version_key


class VersionTests(unittest.TestCase):
    """Проверки границ диапазонов и сортировки версий"""

    def test_normalization_comparison(self):
        """Незначащие нули не изменяют порядок версий"""
        self.assertEqual(version_key("1.2"), version_key("1.2.0"))
        self.assertLess(version_key("1.2"), version_key("1.2.1"))

    def test_range_inclusive(self):
        """Проверять включённые и исключённые границы"""
        bounds = range_bounds("[1.0.0,2.0.0)")
        self.assertTrue(in_range("1.0.0", bounds))
        self.assertTrue(in_range("1.9.0", bounds))
        self.assertFalse(in_range("2.0.0", bounds))

    def test_single_exact(self):
        """Форма в квадратных скобках означает точную версию"""
        bounds = range_bounds("[2.0.0]")
        self.assertTrue(in_range("2.0.0", bounds))
        self.assertFalse(in_range("2.0.1", bounds))

    def test_single_minimum(self):
        """Обычная версия задаёт нижнюю границу"""
        bounds = range_bounds("1.2.0")
        self.assertTrue(in_range("1.3.0", bounds))
        self.assertFalse(in_range("1.1.0", bounds))

    def test_open_bounds(self):
        """Интервалы без нижней границы тоже поддерживаются"""
        bounds = range_bounds("(,3.0]")
        self.assertTrue(in_range("2.0", bounds))
        self.assertTrue(in_range("3.0", bounds))
        self.assertFalse(in_range("3.1", bounds))

    def test_lowest_available(self):
        """Из диапазона выбирается минимальная доступная версия"""
        items = ["2.0.0", "1.5.0", "1.0.0"]
        self.assertEqual(select_version(items, "[1.1.0,2.0.0)"), "1.5.0")

    def test_prerelease_order(self):
        """Prerelease меньше соответствующего стабильного релиза"""
        self.assertLess(version_key("2.0.0-rc.2"), version_key("2.0.0"))
        self.assertLess(version_key("2.0.0-rc.2"),
                        version_key("2.0.0-rc.10"))

    def test_stable_priority(self):
        """Без явного prerelease предпочтительны стабильные версии"""
        items = ["2.0.0-beta", "2.1.0", "3.0.0"]
        self.assertEqual(select_version(items, "2.0"), "2.1.0")

    def test_invalid_range(self):
        """Неверный диапазон вызывает ошибку"""
        with self.assertRaisesRegex(ValueError, "диапазон"):
            select_version(["1.0.0"], "(1.0.0)")

    def test_no_versions(self):
        """Отсутствие подходящей версии не скрывается"""
        with self.assertRaisesRegex(ValueError, "нет доступных"):
            select_version(["1.0.0"], "[2.0.0]")


if __name__ == "__main__":
    unittest.main()
