"""Загрузка тестовых графов и нерекурсивный обход DFS"""

import re
from pathlib import Path
from typing import Callable

TEST_NAME = re.compile(r"[A-Z]+")


def parse_test_line(line: str, number: int) -> tuple:
    """Проверить и разобрать строку тестового графа"""
    name, mark, values = line.partition(":")
    name = name.strip()
    deps = values.split()
    if not mark or not TEST_NAME.fullmatch(name):
        raise ValueError(f"неверный узел в строке {number}")
    if any(not TEST_NAME.fullmatch(dep) for dep in deps):
        raise ValueError(f"неверная зависимость в строке {number}")
    return name, list(dict.fromkeys(deps))


def read_test_repo(path: Path) -> dict[str, list[str]]:
    """Прочитать граф с именами узлов из заглавных латинских букв"""
    graph = {}
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as error:
        raise ValueError(f"не удалось прочитать граф: {error}") from error
    for number, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, deps = parse_test_line(line, number)
        if name in graph:
            raise ValueError(f"повтор узла: {name}")
        graph[name] = deps
    missing = sorted({dep for deps in graph.values() for dep in deps}
                     - graph.keys())
    if missing:
        raise ValueError(f"не описаны узлы: {', '.join(missing)}")
    return graph


def is_filtered(node: str, excluded: str) -> bool:
    """Проверить подстроку в имени пакета без номера версии"""
    name = node.partition("@")[0]
    return bool(excluded) and excluded.casefold() in name.casefold()


def build_graph(root: str, children: Callable, limit: int,
                excluded: str = "") -> dict[str, list[str]]:
    """Собрать граф DFS со стеком и учётом кратчайшей глубины узла"""
    if is_filtered(root, excluded):
        raise ValueError("исходный пакет исключён фильтром")
    graph = {}
    seen = {}
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        if node in seen and seen[node] <= depth:
            continue
        seen[node] = depth
        graph.setdefault(node, [])
        if depth >= limit:
            continue
        deps = list(dict.fromkeys(children(node)))
        deps = [dep for dep in deps if not is_filtered(dep, excluded)]
        graph[node] = deps
        for dep in deps:
            graph.setdefault(dep, [])
        for dep in reversed(deps):
            stack.append((dep, depth + 1))
    return graph
