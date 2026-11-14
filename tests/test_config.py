"""Проверки CSV и всех параметров первого этапа"""

import csv
import tempfile
import unittest
from pathlib import Path

from src.config import load_config


class ConfigTests(unittest.TestCase):
    """Проверки корректных и ошибочных настроек"""

    def setUp(self):
        """Создать независимый временный тестовый репозиторий"""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        (self.folder / "repo.txt").write_text("A: B\nB:\n", encoding="utf-8")
        self.data = {
            "package": "A", "repository": "repo.txt", "test_mode": "true",
            "version": "1.0.0", "max_depth": "3", "filter": ""
        }

    def save(self, data=None):
        """Записать CSV с заданными значениями полей"""
        path = self.folder / "config.csv"
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["key", "value"])
            writer.writerows((data or self.data).items())
        return path

    def test_test_mode(self):
        """Тестовый режим читает файл относительно CSV"""
        cfg = load_config(self.save())
        self.assertEqual(cfg.package, "A")
        self.assertTrue(cfg.test_mode)
        self.assertEqual(cfg.max_depth, 3)
        self.assertEqual(cfg.filter, "")

    def test_nuget_mode(self):
        """Реальный режим принимает URL и версию NuGet"""
        data = dict(self.data)
        data.update(package="Newtonsoft.Json", test_mode="false")
        data.update(repository="https://api.nuget.org/v3/index.json")
        data.update(version="13.0.3-beta", filter="Microsoft")
        cfg = load_config(self.save(data))
        self.assertFalse(cfg.test_mode)
        self.assertEqual(cfg.filter, "Microsoft")

    def test_invalid_parameters(self):
        """Каждый из шести параметров проходит валидацию"""
        cases = {
            "package": "bad-name", "repository": "missing.txt",
            "test_mode": "maybe", "version": "invalid",
            "max_depth": "-1", "filter": "bad\nvalue"
        }
        for key, value in cases.items():
            with self.subTest(key=key):
                data = dict(self.data)
                data[key] = value
                with self.assertRaisesRegex(ValueError, key):
                    load_config(self.save(data))

    def test_bad_url(self):
        """Режим NuGet отклоняет некорректный адрес"""
        data = dict(self.data)
        data.update(test_mode="false", repository="not-a-url")
        with self.assertRaisesRegex(ValueError, "repository"):
            load_config(self.save(data))

    def test_zero_depth(self):
        """Глубина 0 допустима: только исходный пакет"""
        data = dict(self.data)
        data["max_depth"] = "0"
        self.assertEqual(load_config(self.save(data)).max_depth, 0)

    def test_missing_parameter(self):
        """Пропущенный параметр вызывает ошибку"""
        data = dict(self.data)
        del data["version"]
        with self.assertRaisesRegex(ValueError, "version"):
            load_config(self.save(data))

    def test_unknown_parameter(self):
        """Неизвестный ключ не игнорируется молча"""
        data = dict(self.data)
        data["unused"] = "anything"
        with self.assertRaisesRegex(ValueError, "unused"):
            load_config(self.save(data))

    def test_duplicate_parameter(self):
        """Дублирование ключа запрещено"""
        path = self.save()
        with path.open("a", encoding="utf-8") as file:
            file.write("package,B\n")
        with self.assertRaisesRegex(ValueError, "повтор"):
            load_config(path)

    def test_bad_header(self):
        """Проверяется заголовок CSV: key,value"""
        path = self.folder / "bad.csv"
        path.write_text("name,content\npackage,A\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "key,value"):
            load_config(path)

    def test_missing_file(self):
        """Отсутствующий CSV выдаёт понятную ошибку"""
        with self.assertRaisesRegex(ValueError, "CSV"):
            load_config(self.folder / "absent.csv")

    def test_quoted_csv_value(self):
        """CSV корректно хранит подстроку с запятой"""
        data = dict(self.data)
        data["filter"] = "A,B"
        self.assertEqual(load_config(self.save(data)).filter, "A,B")


if __name__ == "__main__":
    unittest.main()
