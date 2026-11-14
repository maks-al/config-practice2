# Практическая работа №2 - Вариант 1

Консольная программа на Python для анализа зависимостей пакетов NuGet
Этап 1 - загрузка и проверка настроек из CSV
Этап 2 - получение прямых зависимостей пакета по HTTP
Этап 3 - построение графа зависимостей алгоритмом DFS без рекурсии
Этап 4 - поиск прямых и транзитивных обратных зависимостей
Этап 5 - вывод графов PlantUML и сравнение с .NET

## Требования

- Windows, Python 3.10 или новее
- Интернет соединение для работы с репозиторием NuGet
- .NET SDK 8.0.4xx или новее, нужен только для сравнения

## Запуск

Открыть PowerShell в папке проекта и выполнить:

```
py run.py
py run.py --config examples/config_dependencies.csv --deps
py run.py --graph
py run.py --config examples/config_graph_cycle.csv --graph
py run.py --config examples/config_graph_depth.csv --graph
py run.py --config examples/config_graph_filter.csv --graph
py run.py --config examples/config_dependencies.csv --graph
py run.py --config examples/config_reverse.csv --reverse
py run.py --reverse D
py run.py --config examples/config_reverse_depth.csv --reverse
py run.py --config examples/config_reverse_filter.csv --reverse
py run.py --config examples/config_dependencies.csv --reverse Microsoft.Extensions.Logging.Abstractions
py run.py --config examples/config_uml_a.csv --uml
py run.py --config examples/config_uml_c.csv --uml
py run.py --config examples/config_uml_g.csv --uml
py run.py --config examples/config_uml_nuget.csv --uml
```

Без ключей программа выводит настройки из `examples/config_test.csv`
`--deps` показывает прямые зависимости NuGet, `--graph` строит граф
`--reverse` показывает обратные зависимости пакета
После `--reverse` можно указать имя пакета или `имя@версия`
Без имени используется параметр `package` из CSV
Режимы `--deps`, `--graph`, `--reverse`, `--uml` взаимоисключающие
`--uml` выводит текст диаграммы, графические файлы не создаются

Пример графа с циклом:

```
Граф зависимостей: A
A -> B, C
B -> C
C -> A
```

Пример графа с ограничением глубины 2:

```
Граф зависимостей: A
A -> B, C
B -> D
C -> F
D -> (нет)
F -> (нет)
```

Пример обратных зависимостей:

```
Обратные зависимости: D
D <- B, C, E
B <- A
C <- A
E <- F
A <- (нет)
F <- (нет)
```

## Формат CSV

Первый ряд: `key,value`, затем 6 обязательных параметров

| Ключ | Значение |
|---|---|
| `package` | Имя NuGet-пакета или тестового узла (`A`, `B`...) |
| `repository` | HTTP(S) URL или путь к текстовому графу |
| `test_mode` | `true` либо `false` |
| `version` | Версия исходного пакета, например `8.0.0` |
| `max_depth` | Максимальная глубина DFS |
| `filter` | Подстрока для исключения пакетов, может быть пустой |

В тестовом режиме путь `repository` считается относительно CSV-файла
При `test_mode=true` имена узлов состоят из заглавных латинских букв
Если фильтр исключает исходный пакет, программа сообщает об ошибке

## Тестовый репозиторий

Файл описывает узлы и их прямые зависимости:

```
A: B C
B: D
C: D
D:
```

Можно использовать циклы и общие зависимости
Пустое значение после `:` означает отсутствие зависимостей
Пустые строки и строки, начинающиеся с `#`, пропускаются
Все упоминаемые узлы должны быть описаны в файле

## Построение графа

DFS использует стек, без рекурсивных вызовов
`max_depth=0` оставляет только исходный пакет
Фильтр исключает пакет вместе с его исходящими зависимостями
Повторные пути и циклы не приводят к бесконечному обходу

В режиме NuGet программа запрашивает список доступных версий каждой
зависимости и выбирает минимальную подходящую стабильную версию
При наличии prerelease в диапазоне учитываются предварительные версии
Диапазоны берутся из `.nuspec`, загрузка выполняется через NuGet V3
Зависимости разных `targetFramework` объединяются в один граф

## Обратные зависимости

`D <- B, C` означает, что пакеты B и C зависят от D
Поиск выполняется через обратные рёбра и нерекурсивный DFS
`max_depth` ограничивает число переходов от выбранного пакета
`filter` исключает узлы и связи с ними
Циклы не вызывают бесконечного обхода

В тестовом режиме проверяется весь граф из файла, включая отдельные ветви
В режиме NuGet анализируются пакеты из графа, построенного от `package`
NuGet не предоставляет полный список всех пакетов, зависящих от заданного

## PlantUML

Каждый пакет отображается прямоугольником, зависимость стрелкой
Сохранены исходные направления рёбер, общие узлы и циклы
Текст начинается с `@startuml` и заканчивается `@enduml`
В тестах демонстрируются три разных пакета: `A`, `C`, `G`

Пример:

```
@startuml
left to right direction
rectangle "A" as N0
rectangle "B" as N1
N0 --> N1
@enduml
```

Для отображения диаграммы текст можно вставить в редактор PlantUML
Программа выводит только описание, как указано в задании

## Сравнение с NuGet

```
py scripts/compare_dotnet.py
```

Требуются .NET SDK и доступ к `https://api.nuget.org/v3/index.json`
Скрипт создаёт временные `.csproj` для трёх настоящих NuGet-пакетов
Затем запускает `dotnet restore`, `dotnet list package --include-transitive`
и `dotnet nuget why`, сопоставляя пакеты и разрешённые версии

Наш граф объединяет зависимости разных .NET-платформ и ограничен глубиной
Штатный NuGet учитывает платформу `net8.0` и разрешает конфликты версий
Поэтому количество пакетов, версии и связи могут различаться
Временные файлы создаются вне репозитория и автоматически удаляются

## Проверки

```
py -m unittest discover -s tests -v
py tests/scenarios.py
py tests/nuget_scenarios.py
py tests/graph_scenarios.py
py tests/reverse_scenarios.py
py tests/uml_scenarios.py
```

Первая команда запускает unit-тесты всех пяти этапов
Остальные показывают команды, результаты и ошибки в консоли
Проверка NuGet работает с локальным HTTP-сервером без внешнего интернета

## Основные функции

| Функция | Назначение |
|---|---|
| `read_rows()` | Чтение CSV |
| `check_mode()` | Проверка `test_mode` |
| `check_package()` | Проверка имени пакета |
| `check_repository()` | Проверка адреса или пути |
| `check_version()` | Проверка версии |
| `check_depth()` | Проверка глубины |
| `check_filter()` | Проверка фильтра |
| `load_config()` | Загрузка конфигурации |
| `download()` | HTTP-запрос |
| `package_base()` | Поиск NuGet `PackageBaseAddress` |
| `is_base()` | Проверка типа ресурса |
| `valid_url()` | Проверка URL ресурса |
| `normalize_version()` | Подготовка версии для URL |
| `dependency_items()` | Чтение зависимостей из XML |
| `parse_nuspec()` | Разбор XML-манифеста |
| `direct_dependencies()` | Получение прямых зависимостей |
| `parse_test_line()` | Проверка строки тестового графа |
| `read_test_repo()` | Загрузка текстового графа |
| `is_filtered()` | Проверка подстроки в имени |
| `build_graph()` | Нерекурсивный DFS |
| `version_key()` | Сортировка версий NuGet |
| `pre_part()` | Сравнение prerelease-меток |
| `parse_bounds()` | Разбор границ диапазона |
| `range_bounds()` | Проверка диапазона |
| `in_range()` | Проверка версии в диапазоне |
| `select_version()` | Выбор доступной версии |
| `NugetGraph.get_base()` | Получение адреса NuGet |
| `NugetGraph.get_versions()` | Получение списка версий |
| `NugetGraph.get_groups()` | Получение зависимостей пакета |
| `NugetGraph.children()` | Получение дочерних узлов |
| `show_dependencies()` | Вывод прямых зависимостей |
| `show_graph()` | Вывод графа |
| `filter_repo()` | Фильтрация тестового репозитория |
| `invert_graph()` | Построение обратных связей |
| `find_target()` | Поиск выбранного узла |
| `reverse_dependencies()` | Обратный DFS |
| `load_graph()` | Загрузка графа NuGet или файла |
| `show_reverse()` | Вывод обратных зависимостей |
| `to_plantuml()` | Построение описания PlantUML |
| `show_uml()` | Вывод диаграммы |
| `make_project()` | Временный проект .NET |
| `run_tool()` | Запуск команды .NET |
| `read_packages()` | Чтение штатного списка пакетов |
| `read_graph()` | Чтение пакетов учебного графа |
| `read_assets()` | Чтение связей из assets.json |
| `show_edges()` | Сравнение рёбер |
| `show_diff()` | Сравнение имён и версий |
| `compare_one()` | Сравнение одного NuGet-пакета |
| `main()` | Обработка параметров CLI |

## Файлы

- `run.py` - запуск программы
- `src/config.py` - работа с CSV
- `src/main.py` - интерфейс командной строки
- `src/nuget.py` - NuGet API и XML
- `src/graph.py` - тестовые графы и DFS
- `src/reverse.py` - обратные связи и обход
- `src/versions.py` - версии и диапазоны NuGet
- `src/nuget_graph.py` - загрузка транзитивных зависимостей NuGet
- `src/uml.py` - формирование текста PlantUML
- `scripts/compare_dotnet.py` - сравнение со штатным NuGet
- `examples/` - конфигурации и тестовые графы
- `tests/` - unit-тесты и демонстрационные сценарии этапов 1-5
- `Makefile` - дополнительный способ запуска при наличии `make`