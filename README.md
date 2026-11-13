# Практическая работа №2 - вариант 1, этапы 1-2

Консольная программа на Python для анализа зависимостей NuGet
На этапе 1 программа проверяет настройки из CSV
На этапе 2 получает прямые зависимости заданной версии пакета по HTTP

## Требования

- Windows, Python 3.10 или новее
- Подключение к интернету для работы с NuGet

## Запуск

Открыть PowerShell в папке проекта и выполнить:

```powershell
py run.py
py run.py --config examples/config_nuget.csv
py run.py --config examples/config_dependencies.csv --deps
```

Без `--deps` выводятся шесть настроек из CSV
С `--deps` выводятся прямые зависимости пакета из NuGet
По умолчанию используется `examples/config_test.csv`

Пример вывода настроек:

```text
package: A
repository: test_repo.txt
test_mode: true
version: 1.0.0
max_depth: 3
filter:
```

Пример результата этапа 2:

```text
Пакет: Demo.Package 2.1.0
Прямые зависимости:
  net6.0:
    Package.One: [1.0.0,2.0.0)
  net8.0:
    Package.Two: [3.0.0,)
```

Этот пример воспроизводится через `py tests/nuget_scenarios.py`

## Формат CSV

Два столбца: `key,value`. Обязательные параметры:

| Ключ | Значение |
|---|---|
| `package` | Имя NuGet-пакета или тестового узла (`A`, `B`...) |
| `repository` | HTTP(S) URL или путь к тестовому файлу |
| `test_mode` | `true` либо `false` |
| `version` | Версия пакета, например `8.0.0` |
| `max_depth` | Неотрицательное целое число |
| `filter` | Подстрока фильтра, может быть пустой |

В тестовом режиме путь `repository` считается относительно CSV-файла
При `--deps` требуется `test_mode=false`
Настройки `max_depth` и `filter` потребуются на этапе 3

## Получение зависимостей

Программа загружает индекс NuGet V3 по адресу `repository`, находит
ресурс `PackageBaseAddress`, запрашивает `.nuspec` нужной версии и
читает элементы `dependency` из XML

Зависимости выводятся отдельно для каждой группы `targetFramework`
Диапазоны версий показываются без изменения и без установки пакетов
Если зависимости отсутствуют, выводится `нет`

## Проверки

```powershell
py -m unittest discover -s tests -v
py tests/scenarios.py
py tests/nuget_scenarios.py
```

Первая команда запускает unit-тесты обоих этапов
Вторая показывает ошибки настройки CSV
Третья запускает локальный HTTP-сервер и проверяет получение зависимостей,
несуществующую версию и ошибки репозитория без доступа к интернету

## Основные функции

| Функция | Назначение |
|---|---|
| `read_rows()` | Считывает ключи и значения CSV |
| `check_mode()` | Проверяет `true/false` |
| `check_package()` | Проверяет имя пакета |
| `check_repository()` | Проверяет URL или путь к файлу |
| `check_version()` | Проверяет версию |
| `check_depth()` | Проверяет глубину |
| `check_filter()` | Проверяет фильтр |
| `load_config()` | Собирает проверенную конфигурацию |
| `download()` | Загружает данные по HTTP |
| `package_base()` | Находит адрес хранилища NuGet |
| `is_base()` | Проверяет тип ресурса NuGet |
| `valid_url()` | Проверяет адрес ресурса |
| `normalize_version()` | Нормализует версию для URL |
| `dependency_items()` | Извлекает зависимости из XML-группы |
| `parse_nuspec()` | Разбирает XML-манифест |
| `direct_dependencies()` | Получает прямые зависимости пакета |
| `show_dependencies()` | Выводит зависимости на экран |
| `main()` | Обрабатывает параметры и запускает программу |

## Файлы

- `run.py` - точка входа
- `src/main.py` - CLI и вывод
- `src/config.py` - чтение и проверка CSV
- `src/nuget.py` - загрузка NuGet и чтение `.nuspec`
- `examples/` - конфигурации и тестовый файл
- `tests/test_*.py` - unit-тесты
- `tests/scenarios.py` - проверка первого этапа
- `tests/nuget_scenarios.py` - проверка второго этапа
- `Makefile` - дополнительный запуск, если установлен `make`

## Git

Проект рассчитан на 5 последовательных коммитов, по одному на этап
Второй коммит: `feat(nuget): add direct dependency lookup`
