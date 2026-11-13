"""Показательные запуски CLI с печатью команд и результатов."""

import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
EXIT_OK = 0
DATA = {
    "package": "A", "repository": "test_repo.txt", "test_mode": "true",
    "version": "1.0.0", "max_depth": "3", "filter": ""
}


def run_case(name, config, success, expected):
    """Проверить вывод и код завершения отдельного процесса."""
    cmd = [sys.executable, str(ROOT / "run.py"), "--config", str(config)]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", env=env
    )
    output = result.stdout + result.stderr
    print(f"\n=== {name} ===", flush=True)
    print(f'Команда: py run.py --config "{config}"', flush=True)
    print(output.rstrip() or "(пустой вывод)", flush=True)
    valid_code = (result.returncode == EXIT_OK) == success
    if not valid_code or expected not in output:
        raise AssertionError(f"Проверка не пройдена: {name}")
    print("PASS", flush=True)


def save_config(folder, name, key, value):
    """Создать временный CSV с ошибочным значением одного поля."""
    data = dict(DATA)
    (folder / "test_repo.txt").write_text("A: B\nB:\n", encoding="utf-8")
    data[key] = value
    path = folder / f"{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["key", "value"])
        writer.writerows(data.items())
    return path


def main():
    """Показать два успешных запуска и ошибки всех шести полей."""
    run_case("Тестовый режим", EXAMPLES / "config_test.csv", True, "A")
    run_case("NuGet URL", EXAMPLES / "config_nuget.csv", True, "13.0.3")
    bad = {
        "package": "a", "repository": "missing.txt", "test_mode": "yes",
        "version": "abc", "max_depth": "-1", "filter": "a\nb"
    }
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        for key, value in bad.items():
            file = save_config(folder, key, key, value)
            run_case(f"Ошибка {key}", file, False, f"{key}:")
    print("\nИТОГ: 8 сценариев пройдены")


if __name__ == "__main__":
    main()
