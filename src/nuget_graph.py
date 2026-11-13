"""Получение транзитивных зависимостей из NuGet V3"""

import json

from src.nuget import download, normalize_version, package_base, parse_nuspec
from src.versions import select_version


class NugetGraph:
    """Клиент NuGet с кешированием индекса версий и манифестов"""

    def __init__(self, repository: str, excluded: str = ""):
        """Получить адрес репозитория и подготовить кеш"""
        self.repository = repository
        self.base = None
        self.excluded = excluded.casefold()
        self.versions = {}
        self.manifests = {}
        self.names = {}

    def get_base(self) -> str:
        """Получить адрес NuGet при первом обращении"""
        if self.base is None:
            self.base = package_base(self.repository)
        return self.base

    def get_versions(self, name: str) -> list[str]:
        """Получить список опубликованных версий пакета"""
        key = name.lower()
        if key not in self.versions:
            url = f"{self.get_base()}/{key}/index.json"
            try:
                data = json.loads(download(url))
            except (ValueError, UnicodeError) as error:
                raise ValueError(f"ошибка индекса {name}: {error}") from error
            if not isinstance(data, dict):
                raise ValueError(f"неверный индекс версий: {name}")
            items = data.get("versions")
            if not isinstance(items, list) or not items:
                raise ValueError(f"нет списка версий пакета: {name}")
            if not all(isinstance(ver, str) for ver in items):
                raise ValueError(f"неверные версии пакета: {name}")
            self.versions[key] = items
        return self.versions[key]

    def get_groups(self, name: str, version: str) -> list[tuple]:
        """Получить группы зависимостей конкретного пакета"""
        key = name.lower(), normalize_version(version)
        if key not in self.manifests:
            package, ver = key
            url = f"{self.get_base()}/{package}/{ver}/{package}.nuspec"
            self.manifests[key] = parse_nuspec(download(url))
        return self.manifests[key]

    def children(self, node: str) -> list[str]:
        """Получить прямые зависимости со связанными версиями"""
        name, version = node.rsplit("@", 1)
        self.names.setdefault(name.casefold(), name)
        groups = self.get_groups(name, version)
        result = []
        for _, deps in groups:
            for package, spec in deps:
                if self.excluded and self.excluded in package.casefold():
                    continue
                chosen = select_version(self.get_versions(package), spec)
                name = self.names.setdefault(package.casefold(), package)
                result.append(f"{name}@{chosen}")
        return list(dict.fromkeys(result))
