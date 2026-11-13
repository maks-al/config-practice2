"""Консольный интерфейс анализатора зависимостей"""

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

from src.config import load_config
from src.graph import build_graph, read_test_repo
from src.nuget import direct_dependencies, normalize_version
from src.nuget_graph import NugetGraph

DEFAULT = Path(__file__).resolve().parent.parent / "examples/config_test.csv"


def main(argv: list[str] | None = None) -> int:
    """Прочитать CSV и показать шесть проверенных параметров"""
    parser = argparse.ArgumentParser(description="Анализатор зависимостей")
    parser.add_argument("--config", default=DEFAULT, help="путь к CSV")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--deps", action="store_true",
                      help="показать прямые зависимости NuGet")
    mode.add_argument("--graph", action="store_true",
                      help="построить граф зависимостей DFS")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        if args.deps:
            show_dependencies(config)
            return 0
        if args.graph:
            show_graph(config, args.config)
            return 0
    except ValueError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1

    for key, value in asdict(config).items():
        text = str(value).lower() if isinstance(value, bool) else value
        print(f"{key}: {text}")
    return 0


def show_dependencies(config) -> None:
    """Вывести прямые зависимости пакета по целевым платформам"""
    if config.test_mode:
        raise ValueError("--deps требует test_mode=false")
    groups = direct_dependencies(
        config.repository, config.package, config.version
    )
    print(f"Пакет: {config.package} {config.version}")
    print("Прямые зависимости:")
    for framework, items in groups:
        print(f"  {framework}:")
        if not items:
            print("    нет")
        for name, version in items:
            print(f"    {name}: {version}")


def show_graph(config, filename) -> None:
    """Построить и вывести граф зависимостей с учётом настроек"""
    if config.test_mode:
        folder = Path(filename).expanduser().resolve().parent
        repo = read_test_repo(folder / config.repository)
        if config.package not in repo:
            raise ValueError(f"в тестовом графе нет узла: {config.package}")
        root = config.package
        children = repo.__getitem__
    else:
        source = NugetGraph(config.repository, config.filter)
        root = f"{config.package}@{normalize_version(config.version)}"
        children = source.children
    graph = build_graph(root, children, config.max_depth, config.filter)
    print(f"Граф зависимостей: {root}")
    for name, deps in graph.items():
        print(f"{name} -> {', '.join(deps) if deps else '(нет)'}")


if __name__ == "__main__":
    raise SystemExit(main())
