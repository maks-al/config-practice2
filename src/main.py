"""Консольный интерфейс 1го этапа практической работы №2"""

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

from src.config import load_config
from src.nuget import direct_dependencies

DEFAULT = Path(__file__).resolve().parent.parent / "examples/config_test.csv"


def main(argv: list[str] | None = None) -> int:
    """Прочитать CSV и показать шесть проверенных параметров"""
    parser = argparse.ArgumentParser(description="Анализатор зависимостей")
    parser.add_argument("--config", default=DEFAULT, help="путь к CSV")
    parser.add_argument(
        "--deps", action="store_true",
        help="показать прямые зависимости NuGet"
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        if args.deps:
            show_dependencies(config)
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


if __name__ == "__main__":
    raise SystemExit(main())
