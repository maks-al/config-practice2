"""Сравнение учебного графа со штатными командами .NET"""

import json
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.main import load_graph

TIMEOUT = 180
MAX_EXAMPLES = 12
CASES = (
    "examples/config_nuget.csv",
    "examples/config_dependencies.csv",
    "examples/config_uml_nuget.csv",
)


def make_project(folder: Path, package: str, version: str) -> Path:
    """Создать временный проект .NET 8 с указанным NuGet-пакетом"""
    root = ET.Element("Project", Sdk="Microsoft.NET.Sdk")
    settings = ET.SubElement(root, "PropertyGroup")
    ET.SubElement(settings, "TargetFramework").text = "net8.0"
    items = ET.SubElement(root, "ItemGroup")
    ET.SubElement(items, "PackageReference", Include=package,
                  Version=version)
    path = folder / "Comparison.csproj"
    ET.ElementTree(root).write(path, encoding="utf-8",
                               xml_declaration=True)
    return path


def run_tool(args: list[str], folder: Path) -> str:
    """Выполнить команду .NET и вернуть её консольный вывод"""
    try:
        result = subprocess.run(args, cwd=folder, capture_output=True,
                                text=True, encoding="utf-8",
                                errors="replace", timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"не удалось запустить .NET: {error}") from error
    if result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def read_packages(output: str) -> tuple[dict, list[str]]:
    """Прочитать список разрешённых пакетов из JSON вывода .NET"""
    try:
        data = json.loads(output)
        frames = data["projects"][0]["frameworks"]
        packages = {}
        transitive = []
        for frame in frames:
            for kind in ("topLevelPackages", "transitivePackages"):
                for item in frame.get(kind, []):
                    packages[item["id"].casefold()] = item["resolvedVersion"]
                    if kind == "transitivePackages":
                        transitive.append(item["id"])
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise ValueError("неверный JSON от dotnet list package") from error
    return packages, transitive


def read_graph(config, path: Path) -> tuple[dict, dict]:
    """Получить имена и версии пакетов из учебного графа"""
    _, graph = load_graph(config, path)
    packages = {}
    for node in graph:
        name, _, version = node.partition("@")
        packages.setdefault(name.casefold(), set()).add(version)
    return packages, graph


def read_assets(path: Path) -> dict[str, list[str]]:
    """Прочитать разрешённые рёбра из project.assets.json"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        target = next(items for key, items in data["targets"].items()
                      if key.partition("/")[0] == "net8.0")
        packages = {key.partition("/")[0].casefold():
                    key.replace("/", "@", 1)
                    for key, item in target.items()
                    if item.get("type") == "package"}
        graph = {}
        for name, item in target.items():
            if item.get("type") != "package":
                continue
            deps = item.get("dependencies", {})
            node = name.replace("/", "@", 1)
            graph[node] = [packages[dep.casefold()] for dep in deps
                           if dep.casefold() in packages]
        return graph
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError("не удалось прочитать project.assets.json") from error


def show_edges(ours: dict, actual: dict) -> None:
    """Сравнить направленные связи нашего графа и .NET"""
    left = {(name.casefold(), dep.casefold())
            for name, deps in ours.items() for dep in deps}
    right = {(name.casefold(), dep.casefold())
             for name, deps in actual.items() for dep in deps}
    print(f"Рёбра только у нас: {len(left - right)}")
    print(f"Рёбра только в .NET: {len(right - left)}")
    for name, dep in sorted(left - right)[:MAX_EXAMPLES]:
        print(f"  наш граф: {name} -> {dep}")
    for name, dep in sorted(right - left)[:MAX_EXAMPLES]:
        print(f"  .NET: {name} -> {dep}")


def show_diff(ours: dict, actual: dict) -> None:
    """Сопоставить имена и разрешённые версии пакетов"""
    extra = sorted(ours.keys() - actual.keys())
    missing = sorted(actual.keys() - ours.keys())
    different = sorted(name for name in ours.keys() & actual.keys()
                       if actual[name] not in ours[name])
    print(f"Учебный граф: {len(ours)} имён пакетов")
    print(f"dotnet restore: {len(actual)} имён пакетов")
    for title, names in (("Только у нас", extra),
                         ("Только в .NET", missing),
                         ("Разные версии", different)):
        print(f"{title}: {len(names)}")
        for name in names[:MAX_EXAMPLES]:
            print(f"  {name}")
    if not extra and not missing and not different:
        print("Списки имён и версий совпали")


def compare_one(path: Path) -> None:
    """Сравнить пакет со штатным NuGet и показать дерево dotnet why"""
    config = load_config(path)
    if config.test_mode:
        raise ValueError("сравнение доступно только для настоящего NuGet")
    print(f"\n=== {config.package}@{config.version} ===")
    ours, ours_graph = read_graph(config, path)
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        project = make_project(folder, config.package, config.version)
        run_tool(["dotnet", "restore", str(project), "--source",
                  config.repository, "--verbosity", "quiet"], folder)
        output = run_tool(["dotnet", "list", str(project), "package",
                           "--include-transitive", "--format", "json",
                           "--no-restore"], folder)
        actual, transitive = read_packages(output)
        show_diff(ours, actual)
        show_edges(ours_graph, read_assets(folder / "obj/project.assets.json"))
        if transitive:
            package = sorted(transitive)[0]
            print(f"\nШтатное дерево dotnet nuget why для {package}:")
            tree = run_tool(["dotnet", "nuget", "why", str(project),
                             package, "--framework", "net8.0"], folder)
            print(tree.strip())
    print("Причины различий: TFM, глубина, версия, разрешение конфликтов")


def main() -> int:
    """Запустить сравнение для трёх настоящих NuGet-пакетов"""
    if not shutil.which("dotnet"):
        print("Ошибка: установите .NET SDK 8.0.4xx или новее")
        return 1
    try:
        for case in CASES:
            compare_one(ROOT / case)
    except ValueError as error:
        print(f"Ошибка сравнения: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
