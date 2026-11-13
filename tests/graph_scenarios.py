"""Демонстрация графов DFS и NuGet через настоящий CLI"""

import csv
import json
import os
import subprocess
import sys
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"


def nuspec(deps: str) -> bytes:
    """Сформировать минимальный манифест NuGet"""
    return ("<package><metadata><dependencies>" + deps
            + "</dependencies></metadata></package>").encode()


DATA = {
    "/flat/demo.package/2.1.0/demo.package.nuspec": nuspec(
        '<dependency id="Package.One" version="[1.0.0,2.0.0)" />'
        '<dependency id="Package.Two" version="[3.0.0,)" />'),
    "/flat/package.one/index.json": b'{"versions":["1.0.0","2.0.0"]}',
    "/flat/package.two/index.json": b'{"versions":["3.0.0"]}',
    "/flat/package.common/index.json": b'{"versions":["2.0.0"]}',
    "/flat/demo.package/index.json": b'{"versions":["2.1.0"]}',
    "/flat/package.one/1.0.0/package.one.nuspec": nuspec(
        '<dependency id="Package.Common" version="[2.0.0]" />'),
    "/flat/package.two/3.0.0/package.two.nuspec": nuspec(
        '<dependency id="Package.Common" version="[2.0.0]" />'),
    "/flat/package.common/2.0.0/package.common.nuspec": nuspec(
        '<dependency id="Demo.Package" version="[2.1.0]" />'),
}


class Handler(BaseHTTPRequestHandler):
    """Локальный репозиторий с циклом зависимостей"""

    def do_GET(self):
        """Отдать service index или конкретный документ"""
        if self.path == "/v3/index.json":
            root = f"http://127.0.0.1:{self.server.server_port}"
            index = {"resources": [
                {"@type": "PackageBaseAddress/3.0.0", "@id": root + "/flat"}
            ]}
            data = json.dumps(index).encode()
        else:
            data = DATA.get(self.path)
        if data is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        """Скрыть служебные записи HTTP-сервера"""


def save_config(folder: Path, url: str) -> Path:
    """Создать конфигурацию для локального HTTP-репозитория"""
    path = folder / "config.csv"
    data = {
        "package": "Demo.Package", "repository": url,
        "test_mode": "false", "version": "2.1.0",
        "max_depth": "4", "filter": ""
    }
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["key", "value"])
        writer.writerows(data.items())
    return path


def run_case(name: str, path: Path, expected: str, code: int = 0):
    """Показать команду, вывод и результат проверки"""
    cmd = [sys.executable, str(ROOT / "run.py"), "--config", str(path),
           "--graph"]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", env=env)
    output = result.stdout + result.stderr
    print(f"\n=== {name} ===")
    print(f'Команда: py run.py --config "{path}" --graph')
    print(output.rstrip())
    if result.returncode != code or expected not in output:
        raise AssertionError(f"Ошибка сценария: {name}")
    print("PASS")


def run_nuget():
    """Проверить реальный HTTP и транзитивный граф с циклом"""
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            root = f"http://127.0.0.1:{server.server_port}"
            with tempfile.TemporaryDirectory() as temp:
                path = save_config(Path(temp), root + "/v3/index.json")
                run_case("NuGet через HTTP", path, "Package.Common@2.0.0")
        finally:
            server.shutdown()


def main():
    """Проверить цикл, глубину, фильтр и HTTP"""
    run_case("Циклический граф", EXAMPLES / "config_graph_cycle.csv",
             "C -> A")
    run_case("Максимальная глубина", EXAMPLES / "config_graph_depth.csv",
             "D -> (нет)")
    run_case("Фильтрация узла B", EXAMPLES / "config_graph_filter.csv",
             "A -> C")
    run_case("Основной тестовый граф", EXAMPLES / "config_test.csv",
             "A -> B, C")
    run_nuget()
    print("\nИТОГ: 5 сценариев этапа 3 пройдены")


if __name__ == "__main__":
    main()
