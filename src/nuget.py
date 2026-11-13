"""Получение прямых зависимостей пакетов из NuGet V3 API"""

import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

TIMEOUT = 15
NOT_FOUND = 404
MIN_PARTS = 3
MAX_PARTS = 4
BASE_TYPE = "PackageBaseAddress/3.0.0"


def download(url: str) -> bytes:
    """Загрузить документ из репозитория по HTTP"""
    request = urllib.request.Request(
        url, headers={"User-Agent": "config-practice2/2"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code == NOT_FOUND:
            message = "пакет или версия не найдены (HTTP 404)"
            raise ValueError(message) from error
        raise ValueError(f"ошибка HTTP: {error.code}") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ValueError(f"ошибка соединения: {error}") from error


def package_base(repository: str) -> str:
    """Найти PackageBaseAddress в индексе репозитория"""
    try:
        data = json.loads(download(repository))
    except (ValueError, UnicodeError) as error:
        message = f"не удалось прочитать индекс NuGet: {error}"
        raise ValueError(message) from error
    if not isinstance(data, dict):
        raise ValueError("неверный индекс NuGet")
    resources = data.get("resources")
    if not isinstance(resources, list):
        raise ValueError("в индексе NuGet нет списка resources")
    for item in resources:
        if isinstance(item, dict) and is_base(item.get("@type")):
            url = item.get("@id", "")
            if not valid_url(url):
                raise ValueError("в индексе NuGet неверный адрес ресурса")
            return url.rstrip("/")
    raise ValueError("репозиторий не поддерживает PackageBaseAddress")


def is_base(types: object) -> bool:
    """Проверить тип ресурса в индексе NuGet"""
    if isinstance(types, str):
        return types == BASE_TYPE
    if isinstance(types, list):
        return BASE_TYPE in types
    return False


def valid_url(url: object) -> bool:
    """Проверить HTTP-адрес ресурса репозитория"""
    if not isinstance(url, str):
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and bool(parts.hostname)


def normalize_version(version: str) -> str:
    """Нормализовать номер версии для адреса flat container"""
    version = version.split("+", 1)[0]
    numbers, sep, suffix = version.partition("-")
    parts = [str(int(value)) for value in numbers.split(".")]
    while len(parts) < MIN_PARTS:
        parts.append("0")
    if len(parts) == MAX_PARTS and parts[-1] == "0":
        parts.pop()
    result = ".".join(parts)
    return result + ("-" + suffix.lower() if sep else "")


def dependency_items(node: ET.Element) -> list[tuple[str, str]]:
    """Прочитать имена и диапазоны версий зависимостей"""
    items = []
    for dep in node.findall("{*}dependency"):
        name = dep.get("id", "").strip()
        version = dep.get("version", "").strip()
        if not name or not version:
            raise ValueError("в nuspec зависимость без id или version")
        items.append((name, version))
    return items


def parse_nuspec(data: bytes) -> list[tuple[str, list]]:
    """Разобрать прямые зависимости из XML-манифеста"""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError(f"неверный XML nuspec: {error}") from error
    metadata = root.find("{*}metadata")
    if metadata is None:
        raise ValueError("в nuspec отсутствует metadata")
    deps = metadata.find("{*}dependencies")
    if deps is None:
        return [("общие", [])]
    groups = deps.findall("{*}group")
    if not groups:
        return [("общие", dependency_items(deps))]
    return [
        (group.get("targetFramework") or "общие", dependency_items(group))
        for group in groups
    ]


def direct_dependencies(
    repository: str, package: str, version: str
) -> list[tuple[str, list]]:
    """Загрузить nuspec для конкретной версии пакета"""
    base = package_base(repository)
    name = package.lower()
    ver = normalize_version(version)
    url = f"{base}/{name}/{ver}/{name}.nuspec"
    return parse_nuspec(download(url))
