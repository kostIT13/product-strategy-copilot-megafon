# Агент продуктовой стратегии

Переносимый CLI и набор файловых артефактов для подготовки проверяемых продуктовых и коммуникационных стратегий. План MVP находится в [едином плане](docs/solution_plans/plan-main.md); краткий план основной разработки — в [roadmap полного решения](docs/solution_plans/roadmap-full-solution.md).

GitHub CI проверяет frozen-установку по `uv.lock`, unittest/Ruff, PostgreSQL/FastMCP smoke, локальные Markdown-ссылки и секреты в истории. Отдельный demo workflow воспроизводит синтетические артефакты без внешней модели. Состав матрицы и локальный повтор — [docs/continuous-integration.md](docs/continuous-integration.md).

Сборка проверяемого ZIP, wheel/sdist и Docker smoke описана в [docs/distribution.md](docs/distribution.md). Теговый release workflow готовит draft после CI и проверки установки.

Работа IDE-агента: [инструкции и запуск R1](docs/ide-instructions.md), канон — [AGENTS.md](AGENTS.md). После создания/открытия кейса команда `psa context ID` выдаёт подходящие skills и knowledge с версиями/хэшами; загрузка в конкретной IDE проверяется отдельно.

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

`init` создаёт папку `projects/<project-id>` с версионируемым `state.json`, шаблоном брифа и пустыми журналами. Исходные материалы в `projects/*/sources/` исключены из Git по умолчанию. Теперь начальный набор готовится отдельно, проверяется по hash receipt и публикуется целиком; занятая папка не дополняется. После сбоя: `psa workspace pending ID`, затем явный `psa workspace recover ID --operation UUID`. [Файловый контракт и границы восстановления](docs/file-core.md).

`psa doctor` проверяет версию Python, встроенные шаблоны, наличие `uv` и optional FastMCP. Конфигурацию он проверяет только по наличию файла и имён известных переменных: значения из `.env` и окружения не читаются и не выводятся. Состояние проекта меняют явные операции `gate`, `mode` и append-only команды записи; `status`, `next` и `resume` его читают.

Типизированный черновик плана от IDE-агента: `psa artifact status ID`, затем `psa artifact record ID --input FILE.json`. Новый файловый журнал связывает JSON/Markdown/event/receipt через atomic HEAD, проверяет expected_version и входные hashes, поддерживает replay/recovery. Это draft без gate/публикации; [контракт и ограничения совместимости](docs/research-artifacts.md).

Gate сохраняет state/events через write-ahead bundle. При прерывании: `psa workflow pending ID`, затем `psa workflow recover ID --operation UUID`; до восстановления обычные команды блокируются. Для exact retry approval передавайте собственный `--operation UUID` и при необходимости `--expected-workflow-version N`. [Протокол, CLI/MCP и границы recovery](docs/workflow-recovery.md).

Файловые читатели и writers используют [общий lock кейса](docs/case-access.md). При занятой операции CLI/MCP возвращают `busy`; автоматического повтора нет. Вложенные core-вызовы используют один scope. Это защищает от участвующих конкурентных операций; crash recovery остальных legacy writes ещё переносится.

Смена режима исследования также использует workflow recovery: `psa mode set ID quick_scan --by OWNER --operation UUID --expected-workflow-version N`. Общую версию workflow показывает `psa status ID`. Смена режима не утверждает этап; [контракт и совместимость](docs/file-mode-recovery.md).

`psa revisit resolve` сохраняет review ревизии источника с теми же `--operation`/`--expected-workflow-version` и workflow recovery. Проверяются current/archive hashes и все затронутые claims/решения; review не меняет этап или approvals. [Контракт](docs/revision-review-recovery.md).

`psa source add/fetch` также используют workflow recovery для registry/current text/archive/revision. Передавайте `--operation UUID` для exact replay без нового чтения файла/HTTP и `--expected-workflow-version N` для проверки версии. [Source import/recovery](docs/source-import-recovery.md).

`psa render` и `--adopt-existing` публикуют Markdown/manifest через workflow recovery. Существующие drafts сохраняются, changed generated files требуют явного разрешения на discard. Поддерживаются те же UUID/expected version; [контракт render/adoption](docs/render-recovery.md).

Canonical add-команды claims/gaps/options/decisions/capabilities и usage также используют workflow recovery. Для обычных записей задавайте `--operation UUID`, для usage — `--journal-operation UUID`; usage `--operation-id` остаётся ID учтённого вызова и защищает от двойного учёта. [Ledger/usage contract](docs/ledger-recovery.md).

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

Первый агентный проход по импортированным источникам: `psa-main agent analyze demo --question "Что известно об экспорте?" --query "экспорт" --dry-run`. Клиент использует LiteLLM и OpenAI-совместимый endpoint; Qwen задаётся именем модели через `LLM_MODEL`, адрес и ключ — через `LLM_BASE_URL` и `LLM_API_KEY`. [Настройка модели, вызов и аудит черновиков](docs/agent-analysis.md).

Для основной PostgreSQL-системы добавлен отдельный FastMCP stdio-сервер `psa-main-mcp`: поиск, подготовка запроса, анализ и просмотр запуска. [Запуск, границы инструментов и проверка CLI/MCP](docs/main-mcp.md).

При ошибке модельного API смотрите сохранённый `error_code` запуска: [диагностика провайдера](docs/model-provider-diagnostics.md). Имя модели должно точно совпадать с ID настроенного сервера.

Для выполнения с контрольными точками: `psa-main pipeline start demo --question "Что известно об экспорте?" --query "экспорт"`, затем `pipeline resume ... --expected-version N`. [Состояния, восстановление и границы повторных вызовов](docs/agent-pipeline.md).

Для черновиков фактов, гипотез и пробелов используйте `--task evidence_extraction` в agent analyze или pipeline start. [Схемы, цитаты и границы извлечения](docs/evidence-extraction.md).

Для отдельной проверки сохранённого run: `psa-main critic prepare demo RUN_UUID`, затем `critic start` и обычный pipeline resume. [Critic, оценки и привязка к исходному черновику](docs/agent-critic.md).

Для трёх стратегических альтернатив и качественного сравнения: `--task strategy_options` в agent analyze / pipeline start. [Поля вариантов, critic и человеческий выбор](docs/strategy-options.md).

Явная загрузка веб-страницы: `psa-main web import demo https://example.com/`. [HTTP-политика и provenance](docs/web-import.md).

Поиск по актуальным ревизиям источников: `psa-main search demo "retention" --json`. [Описание и ограничения поиска](docs/source-search.md).

Основной файловый путь: `psa source add ID PATH` поддерживает PDF/DOCX/XLSX с optional documents parsers, сохранением ограничений и проверкой цитат по странице/ячейке. [Инструкция](docs/file-document-import.md). [План вывода legacy](docs/legacy-retirement.md). Веб-загрузка `psa source fetch ID URL` использует public-HTTP policy, pinned transport и сохраняет provenance: [правила и ограничения](docs/file-web-import.md).

Legacy: импорт TXT/Markdown/CSV/JSON, статического HTML, DOCX, PDF и XLSX через `psa-main document import`: [инструкция](docs/document-import.md). Для локального DOCX/PDF/XLSX установите `python -m pip install -e ".[documents]"`; Docker-образ уже включает парсер.

Ручное резервирование и восстановление в новую БД: [инструкция backup/restore](docs/postgres-backup.md).

Скопируйте `.env.example` в `.env` и задайте локальные значения. `.env` исключён из Git. Запустите базу командой `docker compose up -d postgres`, затем установите пакет командой `python -m pip install -e .` и примените миграции `alembic upgrade head`. Новые миграции создавайте через `alembic revision --autogenerate -m "описание изменения"` и обязательно просматривайте сгенерированный diff.

Для применения миграций через контейнер используйте `docker compose --profile tools run --build --rm migrate`. Для CLI — `docker compose --profile app run --build --rm app psa-main --help`. Образ включает Alembic и миграции; `.dockerignore` исключает секреты и локальные данные из контекста сборки. Локальный Python подключается к `localhost`, контейнеры — к сервису `postgres`; Compose подставляет внутренний URL автоматически. Порт БД опубликован только на `127.0.0.1`.

После применения миграций сквозной сценарий запускается командой `docker compose --profile app run --build --rm app python scripts/smoke_main.py`. Он создаёт отдельный синтетический проект с уникальным ключом, проверяет повторную регистрацию источника, сохранность ревизий, отказ при неверной цитате и блокировки workflow, затем проходит до `completed`. Проект остаётся в development-БД для просмотра; ключ выводится в начале и в итоговом JSON.

Проверки конкуренции и транзакций: `docker compose --profile app run --build --rm app python scripts/smoke_integrity.py`. Четыре потока одновременно регистрируют источники и подтверждают один переход; затем проверяются ссылки между проектами и откат родительских/дочерних записей при ошибке. Сценарий оставляет два синтетических проекта с уникальными ключами для аудита. Эти сценарии предназначены для development-БД.

PostgreSQL CLI основной системы предоставляет `psa-main project create --key demo --name "Demo project"` и `psa-main project show demo`. Для добавления уже извлечённого UTF-8 текста в реестр источников используйте `psa-main source add demo .\research.txt --uri https://example.org/research --kind web_page`, для просмотра реестра — `psa-main source list demo`. Один и тот же URI с тем же содержимым регистрируется идемпотентно; изменённый текст сохраняется новой неизменяемой ревизией. Команда source add принимает уже извлечённый текст; для файловых форматов используйте document import. Для явной загрузки URL используйте web import.

`psa` остаётся файловым CLI MVP; новая команда `psa-main` работает через PostgreSQL. Dockerfile собирает пакет, а named volume сохраняет локальные данные PostgreSQL.

Реестр возможностей доступен командами `psa-main capability add demo --key CAP-01 --name "Экспорт отчёта" --status available --claim CLAIM_UUID` и `psa-main capability list demo`. Статус `available` требует связанный активный factual claim, а значит и проверенную цитату; `planned` и `unavailable` можно регистрировать без такого подтверждения.

Workflow основной системы запускается отдельно для проекта: `psa-main workflow start demo --by "Владелец проекта"`, текущее состояние — `psa-main workflow status demo`, подтверждённый переход — `psa-main workflow advance demo --expected-version 1 --approved-by "Владелец проекта" --reason "Этап проверен"`, история — `psa-main workflow events demo`. Переходы последовательны и требуют автора, причину и версию из последнего проверенного `workflow status`. Устаревшая версия отклоняется; после проверки нового состояния номер нужно обновить. Гейты проверяют наличие источника, активного фактического утверждения, трёх вариантов и решения на соответствующих этапах. Проверки содержимого брифа, плана исследования и validation plan ещё не подключены к PostgreSQL workflow.

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

Явное сохранение проверенных AI-вариантов и человеческого решения, без автоматических claims/approvals: [docs/strategy-selection.md](docs/strategy-selection.md).

Продуктовая стратегия, внутренние коммуникационные гипотезы и эксперименты по сохранённому решению: [docs/strategy-plan.md](docs/strategy-plan.md).

Явное человеческое принятие конкретной стратегии для внутреннего review и экспорт Markdown/JSON с SHA-256: [docs/strategy-approval.md](docs/strategy-approval.md). Нужна миграция `0017_strategy_approvals`; это не разрешение публикации или клиентских обещаний.

Проверка формулировок IDE-агента по доступным возможностям и доказательствам без модели: [docs/promise-check.md](docs/promise-check.md). Команда `psa-main promise check PROJECT --input promises.json` возвращает blockers или пакет для человеческого review; публикацию не разрешает.

Методики и чек-листы для ручной проверки сценария: [knowledge/README.md](knowledge/README.md). Источники, версии и ограничения указаны в каталоге; загрузка этих материалов работающим агентом ещё не подключена.
