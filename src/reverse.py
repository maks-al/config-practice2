"""Поиск обратных зависимостей через нерекурсивный DFS"""

from src.graph import build_graph, is_filtered

MAX_SINGLE_MATCH = 1


def filter_repo(repo: dict[str, list[str]], text: str) -> dict:
    """Исключить узлы и связи по заданной подстроке"""
    return {
        name: [dep for dep in deps if not is_filtered(dep, text)]
        for name, deps in repo.items() if not is_filtered(name, text)
    }


def invert_graph(graph: dict[str, list[str]]) -> dict:
    """Развернуть рёбра графа в обратную сторону"""
    result = {name: [] for name in graph}
    for name, deps in graph.items():
        for dep in deps:
            result.setdefault(dep, []).append(name)
    return result


def find_target(graph: dict, target: str) -> str:
    """Найти пакет по имени или по имени с версией"""
    name = target.casefold()
    exact = [node for node in graph if node.casefold() == name]
    if exact:
        return exact[0]
    found = [node for node in graph
             if node.partition("@")[0].casefold() == name]
    if not found:
        raise ValueError(f"пакет не найден в графе: {target}")
    if len(found) > MAX_SINGLE_MATCH:
        raise ValueError("несколько версий пакета, укажите имя@версия")
    return found[0]


def reverse_dependencies(graph: dict, target: str, limit: int) -> tuple:
    """Найти прямые и транзитивные обратные зависимости через DFS"""
    node = find_target(graph, target)
    reverse = invert_graph(graph)
    return node, build_graph(node, reverse.__getitem__, limit)
