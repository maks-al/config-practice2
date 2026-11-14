"""Демонстрация трёх пакетов и диаграмм PlantUML"""

import os
from functools import partial
import subprocess
import sys
import tempfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from graph_scenarios import Handler, save_config, save_repo

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
EXIT_OK = 0


def run_case(name: str, path: Path, expected: str) -> None:
    """Запустить CLI и показать диаграмму с проверкой результата"""
    cmd = [sys.executable, str(ROOT / "run.py"),
           "--config", str(path), "--uml"]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", env=env)
    print(f"\n=== {name} ===")
    print(f'Команда: py run.py --config "{path}" --uml')
    print((result.stdout + result.stderr).rstrip())
    valid = result.returncode == EXIT_OK
    valid = valid and expected in result.stdout
    valid = valid and result.stdout.strip().endswith("@enduml")
    if not valid:
        raise AssertionError(f"Ошибка сценария: {name}")
    print("PASS")


def run_nuget() -> None:
    """Проверить диаграмму с настоящими HTTP-запросами к NuGet"""
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        handler = partial(Handler, directory=temp)
        with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
            root = f"http://127.0.0.1:{server.server_port}"
            save_repo(folder, root)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                path = save_config(folder, root + "/v3/index.json")
                run_case("NuGet через HTTP", path, '"Package.Common@2.0.0"')
            finally:
                server.shutdown()


def main() -> None:
    """Показать три исходных пакета, цикл и локальный NuGet"""
    for name in ("A", "C", "G"):
        path = EXAMPLES / f"config_uml_{name.lower()}.csv"
        run_case(f"Пакет {name}", path, f'"{name}"')
    run_case("Циклический граф", EXAMPLES / "config_graph_cycle.csv",
             '"C"')
    run_nuget()
    print("\nИТОГ: 5 сценариев этапа 5 пройдены")


if __name__ == "__main__":
    main()
