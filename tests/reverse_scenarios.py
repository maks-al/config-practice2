"""Демонстрация обратных зависимостей через настоящий CLI"""

import os
import subprocess
import sys
import tempfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from graph_scenarios import Handler, save_config

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"


def run_case(name: str, path: Path, target: str, expected: str,
             code: int = 0) -> None:
    """Показать ввод, вывод и проверить ожидаемый результат"""
    cmd = [sys.executable, str(ROOT / "run.py"), "--config", str(path)]
    cmd.extend(["--reverse", target] if target else ["--reverse"])
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", env=env)
    output = result.stdout + result.stderr
    print(f"\n=== {name} ===")
    print(f"Команда: py run.py --config {path} --reverse {target}")
    print(output.rstrip())
    if result.returncode != code or expected not in output:
        raise AssertionError(f"Ошибка сценария: {name}")
    print("PASS")


def run_nuget() -> None:
    """Проверить обратные зависимости через локальный NuGet API"""
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            root = f"http://127.0.0.1:{server.server_port}"
            with tempfile.TemporaryDirectory() as temp:
                path = save_config(Path(temp), root + "/v3/index.json")
                run_case("NuGet через HTTP", path, "Package.Common",
                         "Package.Common@2.0.0 <- Package.One@1.0.0")
        finally:
            server.shutdown()


def main() -> None:
    """Проверить обратный DFS, фильтр, глубину, цикл и HTTP"""
    run_case("Обратные зависимости", EXAMPLES / "config_reverse.csv",
             "", "D <- B, C, E")
    run_case("Ограничение глубины", EXAMPLES / "config_reverse_depth.csv",
             "", "B <- (нет)")
    run_case("Фильтр узла B", EXAMPLES / "config_reverse_filter.csv",
             "", "D <- C, E")
    run_case("Циклический граф", EXAMPLES / "config_graph_cycle.csv",
             "", "A <- C")
    run_case("Неизвестный узел", EXAMPLES / "config_reverse.csv",
             "Z", "не найден", 1)
    run_nuget()
    print("\nИТОГ: 6 сценариев этапа 4 пройдены")


if __name__ == "__main__":
    main()
