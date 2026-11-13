"""Чтение и проверка CSV-конфигурации анализатора зависимостей"""

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

CSV_COLUMNS = 2
FIELDS = (
    "package", "repository", "test_mode", "version", "max_depth", "filter"
)
NUGET_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
TEST_NAME = re.compile(r"[A-Z]+")
VERSION = re.compile(r"[0-9]+(?:\.[0-9]+){1,3}(?:-[\w.-]+)?(?:\+[\w.-]+)?")


@dataclass(frozen=True)
class Config:
    """Проверенные параметры, полученные из CSV-файла"""

    package: str
    repository: str
    test_mode: bool
    version: str
    max_depth: int
    filter: str


def read_rows(path: Path) -> dict[str, str]:
    """Прочитать ровно шесть пар ключ-значение из CSV"""
    values = {}
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file, strict=True)
            if next(reader, None) != ["key", "value"]:
                raise ValueError("CSV должен начинаться с key,value")
            for row in reader:
                if len(row) != CSV_COLUMNS:
                    raise ValueError("в каждой строке CSV должно быть 2 поля")
                key, value = row[0].strip(), row[1].strip()
                if key not in FIELDS:
                    raise ValueError(f"неизвестный параметр: {key}")
                if key in values:
                    raise ValueError(f"повтор параметра: {key}")
                values[key] = value
    except (OSError, csv.Error) as error:
        raise ValueError(f"не удалось прочитать CSV: {error}") from error
    missing = [key for key in FIELDS if key not in values]
    if missing:
        raise ValueError(f"отсутствуют параметры: {', '.join(missing)}")
    return values


def check_mode(value: str) -> bool:
    """Преобразовать текст true/false в логическое значение"""
    if value.lower() not in ("true", "false"):
        raise ValueError("test_mode: допустимы только true и false")
    return value.lower() == "true"


def check_package(value: str, test_mode: bool) -> str:
    """Проверить имя NuGet-пакета или тестового узла"""
    pattern = TEST_NAME if test_mode else NUGET_NAME
    if not pattern.fullmatch(value):
        raise ValueError("package: неверное имя пакета")
    return value


def check_repository(value: str, test_mode: bool, folder: Path) -> str:
    """Проверить URL или существование локального файла"""
    if not value:
        raise ValueError("repository: не задан адрес или путь")
    if test_mode:
        if not (folder / value).is_file():
            raise ValueError("repository: файл тестового репозитория не найден")
    else:
        try:
            url = urlsplit(value)
        except ValueError as error:
            raise ValueError("repository: неверный URL") from error
        if url.scheme not in ("http", "https") or not url.hostname:
            raise ValueError("repository: требуется URL http(s)")
        if any(char.isspace() for char in value):
            raise ValueError("repository: пробелы в URL недопустимы")
    return value


def check_version(value: str) -> str:
    """Проверить обычную форму номера версии NuGet"""
    if not VERSION.fullmatch(value):
        raise ValueError("version: неверный формат версии")
    return value


def check_depth(value: str) -> int:
    """Проверить неотрицательную целую глубину обхода"""
    if not value.isascii() or not value.isdecimal():
        raise ValueError("max_depth: требуется неотрицательное целое число")
    try:
        return int(value)
    except ValueError as error:
        raise ValueError("max_depth: слишком большое число") from error


def check_filter(value: str) -> str:
    """Разрешить пустую подстроку, но запретить управляющие символы"""
    if any(char in value for char in ("\n", "\r", "\x00")):
        raise ValueError("filter: недопустимый управляющий символ")
    return value


def load_config(path: str | Path) -> Config:
    """Прочитать CSV и получить объект с проверенными параметрами"""
    file = Path(path).expanduser().resolve()
    data = read_rows(file)
    mode = check_mode(data["test_mode"])
    return Config(
        package=check_package(data["package"], mode),
        repository=check_repository(data["repository"], mode, file.parent),
        test_mode=mode,
        version=check_version(data["version"]),
        max_depth=check_depth(data["max_depth"]),
        filter=check_filter(data["filter"]),
    )
