# Агент продуктовой стратегии

Переносимый CLI и набор файловых артефактов для подготовки проверяемых продуктовых и коммуникационных стратегий. План MVP находится в [едином плане](docs/solution_plans/plan-main.md); краткий план основной разработки — в [roadmap полного решения](docs/solution_plans/roadmap-full-solution.md).

## CLI

Требуется Python 3.11 или новее. Из корня репозитория установите пакет в editable-режиме и используйте команду `psa`:

```powershell
python -m pip install -e .
psa doctor
psa --help
psa init demo-retention
psa status demo-retention
psa next demo-retention
psa resume demo-retention
```

`init` создаёт папку `projects/<project-id>` с версионируемым `state.json`, шаблоном брифа и пустыми журналами. Исходные материалы в `projects/*/sources/` исключены из Git по умолчанию.

`psa doctor` проверяет версию Python, встроенные шаблоны, наличие `uv` и optional FastMCP. Конфигурацию он проверяет только по наличию файла и имён известных переменных: значения из `.env` и окружения не читаются и не выводятся. Состояние проекта меняют явные операции `gate`, `mode` и append-only команды записи; `status`, `next` и `resume` его читают.

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

`psa render demo-retention` создаёт `03_evidence.md`, `04_options.md`, `decision.md`, `05_strategy.md` и `06_validation-plan.md`. Для продуктовой, коммуникационной стратегии и плана проверки команда создаёт исходные черновики в `drafts/`; `render` читает их, но не меняет. Сгенерированные Markdown-файлы пересобираются, если их хэши совпадают с манифестом; ручные изменения останавливают перезапись. `psa coverage demo-retention` показывает пропущенные ссылки, метки гипотез/вопросов и неподтверждённые обещания; см. [docs/coverage.md](docs/coverage.md). Защита генерируемых сводок описана в [docs/generated-artifacts.md](docs/generated-artifacts.md).

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

Для первого запуска нужны Python 3.11+ и `python -m pip install -e .`. CLI работает с файловыми проектами; `source fetch` — отдельная команда для явного сетевого импорта. Типизированные настройки из окружения и `.env` описаны в `src/product_strategy_agent/config.py`.

### Docker и PostgreSQL для основной разработки

Скопируйте `.env.example` в `.env` и задайте локальные значения. `.env` исключён из Git. Запустите базу командой `docker compose up -d postgres`, затем установите пакет командой `python -m pip install -e .` и примените миграции `alembic upgrade head`. Новые миграции создавайте через `alembic revision --autogenerate -m "описание изменения"` и обязательно просматривайте сгенерированный diff.

Для применения миграций через контейнер используйте `docker compose --profile tools run --build --rm migrate`. Для CLI — `docker compose --profile app run --build --rm app psa-main --help`. Образ включает Alembic и миграции; `.dockerignore` исключает секреты и локальные данные из контекста сборки. Локальный Python подключается к `localhost`, контейнеры — к сервису `postgres`; Compose подставляет внутренний URL автоматически. Порт БД опубликован только на `127.0.0.1`.

PostgreSQL CLI основной системы предоставляет `psa-main project create --key demo --name "Demo project"` и `psa-main project show demo`. Для добавления уже извлечённого UTF-8 текста в реестр источников используйте `psa-main source add demo .\research.txt --uri https://example.org/research --kind web_page`, для просмотра реестра — `psa-main source list demo`. Один и тот же URI с тем же содержимым регистрируется идемпотентно; изменённый текст сохраняется новой неизменяемой ревизией. На этом шаге CLI принимает именно извлечённый текст; загрузчики URL и парсеры документов будут отдельными адаптерами.

`psa` остаётся файловым CLI MVP; новая команда `psa-main` работает через PostgreSQL. Dockerfile собирает пакет, а named volume сохраняет локальные данные PostgreSQL.

Реестр возможностей доступен командами `psa-main capability add demo --key CAP-01 --name "Экспорт отчёта" --status available --claim CLAIM_UUID` и `psa-main capability list demo`. Статус `available` требует связанный активный factual claim, а значит и проверенную цитату; `planned` и `unavailable` можно регистрировать без такого подтверждения.

Workflow основной системы запускается отдельно для проекта: `psa-main workflow start demo --by "Владелец проекта"`, текущее состояние — `psa-main workflow status demo`, подтверждённый переход — `psa-main workflow advance demo --approved-by "Владелец проекта" --reason "Этап проверен"`, история — `psa-main workflow events demo`. Переходы последовательны и требуют автора с причиной. Гейты проверяют наличие источника, активного фактического утверждения, трёх вариантов и решения на соответствующих этапах. Проверки содержимого брифа, плана исследования и validation plan ещё не подключены к PostgreSQL workflow.

Утверждения основной системы сохраняют ссылку на точную ревизию источника и принимаются только если цитата дословно присутствует в извлечённом тексте. Добавить факт с подтверждением и вывести реестр можно командами `psa-main claim add demo --key C-001 --type fact --text "Описание факта" --confidence medium --evidence SOURCE_UUID 1 "paragraph:1" "точная цитата"` и `psa-main claim list demo`. Для гипотез и прогнозов источник необязателен; тип и уверенность всё равно задаются явно.

Варианты поддерживают ссылки на подтверждающие и оспаривающие claims: `psa-main option add demo --key OPT-A --name "Улучшить текущий продукт" --supports CLAIM_UUID --strength "Низкий срок запуска" --risk "Ограниченный рост"`, затем `psa-main option list demo`. Решение фиксируется отдельно: `psa-main decision add demo --key DEC-001 --selected-option OPTION_UUID --owner "Владелец продукта" --rationale "Основание выбора" --review-trigger "Пересмотреть при падении retention" --claim CLAIM_UUID --reject-option OTHER_OPTION_UUID`; список решений выводится `psa-main decision list demo`. Решения сохраняются как отдельные записи и не перезаписывают предыдущие.

### MCP adapter

MCP integration is optional. Install with `python -m pip install -e ".[mcp]"`, launch `psa-mcp` as a local stdio process, and configure that command in the target host. The adapter uses the standalone FastMCP 4.x framework. See [docs/mcp.md](docs/mcp.md) for available tools and host configuration.

### Пересмотр после изменения источника

Повторный импорт того же источника с новым содержимым сохраняет старую локальную версию и добавляет событие в `events.jsonl`. Команда `psa revisit list <id>` показывает claims и решения, которые нужно проверить; после рассмотрения всех зависимостей можно записать аудит через `psa revisit resolve`.
Подробный порядок и формат аудита описаны в [docs/revisit.md](docs/revisit.md).

### Учёт использования

Добавляйте usage от провайдера без содержимого запросов и сводите его через `psa usage add` / `psa usage report`. Неизвестные данные остаются неизвестными, оценочная и измеренная стоимость показываются отдельно. Подробности: [docs/usage.md](docs/usage.md).

### Режимы глубины

`psa mode show <id>` показывает активный режим, `psa mode set <id> quick_scan|decision_grade|deep_research --by ... --reason ...` переключает глубину с аудитом автора и причины. Режимы не расширяют доступы; правила описаны в [docs/modes.md](docs/modes.md).

## Материалы приёмки MVP

- [Проверка coverage и capability-обещаний](docs/coverage.md).
- [Runbook пересмотра изменённого источника](docs/demo-runbook.md).
- [Приёмка FastMCP-хостов и CLI/MCP parity](docs/mcp-host-acceptance.md).
- [Нейтральный A/B-пакет для независимой оценки](evals/demo/blind-review/reviewer-brief.md); ключ владельца не передавать рецензенту.
- [Шаблон записи равноусловного запуска M6](evals/demo/blind-review/run-record-template.md).
