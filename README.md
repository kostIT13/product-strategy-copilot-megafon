# Агент продуктовой стратегии

Переносимый CLI и набор файловых артефактов для подготовки проверяемых продуктовых и коммуникационных стратегий. Текущий MVP развивается по пунктам в [едином плане](docs/solution_plans/plan-main.md).

## CLI

Требуется Python 3.11 или новее. Из корня репозитория установите пакет в editable-режиме и используйте команду `psa`:

```powershell
python -m pip install -e .
psa --help
psa init demo-retention
psa status demo-retention
psa next demo-retention
psa resume demo-retention
```

`init` создаёт папку `projects/<project-id>` с версионируемым `state.json`, шаблоном брифа и пустыми журналами. Исходные материалы в `projects/*/sources/` исключены из Git по умолчанию.

Пока состояние изменяется только при создании проекта. Команды `status`, `next` и `resume` читают сохранённое состояние; следующие этапы MVP добавят управляемые переходы и артефакты.

### Импорт источников

```powershell
psa source add demo-retention .\notes.md
psa source fetch demo-retention https://example.org/research
psa source list demo-retention
```

Поддерживаются текст, Markdown, CSV, JSON и HTML файлы, а также HTML/text веб-страницы до 10 MiB. Для каждой записи сохраняются URI или локальный путь, тип, время загрузки, locator, SHA-256 извлечённого текста и путь к локальной копии. Повторный импорт того же пути или URL обновляет запись. Веб-запрос выполняется только явной командой `source fetch`.

### Утверждения, пробелы и решения

```powershell
psa claim add demo-retention --type fact --text "..." --source S-0123456789AB --locator "paragraph:4" --quote "Точный текст выдержки" --confidence medium
psa gap add demo-retention --question "..." --why-it-matters "..." --method "..." --priority high
psa decision add demo-retention --option "Пилот на одном сегменте" --owner "Владелец решения" --claim C-001 --reject "Оставить как есть" --revisit-when "После 4 недель"
```

Утверждения имеют тип `fact`, `interpretation`, `hypothesis`, `forecast` или `synthetic`. Факт обязан ссылаться на известный источник и locator. Ссылки на источники, противоречащие и замещаемые утверждения, а также основания решения проверяются по реестрам. Все три журнала записываются добавлением новых строк.

### Проверка структуры и цитат

```powershell
psa validate demo-retention
psa verify demo-retention
```

`validate` проверяет версию состояния, основные артефакты, JSONL-синтаксис, уникальность ID и ссылки между утверждениями, источниками и решениями. `verify` пересчитывает SHA-256 сохранённых текстов и сверяет точные цитаты по locator вида `paragraph:4`, `p:4`, `line:4` или `lines:2-8` для диапазона строк таблицы. Неподдерживаемые locator отмечаются как предупреждения и не объявляются проверенными.

Для факта указывайте цитату вместе с каждым источником:

```powershell
psa claim add demo-retention --type fact --text "..." --source S-0123456789AB --locator "paragraph:4" --quote "Точный текст выдержки"
```


### Варианты и сборка результатов

Добавляйте варианты с ролями `status_quo` (оставить как есть), `stop` (закрыть) и `change` (изменить/расширить):

```powershell
psa option add demo-retention --name "Оставить как есть" --role status_quo --description "Сохранить текущий подход"
psa option add demo-retention --name "Закрыть направление" --role stop --description "Прекратить развитие и поддержать текущих пользователей"
psa option add demo-retention --name "Пилот для сегмента A" --role change --description "Проверить новое предложение на ограниченном сегменте" --benefits "Ниже риск" --costs "Команда пилота" --risks "Малый охват"
```

Свяжите решение с выбранным вариантом: `psa decision add ... --option-id O-003`. `psa validate` проверяет наличие минимум трёх вариантов с тремя обязательными ролями, если варианты уже начали записывать.

`psa render demo-retention` создаёт `03_evidence.md`, `04_options.md`, `decision.md`, `05_strategy.md` и `06_validation-plan.md`. Для продуктовой, коммуникационной стратегии и плана проверки команда создаёт исходные черновики в `drafts/`; повторный `render` читает их, но не меняет. Сгенерированные Markdown-файлы пересобираются при каждом запуске.

## Сквозной демо-кейс

В `projects/demo/` лежит полностью синтетический учебный кейс. Он уже прошёл бриф, исследовательский план, источники, обзор доказательств, варианты и учебную рекомендацию. Состояние намеренно сохранено на этапе проверки, чтобы показать продолжение после перерыва:

```powershell
psa resume demo
psa validate demo
psa verify demo
psa gate approve demo --stage validation --by "Имя ответственного" --reason "План проверки согласован"
psa resume demo
```

Все значения и решение в кейсе вымышлены. Они не являются данными о МегаФоне или реальными продуктовыми рекомендациями. Черновики находятся в `projects/demo/drafts/`, а извлечённый текст синтетического источника включён в репозиторий для воспроизводимой локальной проверки.

## Критика и оценка качества

Собрать пакет материалов для независимого рецензента:

```powershell
psa critic-pack demo
```

Результат по умолчанию: `projects/demo/reviews/critic-pack.md`. Рецензент получает задачу, вариант-кандидат, источники и цитаты, варианты, пробелы, стратегии и общую рубрику; он должен самостоятельно оспорить рекомендацию. Ответ critic не добавляется в реестр как факт.

Методика и текущая предварительная оценка находятся в [docs/evaluation](docs/evaluation/README.md) и [evals/demo](evals/demo/comparison.md). Самооценка неслепая и не заменяет независимого рецензента.

Для первого запуска нужны Python 3.11+ и `python -m pip install -e .`. CLI не требует Docker, базы данных или внешнего API для локального процесса; `source fetch` — отдельная команда для явного сетевого импорта. Runtime-пакет использует только стандартную библиотеку Python.

### MCP adapter

MCP integration is optional. Install with `python -m pip install -e ".[mcp]"`, launch `psa-mcp` as a local stdio process, and configure that command in the target host. The adapter uses the standalone FastMCP 4.x framework. See [docs/mcp.md](docs/mcp.md) for available tools and host configuration.

### Пересмотр после изменения источника

Повторный импорт того же источника с новым содержимым сохраняет старую локальную версию и добавляет событие в `events.jsonl`. Команда `psa revisit list <id>` показывает claims и решения, которые нужно проверить; после рассмотрения всех зависимостей можно записать аудит через `psa revisit resolve`.
Подробный порядок и формат аудита описаны в [docs/revisit.md](docs/revisit.md).

### Учёт использования

Добавляйте usage от провайдера без содержимого запросов и сводите его через `psa usage add` / `psa usage report`. Неизвестные данные остаются неизвестными, оценочная и измеренная стоимость показываются отдельно. Подробности: [docs/usage.md](docs/usage.md).

### Режимы глубины

`psa mode show <id>` показывает активный режим, `psa mode set <id> quick_scan|decision_grade|deep_research --by ... --reason ...` переключает глубину с аудитом автора и причины. Режимы не расширяют доступы; правила описаны в [docs/modes.md](docs/modes.md).
