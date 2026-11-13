"""Консольный интерфейс 1го этапа практической работы №2"""

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

from src.config import load_config

DEFAULT = Path(__file__).resolve().parent.parent / "examples/config_test.csv"


def main(argv: list[str] | None = None) -> int:
    """Прочитать CSV и показать шесть проверенных параметров"""
    parser = argparse.ArgumentParser(description="Анализатор зависимостей")
    parser.add_argument("--config", default=DEFAULT, help="путь к CSV")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ValueError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1

    for key, value in asdict(config).items():
        text = str(value).lower() if isinstance(value, bool) else value
        print(f"{key}: {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
