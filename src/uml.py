"""Преобразование графа зависимостей в текст PlantUML"""

import json


def to_plantuml(graph: dict[str, list[str]]) -> str:
    """Создать описание ориентированного графа в PlantUML"""
    nodes = list(dict.fromkeys(
        list(graph) + [dep for deps in graph.values() for dep in deps]
    ))
    names = {name: f"N{index}" for index, name in enumerate(nodes)}
    lines = ["@startuml", "left to right direction"]
    for name in nodes:
        label = json.dumps(name, ensure_ascii=False)
        lines.append(f"rectangle {label} as {names[name]}")
    for name, deps in graph.items():
        for dep in dict.fromkeys(deps):
            lines.append(f"{names[name]} --> {names[dep]}")
    lines.append("@enduml")
    return "\n".join(lines)
