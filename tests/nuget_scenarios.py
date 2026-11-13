"""Проверка HTTP-запросов NuGet и CLI на локальном сервере"""

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
XML = b"""<package xmlns="urn:nuget"><metadata><dependencies>
<group targetFramework="net6.0">
<dependency id="Package.One" version="[1.0.0,2.0.0)" />
</group><group targetFramework="net8.0">
<dependency id="Package.Two" version="[3.0.0,)" />
</group></dependencies></metadata></package>"""


class Handler(BaseHTTPRequestHandler):
    """Простейший тестовый NuGet V3 сервер"""

    def do_GET(self):
        """Отдать индекс NuGet или nuspec"""
        root = f"http://127.0.0.1:{self.server.server_port}"
        index = {"resources": [
            {"@type": "PackageBaseAddress/3.0.0", "@id": root + "/flat"}
        ]}
        data = None
        if self.path == "/v3/index.json":
            data = json.dumps(index).encode("utf-8")
        if self.path == "/flat/demo.package/2.1.0/demo.package.nuspec":
            data = XML
        if data is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        """Не выводить сообщения HTTP-сервера"""


def save_config(folder: Path, url: str, version: str) -> Path:
    """Создать CSV для демонстрационного запуска"""
    path = folder / "config.csv"
    data = {
        "package": "Demo.Package", "repository": url,
        "test_mode": "false", "version": version,
        "max_depth": "3", "filter": ""
    }
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["key", "value"])
        writer.writerows(data.items())
    return path


def run_case(name: str, path: Path, code: int, expected: str):
    """Запустить CLI и проверить код и вывод"""
    cmd = [sys.executable, str(ROOT / "run.py"), "--config", str(path)]
    cmd.append("--deps")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", env=env)
    output = result.stdout + result.stderr
    print(f"\n=== {name} ===")
    print(f'Команда: py run.py --config "{path}" --deps')
    print(output.rstrip())
    if result.returncode != code or expected not in output:
        raise AssertionError(f"Ошибка сценария: {name}")
    print("PASS")


def main():
    """Проверить прямые зависимости и ошибки без внешнего интернета"""
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)
                good = save_config(folder, base + "/v3/index.json", "2.1.0")
                run_case("NuGet и группы платформ", good, 0, "Package.Two")
                bad = save_config(folder, base + "/v3/index.json", "2.1.1")
                run_case("Несуществующая версия", bad, 1, "HTTP 404")
                wrong = save_config(folder, base + "/bad/index.json", "2.1.0")
                run_case("Недоступный индекс", wrong, 1, "HTTP 404")
                sample = ROOT / "examples/config_test.csv"
                run_case("Тестовый режим", sample, 1, "test_mode=false")
        finally:
            server.shutdown()
    print("\nИТОГ: 4 сценария этапа 2 пройдены")


if __name__ == "__main__":
    main()
