"""Выбор версии пакета по диапазонам NuGet"""

import re

NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+){0,3}")
SUFFIX = re.compile(r"[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*")


def version_key(value: str) -> tuple:
    """Построить ключ сортировки версий NuGet"""
    text = value.split("+", 1)[0]
    numbers, mark, suffix = text.partition("-")
    if not NUMBER.fullmatch(numbers):
        raise ValueError(f"неверная версия NuGet: {value}")
    if mark and not SUFFIX.fullmatch(suffix):
        raise ValueError(f"неверная версия NuGet: {value}")
    parts = tuple(int(part) for part in numbers.split("."))
    parts += (0,) * (4 - len(parts))
    pre = tuple(pre_part(part) for part in suffix.split(".")) if mark else ()
    return parts, 0 if mark else 1, pre


def pre_part(part: str) -> tuple:
    """Числовые метки prerelease упорядочить раньше текстовых"""
    return (0, int(part)) if part.isdecimal() else (1, part.casefold())


def parse_bounds(spec: str) -> tuple:
    """Разделить нижнюю и верхнюю границы диапазона"""
    body = spec[1:-1]
    if "," in body:
        left, right = body.split(",", 1)
        return left.strip() or None, right.strip() or None
    if spec[0] == "[" and spec[-1] == "]":
        return body, body
    raise ValueError(f"неверный диапазон версий: {spec}")


def range_bounds(spec: str) -> tuple:
    """Прочитать границы обычного диапазона версий NuGet"""
    spec = spec.strip()
    if not spec:
        raise ValueError("пустой диапазон версий NuGet")
    if spec[0] not in "[(":
        version_key(spec)
        return spec, None, True, False
    if spec[-1] not in ")]":
        raise ValueError(f"неверный диапазон версий: {spec}")
    left, right = parse_bounds(spec)
    if left:
        version_key(left)
    if right:
        version_key(right)
    return left, right, spec[0] == "[", spec[-1] == "]"


def in_range(value: str, bounds: tuple) -> bool:
    """Проверить включение версии в заданные границы"""
    low, high, inc_low, inc_high = bounds
    key = version_key(value)
    if low:
        border = version_key(low)
        if key < border or (key == border and not inc_low):
            return False
    if high:
        border = version_key(high)
        if key > border or (key == border and not inc_high):
            return False
    return True


def select_version(versions: list[str], spec: str) -> str:
    """Выбрать минимальную доступную версию из диапазона"""
    bounds = range_bounds(spec)
    items = [ver for ver in versions if in_range(ver, bounds)]
    if "-" not in spec:
        stable = [ver for ver in items if "-" not in ver]
        items = stable
    if not items:
        raise ValueError(f"для диапазона {spec} нет доступных версий")
    return min(items, key=version_key)
