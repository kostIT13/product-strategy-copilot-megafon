# Журнал разработки

Часовой пояс: Asia/Novosibirsk (UTC+07:00). Каждый новый блок фиксируется с началом, окончанием и длительностью. Длительности до создания журнала не замерялись и не восстанавливались.

## Работа до ведения журнала

| Дата и время | Длительность | Что сделано |
|---|---:|---|
| 2026-11-05, файлы около 21:52 | Не замерялась | Создана ветка `codex/mvp-first-slice`, затем переименована в `feature/mvp-first-slice`. Добавлены план MVP, пакет и CLI `psa --help/--version`. |
| 2026-11-05, файлы обновлены около 21:59 | Не замерялась | Реализованы `init/status/next/resume`; импорт источников `source add/fetch/list`, извлечение текста и SHA-256. Пункты 1–3 отмечены готовыми. |
| 2026-11-05, завершено около 22:04 | Не замерялась | Добавлены `claim add`, `gap add`, `decision add`; append-only JSONL и проверка ссылок. Для факта нужны источник и locator. Пункт 4 отмечен готовым. |
| 2026-11-05, завершено около 22:10 | Не замерялась | Добавлены `validate` и `verify`, цитаты и проверки схем, ссылок, хэшей и locator. Пункт 5 отмечен готовым. |

## Замеренные блоки

| Дата | Начало | Окончание | Длительность | Что сделано |
|---|---|---|---:|---|
| 2026-11-05 | 22:01:10 | 22:01:37 | около 27 секунд | Создан `reports/` и журнал; внесена история предыдущей работы. |
| 2026-11-05 | 22:02:26 | 22:04:07 | около 1 мин 41 сек | Реализованы команды утверждений, пробелов и решений; обновлены README и план MVP. |
| 2026-11-05 | 22:05:28 | 22:10:14 | около 4 мин 46 сек | Реализованы проверки структуры и цитат; обновлены README и план MVP. |
| 2026-11-05 | 22:17:37 | 22:23:44 | около 6 мин 7 сек | Добавлены `option add`, обязательные роли вариантов, авторские черновики и `psa render` для пяти итоговых артефактов. Пункт 6 отмечен готовым. |
| 2026-11-05 | 22:28:17 | 22:36:20 | около 8 мин 3 сек | Добавлен `gate approve` с проверками этапов и журналом approvals; исправлены относительные URI и хэширование сохранённых байтов. Создан синтетический кейс `projects/demo`, проведён до validation и возобновлён через `resume`; `validate` и `verify` прошли. Пункт 7 отмечен готовым. |
| 2026-11-05 | 22:41:58 | 22:46:57 | около 4 мин 59 сек | Добавлена команда `critic-pack`, создан пакет рецензирования, baseline prompt/answer и exploratory-сравнение. Оценка явно помечена как неслепая самооценка; слепой независимый review остаётся ограничением. Обновлены инструкции запуска и пункт 8 плана. |
| 2026-11-05 | 22:49:43 | 22:53:32 | около 3 мин 49 сек | Добавлен необязательный stdio MCP-адаптер на SDK v2 с операциями поверх CLI и инструкция подключения. SDK отсутствует в окружении; живой MCP host не подключался. Форматные импортеры и поиск оставлены по реальной потребности. |
| 2026-11-05 | 22:59:29 | 23:06:07 | около 6 мин 38 сек | Добавлены `psa usage add/report`, строгие поля usage, группировка времени/токенов и измеренной/оценочной стоимости; те же операции добавлены в MCP. Обновлены README, MCP-справка и контракт журнала. Изменения закоммичены и запушены. |

| 2026-11-06 | 23:29:00 | 23:31:28 | около 2 мин 28 сек | Обновлены план полной системы и roadmap: PostgreSQL принят как основное хранилище, полнотекстовый поиск — средствами PostgreSQL, миграции/backup/restore и Docker Compose включены в этап хранения. Уточнено, что MVP остаётся файловым; старые альтернативные планы помечены архивными. |

| 2026-11-06 | 23:32:00 | 23:35:00 | около 3 мин | В целевой архитектуре основной системы зафиксирована модульная структура domain/application/adapters/interfaces: отдельные application service modules по ответственности, отдельные persistence/provider/document adapters, тонкие CLI и FastMCP интерфейсы, запрет на общий модуль-комбайн и циклические зависимости. MVP-код не переписывался. |

| 2026-11-06 | 23:35:00 | 23:46:12 | около 11 мин 12 сек | Начат каркас основной разработки: добавлены `.env.example` и игнорируемый локальный `.env` без API-ключей, typed `Settings` на pydantic-settings, Dockerfile и Compose с PostgreSQL 17, healthcheck и persistent volume. Добавлены инструкции в README и зависимости/игнорирование секретов. Compose пока поднимает инфраструктуру; файловый MVP с БД ещё не интегрирован. Тесты не запускались. |

| 2026-11-06 | 23:46:12 | 23:54:32 | около 8 мин 20 сек | Начат первый вертикальный срез основной системы на SQLAlchemy 2/Alembic: добавлены доменная сущность проекта, порт хранения, отдельный ProjectService, PostgreSQL-репозиторий и Alembic initial migration для projects; создан отдельный интерфейс `psa-main project create/show`, MVP-команда `psa` не менялась. Обновлены инструкции запуска и roadmap. Тесты не запускались; выполнены только compileall и git diff --check. |

| 2026-11-06/07 | 23:55:00 | 00:03:00 | около 8 мин | Добавлен отдельный SourceService: сохраняются метаданные источника и неизменяемые извлечённые ревизии с SHA-256; повтор содержимого идемпотентен, изменение создаёт новую версию. Добавлены SQLAlchemy-модели и Alembic migration 0002, команды `psa-main source add/list`, обновлены README и roadmap. URL-fetch и парсеры документов оставлены отдельными будущими адаптерами. Тесты и PostgreSQL-приёмка не запускались. |

| 2026-11-07 | 00:03:00 | 00:07:02 | около 4 мин | По запросу пользователя выполнена штатная инициализация `alembic init alembic`; `env.py`, шаблон и существующие миграции перенесены в корневую `alembic/`, URL/metadata подключены к общему config и SQLAlchemy-моделям. Архитектурный план и инструкции обновлены. |

| 2026-11-07 | 00:07:02 | 00:08:24 | около 1 мин 22 сек | Проверена генерация SQL через `alembic upgrade --sql head`: конфигурация импортирует application package через `%(here)s/src`, обе миграции последовательно дают единственную head-ревизию. К БД не подключались. |

| 2026-11-07 | 00:08:24 | 00:13:43 | около 5 мин 19 сек | Добавлен ClaimService и реестр доказательств: факты требуют цитаты, каждая цитата сверяется с текстом конкретной ревизии источника и ограничивается рамками проекта. Добавлены отдельные SQLAlchemy-модели, миграция 0003 и CLI `psa-main claim add/list`; обновлены README и архитектурный roadmap. Тесты не запускались. |

| 2026-11-07 | 00:13:43 | 00:21:27 | около 7 мин 44 сек | Добавлены отдельные OptionService и DecisionService: варианты связываются с поддерживающими/оспаривающими claims; решения фиксируют выбранный, отклонённые/отложенные варианты, владельца, обоснование, риски, предположения и условие пересмотра. Добавлены PostgreSQL-модели, миграции 0004/0005, CLI-команды и документация. Тесты не запускались; compileall, офлайн-генерация SQL и git diff --check прошли. |

| 2026-11-07 | 00:21:27 | 00:28:12 | около 6 мин 45 сек | Добавлен CapabilityService и PostgreSQL-реестр возможностей с отдельными claim-связями, миграцией 0006 и CLI `psa-main capability add/list`. Статус `available` требует активный factual claim, ранее проверенный ClaimService. Обновлены README и архитектурный roadmap. Тесты не запускались; compileall, офлайн SQL для всех миграций и git diff --check прошли. |

| 2026-11-07 | 00:28:12 | 00:35:03 | около 6 мин 51 сек | Добавлен WorkflowService: явный старт проекта, последовательные переходы с обязательными актором и причиной, блокировка переходов без источника, активного фактического claim, трёх вариантов или решения на соответствующих этапах. Состояние и append-only события сохраняются в PostgreSQL; добавлена миграция 0007 и команды `psa-main workflow start/status/advance/events`. Обновлён README с текущими границами гейтов. Тесты не запускались; compileall, offline SQL для всех миграций, heads и git diff --check прошли. |

| 2026-11-07 | 00:35:03 | 00:36:15 | около 1 мин 12 сек | Создан дневной сводный отчёт `reports/2026-11-07-main-development-summary.md` по непрерывной серии основной разработки 6–7 ноября: архитектура, сервисы, миграции, команды, проверки, ограничения и коммиты. |

## Проверки

Тестовый набор не запускался. Для демо выполнялись CLI-команды; `validate demo` и `verify demo` прошли. `critic-pack demo` сформировал пакет. MCP-зависимость в окружении не установлена, поэтому адаптер не запускался.

| 2026-11-05 | 23:10:39 | 23:17:26 | около 6 мин 47 сек | Добавлены режимы `quick_scan`, `decision_grade`, `deep_research`, аудит переключений, проверки source threshold в CLI/MCP и отображение режима в status, next, render и critic pack. Зафиксированы пороги: 1, 2 либо 1 + открытый high gap, 4 либо 1 + такой gap. Обновлены инструкции и план MVP. Тесты не запускались; выполнена только проверка diff на пробелы. |

| 2026-11-05 | 23:21:35 | 23:27:25 | около 5 мин 50 сек | Повторно проверен M6: сравнение остаётся exploratory без независимого слепого оценщика и отдельного замера времени/API-стоимости. Выполнен M7: синтетический табличный кейс прошёл полный workflow до completed; рассчитаны доли и ограничения, добавлен локатор цитат `lines:start-end` для диапазона строк; validate и verify прошли без ошибок и предупреждений. Обновлены evaluation/README/план; табличная агрегация остаётся ручной, автоматический профиль CSV не добавлялся.

| 2026-11-05 | 23:31:26 | 23:32:41 | около 1 мин 15 сек | Создан `diagrams/mvp/` с архитектурой, жизненным циклом, pipeline доказательств и решений, взаимодействием MCP и моделью данных проекта. Схемы привязаны к текущей реализации и помечают границы MVP; автоматическая табличная аналитика и целевые MCP-host проверки обозначены как отдельные/не готовые элементы.

| 2026-11-05 | 23:39:34 | 23:42:34 | около 3 мин | Уточнён целевой MCP framework полного проекта: отдельный FastMCP 4.x (`fastmcp>=4,<5`); зафиксировано отличие от текущего MVP на официальном SDK v2 `MCPServer`. В M8 добавлены миграция и CLI/MCP parity-проверки. Обновлена MCP-документация, чтобы она различала текущий код и целевую архитектуру.

| 2026-11-05 | 23:43:00 | 23:46:30 | около 3 мин 30 сек | MCP-адаптер переведён на отдельный FastMCP 4.x (`fastmcp>=4,<5`), stdio указан явно; обновлены опциональная зависимость, README, docs/mcp, архитектурный план и схемы. FastMCP в текущем окружении не установлен, поэтому runtime/host-подключение не проверялись; остаток M8 — parity в целевых средах.

| 2026-11-05 | 23:49:37 | 23:56:37 | около 7 мин | Реализована основа M9: повторный импорт того же источника сохраняет архив предыдущего текста, проверяет хэши и пишет source revision event; `psa revisit list/resolve` и MCP-tools находят зависимости claims/options/decisions и аудируют подтверждение владельца со списком ID. Добавлены docs и Mermaid-схема, уточнён план. Тесты не запускались; ручной сценарий изменения источника и финальная демонстрация остаются до закрытия M9. |

| 2026-11-06 | 00:00:00 | 00:06:30 | около 6 мин 30 сек | Подготовлен PowerShell runbook M9 и две синтетические версии CSV для сценария изменения источника; сценарий не запускался. Создан label-masked A/B-пакет и scoring sheet для независимого оценщика с отдельным owner key; обновлены статусы M6/M9 в плане и документации. MVP не завершён: acceptance M9, средовые проверки M8 и внешняя оценка M6 остаются открытыми. |

| 2026-11-06 | 00:06:30 | 00:09:46 | около 3 мин 16 сек | Проведена ручная приёмка M9: повторный импорт создал ревизию, зависимые C-001/D-001 обнаружены, review снял pending; validate и verify прошли. Исправлен runbook: ASCII аргументы для PowerShell и полный набор ролей вариантов; исходники демо включены в Git. Тестовый набор не запускался. |

| 2026-11-06 | 00:09:46 | 00:13:19 | около 3 мин 33 сек | Обновлён план: M9 ручная приёмка закрыта, проверки CLI прошли. Runbook переведён на ASCII в аргументах PowerShell для воспроизводимости; удалён дублирующий блок README. Проверено: FastMCP не установлен (astmcp: None), целевые IDE в этой среде недоступны; M8 host parity и M6 независимая оценка остаются открытыми. git diff --check прошёл. |

| 2026-11-06 | 00:13:19 | 00:15:00 | около 1 мин 41 сек | Для M8 подготовлена матрица live-приёмки FastMCP stdio: общие условия подключения, parity-сценарий CLI/MCP, безопасные синтетические данные и поля для версии/доказательств; README и план ссылаются на неё. Результаты хостов не отмечены как пройденные: FastMCP не установлен, Qwen Coder и SourceCraft недоступны. git diff --check прошёл; тесты не запускались. |

| 2026-11-06 | 00:15:00 | 00:27:43 | около 12 мин 43 сек | Установлен FastMCP 4.1.6 в локальный игнорируемый .venv. Через MCP Python SDK 2.3.0 поднят сервер stdio, обнаружено 20 инструментов; выполнены импорт источника, claim/options/decision, source revision и review. MCP-сценарий: pending 1→0; validate/verify успешны. CLI на том же проекте вернул validate/verify passed и pending_count 0. Зафиксирован частичный локальный parity результат; подключение из UI Codex и проверки Qwen Coder/SourceCraft остаются открытыми. Обновлены матрица, план, .gitignore и синтетический кейс. |

| 2026-11-06 | 00:27:43 | 00:29:38 | около 1 мин 55 сек | Для M6 добавлен шаблон записи парного A/B-запуска: версии модели/входов, одинаковые лимиты, порядок условий, human/model time, фактическая или неизвестная стоимость, вмешательства, артефакты, scoring и догадки рецензента. Документация оценки и README ссылаются на шаблон; M6 остаётся открытым до равноусловного запуска и независимой оценки. git diff --check прошёл. |

| 2026-11-06 | 22:36:00 | 22:59:36 | около 23 мин 36 сек | Реализован coverage контроль черновиков стратегии: абзацы требуют claim/hypothesis/open-question/commitment маркеры; клиентские обещания в ключевом сообщении должны ссылаться на capability со статусом available. Добавлены capabilities.jsonl, CLI capability/coverage, MCP psa_add_capability/psa_coverage, проверки validate и gate, вывод capability registry в strategy render и документация. Синтетические кейсы размечены и их производные Markdown пересобраны. Приёмочные проверки по просьбе пользователя пропущены; выполнен только git diff --check. |

| 2026-11-06 | 22:59:36 | 23:01:06 | около 1 мин 30 сек | Ужесточена обработка capability-статусов и добавлена проверка существования проекта для psa coverage; ошибки схемы остаются диагностируемыми. Тесты и приёмка не запускались. |

| 2026-11-06 | 23:01:06 | 23:09:59 | около 8 мин 53 сек | Добавлена защита generated Markdown: SHA-256 render-manifest, обнаружение ручных изменений в validate и gate, безопасная миграция старых проектов через --adopt-existing без перезаписи, а намеренное восстановление требует --by/--reason и записывается в events.jsonl. Добавлены CLI/MCP операции, документация и статусы плана. Манифесты demo/table-demo созданы без изменения самих Markdown. Приёмочные проверки не запускались; git diff --check прошёл. |

| 2026-11-06 | 23:09:59 | 23:13:11 | около 3 мин 12 сек | Добавлена команда psa doctor: безопасно проверяет Python, встроенные шаблоны, uv/FastMCP и наличие .env/.env.example; значения секретов не читаются и не выводятся. Есть текстовый и JSON-вывод, optional-компоненты дают предупреждения. Обновлены README и MVP-план. Приёмка и тесты не запускались; git diff --check прошёл. |

| 2026-11-06 | 23:13:11 | 23:22:49 | около 9 мин 38 сек | По запросу о переходе к основной разработке создана ветка feature/main-solution-roadmap и короткий roadmap полного решения: foundation, домен/хранилище, источники/retrieval, provider/workflow, стратегический анализ, FastMCP-интеграции, безопасность/надёжность и pilot/evaluation. Зафиксированы постоянные архитектурные решения и отложенные scope (RAG/web/multiuser без обоснования). README и полный план ссылаются на roadmap. git diff --check прошёл. |

## Продолжение 7 ноября 2026, 18:55 (Asia/Novosibirsk)

Подготовлен контейнерный запуск миграций: Dockerfile включает Alembic, добавлен Compose-сервис migrate, .dockerignore исключает секреты и локальные данные. Шаблон .env настроен для localhost, Compose использует внутренний hostname postgres; порт опубликован на loopback. Исправлено ORM-ограничение workflow_states: current_stage вместо несуществующей stage. Compose config, генерация PostgreSQL DDL и offline Alembic SQL прошли. Docker Engine недоступен, сборка и подключение к живой БД не выполнялись. Длительность блока отдельно не замерялась.

## PostgreSQL integration smoke — 7 ноября 2026, 19:07 (Asia/Novosibirsk)

Запущены Docker Desktop и PostgreSQL 17; образ приложения собран, миграции 0001–0007 применены к development-БД. Добавлен scripts/smoke_main.py и запуск в README. Сквозной сценарий выявил отсутствующий импорт UUID в claim-репозитории; исправлено. Контрольный сценарий из пересобранного образа прошёл до completed с восемью событиями, alembic check не обнаружил новых операций. Отчёт: reports/2026-11-07-postgres-smoke.md. PostgreSQL и синтетические данные оставлены для просмотра. Длительность отдельно не замерялась.

## PostgreSQL backup/restore — 7 ноября 2026, 19:16 (Asia/Novosibirsk)

Добавлен host-side scripts/postgres_backup.py: pg_dump custom format, бинарное копирование через Compose cp, SHA-256-манифест, restore одной транзакцией только в новую БД. Выполнено восстановление в restore_check_ed922d864b17; совпали набор и количества строк во всех 15 public-таблицах, сохранена версия Alembic 0007. Проверены отказы для существующей БД и повреждённого архива. Добавлены инструкция и отдельный отчёт; backups/ исключён из Git и Docker context. Исходная БД не изменялась, backup и тестовая БД оставлены локально. Длительность отдельно не замерялась.

## Конкурентность и транзакции — 7 ноября 2026, 19:23 (Asia/Novosibirsk)

Добавлен scripts/smoke_integrity.py: четыре потока проверяют регистрацию источников и workflow approvals, проверяются четыре типа межпроектных ссылок и три rollback-сценария после flush. WorkflowService и CLI требуют expected_version/--expected-version для привязки approval к проверенному состоянию; устаревшие запросы отклоняются. Обновлён основной smoke-сценарий. Обе проверки прошли из пересобранного Docker-образа на PostgreSQL. Отчёт: reports/2026-11-07-postgres-integrity.md. Синтетические проекты оставлены для просмотра; длительность отдельно не замерялась.

## Импорт локальных документов — 7 ноября 2026, 19:45 (Asia/Novosibirsk)

Начат этап 3: добавлены DocumentExtractor port, отдельные local/HTML adapters, DocumentImportService и CLI document import. Поддерживаются TXT/Markdown/CSV/JSON как текст и статический HTML; размер ограничен 10 MiB, кодировка задаётся явно, исполняемые HTML-блоки исключаются. Пять unit-тестов прошли в контейнере; CLI smoke на PostgreSQL подтвердил идемпотентность, новую ревизию при изменении и сохранение ссылок цитат. Контрольный запуск из собранного образа прошёл. Добавлены инструкция и отчёт reports/2026-11-07-document-import.md. Длительность отдельно не замерялась.

## DOCX-импорт — 7 ноября 2026, 19:53 (Asia/Novosibirsk)

Добавлен отдельный python-docx adapter, optional extra documents и установка extra в Docker-образ. Извлекаются абзацы и таблицы тела в исходном порядке, title и ограничения; добавлены лимиты ZIP/распаковки/table span. Двенадцать unit-тестов прошли. CLI smoke из собранного образа на PostgreSQL подтвердил HTML/DOCX ревизии, идемпотентность, таблицы и сохранение цитат. Отчёт: reports/2026-11-07-docx-import.md. Документация и roadmap обновлены; длительность отдельно не замерялась.

## PDF-импорт — 7 ноября 2026, 19:59 (Asia/Novosibirsk)

Добавлен pypdf adapter в extra documents: текст по страницам, page markers, metadata title, locator pages:1-N, отметки пустых страниц и отказы для шифрования/повреждения/отсутствия текста. Добавлены ограничения страниц, stream и выходного текста; передача locator поддержана существующим SourceService без миграции. Все 19 unit-тестов, PDF CLI smoke и регрессия HTML/DOCX прошли в собранном образе на PostgreSQL. Отчёт: reports/2026-11-07-pdf-import.md. OCR и автоматическая сверка locator с номером страницы не реализованы; длительность отдельно не замерялась.

## XLSX-импорт — 7 ноября 2026, 20:10 (Asia/Novosibirsk)

Добавлен отдельный openpyxl adapter с defusedxml в extra documents: видимые листы, адреса/типы ячеек, формулы без вычисления и без кешированных результатов, исключение скрытых листов. Введены лимиты ZIP/распаковки/листов/координат/ячеек/текста, проверяются реальные XML-координаты вместо доверия dimension. Исправлена обработка lxml ошибки повреждённого workbook.xml. Все 28 тестов и XLSX CLI smoke прошли из финального образа на PostgreSQL; подтверждены ревизии, формулы и цитата исходной ячейки. Отчёт: reports/2026-11-07-xlsx-import.md. Длительность отдельно не замерялась.

## Полнотекстовый поиск PostgreSQL — 7 ноября 2026, 20:20 (Asia/Novosibirsk)

Добавлены отдельный SourceSearchService/port, PostgreSQL search adapter, revision-aware результаты и CLI search с JSON. Миграция 0008 применена к существующей development-БД: generated tsvector и GIN по названию и первым 100000 символам текста. Выдача ограничена проектом и последней ревизией. Все 31 unit-тест, PostgreSQL smoke поиска и alembic check прошли из собранного образа. Проверены ranking, фразы, кириллица, изоляция, исключение старых версий, backfill и CLI JSON. Инструкция docs/source-search.md, отчёт reports/2026-11-07-source-search.md; длительность отдельно не замерялась.

## HTTP-импорт и provenance — 7 ноября 2026, 20:34 (Asia/Novosibirsk)

Добавлены отдельные public URL policy, pinned HTTP/TLS transport, fetch/extract adapters, WebImportService и CLI web import. Миграция 0009 добавила provenance ревизии (requested/final URL, media type, charset, время и hash тела). DNS/redirect проверки исключают приватные и смешанные адреса; ввод/ответ ограничены, compressed/truncated ответы отклоняются. Все 47 unit-тестов, web smoke с реальным HTTPS example.com, регрессия основной цепочки и alembic check прошли. Документация и roadmap обновлены; отчёт reports/2026-11-07-web-import.md. Длительность отдельно не замерялась.

## Первый агентный проход — 7 ноября 2026, 22:54 (Asia/Novosibirsk)

Начат этап 4: отдельные Qwen-compatible HTTP adapter, порты, доменные схемы, версионированный prompt и AgentAnalysisService. Добавлены CLI agent analyze/show и dry-run, PostgreSQL agent_runs и миграция 0010. Ответ проверяется по JSON-схеме и точным цитатам переданных ревизий; результат остаётся черновиком, claims/решения/workflow не изменяются. Все 64 unit-теста, PostgreSQL smoke с MockTransport и Alembic check прошли. Реальный API не вызывался: ключ не настроен. Обновлены конфигурация, Docker-образ, инструкция и планы. Отчёт: reports/2026-11-07-agent-analysis.md. Длительность отдельно не замерялась.

## OpenAI-compatible клиент через LiteLLM — 7 ноября 2026, 23:10 (Asia/Novosibirsk)

По запросу пользователя Qwen отделён от провайдера: OpenAICompatibleProvider на LiteLLM SDK 1.108.2, универсальные LLM_* настройки и необязательный JSON extra body. Сохранены alias для прежних QWEN_* переменных; локальный .env переименован без вывода значений. Удалён прежний QwenChatProvider, обновлены CLI, extra agent, инструкции и планы. Отдельный transport сохраняет лимит ответа, raw usage и обработку gzip; проверены отсутствие retries и безопасные ошибки. Все 70 unit-тестов и агентный PostgreSQL smoke из собранного Docker-образа прошли с MockTransport. Внешняя модель не вызывалась. Отчёт: reports/2026-11-07-litellm-provider.md. Длительность отдельно не замерялась.

## FastMCP основной системы — 8 ноября 2026, 14:22 (Asia/Novosibirsk)

Добавлен отдельный PostgreSQL stdio-server psa-main-mcp с поиском, prepare/analyze/get run. CLI и MCP используют общий bootstrap и JSON payloads; server/tool/error модули разделены. Все 77 unit-тестов и интеграционный PostgreSQL smoke прошли: настоящий stdio subprocess, CLI/MCP parity, проектная изоляция, проверка цитат и отсутствие побочных эффектов чтения. Запущены Docker Desktop/PostgreSQL; локальный DATABASE_URL и пример переведены с localhost на 127.0.0.1 после зависания Windows-подключения. Ключ LLM уже настроен: одна попытка живого анализа синтетического текста завершилась provider_error, failed run сохранён без повторов. Добавлен явный live smoke, обновлены инструкции, планы и README. Отчёт: reports/2026-11-08-main-mcp.md. Длительность отдельно не замерялась.

## Диагностика провайдера и живой Qwen — 8 ноября 2026, 14:41 (Asia/Novosibirsk)

Добавлены безопасные provider error codes с сохранением в существующем agent_runs.error_code и передачей через CLI/MCP. Диагностика установила HTTP 400; GET /models подтвердил несовпадение настроенного qwen3.8:27b с доступным Qwen3.8-27B. Исправлены локальная конфигурация, пример и default model. После исправления живой синтетический проход прошёл: одна проверенная цитата, 768 input + 273 output = 1041 токен, стоимость null. Всего в блоке две явные попытки анализа и один read-only запрос моделей, без автоматических retries. Отдельный text-only envelope исключает provider metadata из SDK warnings, не меняя текст и известный usage. Все 82 unit-теста, агентный PostgreSQL smoke и stdio CLI/MCP smoke прошли. Обновлены документы и roadmap. Отчёт: reports/2026-11-08-provider-diagnostics.md. Длительность отдельно не замерялась.

## Checkpointed агентный pipeline — 8 ноября 2026, 14:57 (Asia/Novosibirsk)

Добавлены AgentPipelineService/port/model/repository, миграция 0011 и CLI pipeline start/show/resume. MCP расширен до семи tools. Этапы: pin evidence, checked draft, deterministic human review packet; human project workflow не меняется. Atomic reservation связывает running agent_run до HTTP, expected_version и row lock исключают двойной конкурентный вызов. Resume сохраняет source revisions/request hash/config fingerprint, использует persisted success без повторной генерации и блокирует unknown outcome. Все 96 unit-тестов, Alembic check, PostgreSQL recovery/concurrency/rollback/composite FK smoke и регрессии agent/stdio MCP прошли. Новых живых вызовов не было; синтетические checkpoints сохранены локально. Добавлены инструкция, диаграмма и отчёт reports/2026-11-08-agent-pipeline.md, планы обновлены. Длительность отдельно не замерялась.

## План IDE-инструкций и evidence extraction — 8 ноября 2026, 15:16 (Asia/Novosibirsk)

По запросу пользователя добавлен отдельный пакет AGENTS.md и адаптеров .cursor/.claude/.codex с проверкой загрузки, синхронизации и CLI/MCP parity; коммит плана 7d98455, сами файлы пока не реализованы. Продолжена основная разработка: task evidence_extraction с отдельными schemas/prompt/registry, черновиками fact/hypothesis и gaps, проверкой цитат и validation_question. Task сохраняется в runs/pipelines (0012), выбирается CLI/MCP и закреплён для resume; default answer совместим. Все 108 unit-тестов, Alembic check, PostgreSQL extraction smoke, recovery/concurrency и stdio parity прошли; восстановлен старый pre-task checkpoint без нового вызова. На синтетическом живом Qwen первый лимит 1024 дал incomplete completion, явная контрольная попытка до настроенных 2048 прошла: два fact drafts, два gaps, четыре цитаты, 2348 total tokens, cost null. Canonical claims/approvals не создавались. Обновлены инструкции и планы; отчёт reports/2026-11-08-evidence-extraction.md. Длительность отдельно не замерялась.

## Linked critic-проверка — 8 ноября 2026, 15:39 (Asia/Novosibirsk)

Добавлены отдельные CriticDraft/Assessment, prompt evidence-critic-v1, AgentCriticService/critic_context, CLI critic prepare/start и два MCP tools (inventory девять). К исходному успешному answer/extraction run привязаны input_run_id и канонический input_hash; миграция 0013 задаёт task guard и project-bound FK. Проверяются полное item coverage и цитаты; verdict вычисляется сервером, требует human review и не изменяет исходный результат/approvals. Общий pipeline сохраняет безопасный recovery без повторного модельного запроса. Все 125 unit-тестов, Alembic check, PostgreSQL critic/hash/FK/recovery и регрессия pipeline/extraction/stdio parity прошли. Первый живой toy case имел подсказку overclaim в caveat и учтён только как API check; фикстура исправлена, новый нейтральный live case также вернул needs_revision (2040 total tokens, cost null). Всего две явные живые попытки, без retries. Обновлены инструкция, диаграмма и планы; отчёт reports/2026-11-08-agent-critic.md. Длительность отдельно не замерялась.

## Стратегические варианты и сравнение — 8 ноября 2026, 16:22 (Asia/Novosibirsk)

Начат этап 5: отдельная задача strategy_options с compact prompt v2, тремя типизированными альтернативами, качественным сравнением, цитатами, допущениями, рисками и экспериментом. Добавлены migration 0014 и linked critic options/comparison/gaps; используются общий pipeline и девять MCP tools. Human-review packet требует выбора человека, canonical side effects отсутствуют. Все 140 unit-тестов, PostgreSQL options/critic smoke, stdio CLI/MCP parity и Alembic check прошли. Пять явных живых синтетических попыток: первые три исчерпали лимиты 2048/4096, короткая диагностика показала расход 128 токенов на reasoning, разовое отключение thinking дало валидный insufficient_evidence (2325 total tokens, cost null). Полный живой кейс трёх стратегий пока не подтверждён. Добавлены безопасные error/usage counters, инструкция, диаграмма и обновления планов; .env не менялся. Отчёт: reports/2026-11-08-strategy-options.md. Длительность отдельно не замерялась.

## План GitHub Actions — 8 ноября 2026, 16:27 (Asia/Novosibirsk)

В основной план добавлен раздел 14.1 и целевая структура .github/: ci/demo/release, unittest/Ruff/lock, PostgreSQL 17/Alembic/FastMCP smoke, synthetic demo без модели, secrets/docs и будущий instruction-sync. Команды адаптированы под psa/psa-main; несуществующие sf/replay/doctor flags не приняты за реализацию. Указаны порядок внедрения, приёмка чистого checkout/архива, ограничения PR permissions и запрет LLM-секретов/вызовов в CI. Обновлён roadmap, проверен diff; код и GitHub settings не менялись, тесты/Actions не запускались. Отчёт: reports/2026-11-08-github-actions-plan.md. Длительность отдельно не замерялась.

## Первый GitHub CI — 8 ноября 2026, 16:36 (Asia/Novosibirsk)

Реализован первый срез раздела 14.1: ci.yml с Ubuntu Python 3.11/3.12 + Windows 3.12 unit matrix, base-install и PostgreSQL 17/Alembic/FastMCP job. Добавлены dev-группа Ruff/build, uv 0.11.30 и uv.lock (119 packages); Actions закреплены на проверенные SHA, ключи/вызовы LLM не используются. Frozen install и 140 тестов прошли локально на Python 3.12, затем на Python 3.11 из чистой копии без .env; семь smoke и миграции 0001–0014 прошли в отдельной временной БД. Ruff/diff/YAML checks успешны. Тестовые БД/checkout очищены, рабочие .env/.venv/БД не менялись. Удалённый Actions status не подтверждён (API без авторизации 404). Обновлены планы/README и инструкция docs/continuous-integration.md; отчёт reports/2026-11-08-github-ci.md. Длительность отдельно не замерялась.

## CI: docs, secrets и demo — 8 ноября 2026, 16:51 (Asia/Novosibirsk)

Добавлены docs/secrets jobs и demo.yml. scripts/ci/ разделяет Markdown links/anchors/required files, tracked runtime/history policy, pinned официальный Gitleaks CLI и локальное воспроизведение synthetic artifacts. Исправлены пять битых ссылок; scanner не читает игнорируемый .env и выводит только безопасные поля, --network none и negative probes проверены. Все 146 unit-тестов, Ruff, docs/history/Gitleaks checks и demo/table-demo прошли; базовый Python 3.11 без extras/dev также воспроизвёл демо (1+1 цитаты, 9+5 абзацев, model_calls=0). Оригиналы projects/, .env и рабочая БД не менялись. Remote Actions result пока не подтверждён. Обновлены README, инструкция и планы; отчёт reports/2026-11-08-ci-docs-secrets-demo.md. Длительность отдельно не замерялась.

## Релизная сборка и Docker smoke — 8 ноября 2026, 21:33 (Asia/Novosibirsk)

Завершён начатый днём срез: builder ZIP/wheel/sdist из tracked allowlist, version/tag guard, SHA-256 manifests и проверка установки wheel/sdist вне src; release.yml переиспользует ci/demo и создаёт только draft по точному тегу. Dockerfile переведён на pinned Python/uv images и frozen runtime agent/documents/mcp; smoke прошёл на Linux от non-root с read-only FS/network none, offline Alembic SQL, 9 FastMCP tools и обоими демо. Все 151 unit-тест, Ruff/docs/diff/YAML и Gitleaks (0/0 находок, negative probes) прошли. Чистый ZIP собран и проверен из f038a1e, dirty=false, model_calls=0; этот отчёт коммитится отдельно. Остановка автоматической проверки разрешений из-за usage limit прервала промежуточный запуск, вечером проверки завершены после продолжения; Docker Engine восстановлен запуском Desktop. .env/данные рабочей БД не менялись; теги/релизы не создавались, remote Actions result не подтверждён. Отчёт reports/2026-11-08-release-docker.md, инструкция docs/distribution.md. Длительность отдельно не замерялась.

## Канонические варианты и человеческий выбор — 8 ноября 2026, 21:54 (Asia/Novosibirsk)

Добавлены отдельные StrategySelectionService/port/domain command и PostgreSQL adapter, migration 0015, selection preview/record/show и три MCP tools (inventory 12). Явная команда человека с pinned hashes/полным выбором/notes сохраняет 3 proposed options, decision и immutable audit атомарно; critic concerns требуют resolution, workflow approvals/claims/capabilities не создаются. Под locks проверяются runs/источники; replay идемпотентен, collision откатывает весь набор. Все 160 unit-тестов, Alembic check, PostgreSQL concurrent/rollback/FK/CLI/stdio smoke и options/main-MCP регрессия прошли; Docker подтвердил 12 tools/offline SQL/non-root/read-only/network none. Живых LLM-запросов нет. Остановленный PostgreSQL поднят на прежнем volume; .env не менялся. Обновлены планы, CI, инструкции и диаграмма; отчёт reports/2026-11-08-strategy-selection.md. Далее — стратегические артефакты на основе решения. Длительность отдельно не замерялась.

## Стратегия по сохранённому решению — 8 ноября 2026, 22:22 (Asia/Novosibirsk)

Добавлены StrategyPlanDraft/prompt v1, отдельные context/service/input port и project-bound snapshot migration 0016. Проход фиксирует canonical decision/selected option, human review/critic resolution и источники; fresh retrieval/смена выбора запрещены. Pipeline/recovery/linked critic работают с hashes и freshness, communication internal-only, без публикации/canonical approvals. Добавлены CLI strategy prepare/start и два MCP tools (inventory 14). JSONB key reorder выявлен integration smoke и устранён канонической сериализацией только нового task; prototype checkpoints не переписывались. Все 170 unit-тестов, PostgreSQL selection→strategy→critic/concurrency/recovery/FK/CLI/stdio и old critic/main-MCP регрессия прошли; Docker подтвердил offline SQL/non-root/read-only/network none и 14 tools. Живой модели нет, .env не менялся. Обновлены CI, docs/планы и диаграмма; отчёт reports/2026-11-08-strategy-plan.md. Далее — human approval/export и capability-backed promises. Длительность отдельно не замерялась.

## Привязка knowledge/ к этапам — 8 ноября 2026, 22:34 (Asia/Novosibirsk)

По согласованию пользователя базовое наполнение knowledge/ закреплено за текущим этапом 5: README, methods/checklists, provenance/версии/применимость/ограничения и приёмка до завершения этапа. Этап 6 включает подключение к agent/skills, каноническим и IDE-инструкциям с проверкой загрузки/версий. RAG остаётся отдельным отложенным расширением. Обновлены основной план и roadmap; папка и интеграция пока не реализованы. Изменения только документационные, тесты кода не запускались. Отчёт reports/2026-11-08-knowledge-plan.md. Длительность отдельно не замерялась.

## Базовое knowledge/ — 8 ноября 2026, 22:46 (Asia/Novosibirsk)

Созданы README/sources/catalog и 3 methods + 3 checklists версии 1.0.0, с provenance/авторством/датой/применимостью/ограничениями. Проверены 4 внешние первичные страницы; внутренние эвристики отделены от внешних адаптаций. База ручная, runtime/IDE/FTS/RAG интеграция не добавлялась. Knowledge включено в ZIP/sdist упаковку и required docs; 11 целевых distribution/CI tests, проверка catalog metadata и состава ZIP/sdist прошли, Ruff/diff — OK. Review bundle сохранён отдельно в игнорируемой .venv-ci, предыдущий release не заменялся. Обновлены планы/README; основной этап 5 ещё не закрыт. Отчёт reports/2026-11-08-knowledge-base.md. .env/БД/prompts не менялись, живой модели нет. Длительность отдельно не замерялась.

## LangGraph в плане — 8 ноября 2026, 22:55 (Asia/Novosibirsk)

LangGraph закреплён как целевой основной orchestration framework и ближайший подэтап 4.1 до расширения approval/export. В основной план/roadmap добавлены ADR/state/modules, PostgreSQL checkpointer, durable operation keys, human interrupts, legacy compatibility/rollout и failure/concurrency/project-isolation приёмка без живой модели. FastMCP/LiteLLM/domain ledgers сохраняют роли, knowledge integration остаётся этапом 6. Проверены официальные persistence/checkpointers/interrupts docs; библиотека не устанавливалась, код/.env/БД не менялись. Отчёт reports/2026-11-08-langgraph-plan.md. Длительность отдельно не замерялась.

## Корректировка оркестрации — 8 ноября 2026, 22:59 (Asia/Novosibirsk)

После сверки со specs/case.md отменён обязательный LangGraph 4.1: агентный цикл ведёт IDE-хост, CLI/MCP и общие сервисы обеспечивают состояние, проверки и gates. LiteLLM/pipeline сохранены как опциональные операции; основной путь без отдельного API-ключа ещё подлежит проверке. Следующие работы — approval/export и capability-backed promises, затем AGENTS.md/skills/адаптеры и knowledge integration. Обновлены основной план/roadmap, прошлый LangGraph-отчёт помечен историческим. Только документация; зависимости/код/.env/БД не менялись. Отчёт reports/2026-11-08-ide-orchestration-plan.md. Длительность отдельно не замерялась.

## Внутреннее утверждение и экспорт стратегии — 8 ноября 2026, 23:13 (Asia/Novosibirsk)

Добавлены отдельные domain command/service/port/PostgreSQL store и guards, migration 0017, immutable internal_review receipt, CLI preview-approval/approve/approval/export и четыре MCP tools (inventory 18). Запись требует явного подтверждения человека и разрешения замечаний critic, rechecks под locks исключают изменение оснований после preview; replay/concurrency идемпотентны. Экспорт возвращает UTF-8 Markdown/JSON contents + SHA-256 и блокируется при stale/changed inputs; публикация/customer promises/workflow gates не утверждаются. Исправлен UTF-8 stdout main CLI в Windows. Все 180 unit-тестов, Alembic check и PostgreSQL concurrency/rollback/FK/CLI/real-stdio smoke прошли без живой модели; Docker offline/non-root/read-only/18-tools, docs (114), Ruff/diff и Gitleaks (0/0, negative probes) прошли. Обновлены CI, планы, документация и диаграмма. Следующий срез — capability-backed promises. Отчёт reports/2026-11-08-strategy-approval.md. .env/зависимости не менялись; синтетические проекты остались в development-БД. Длительность отдельно не замерялась.

## Проверка клиентских обещаний — 8 ноября 2026, 23:29 (Asia/Novosibirsk)

Добавлен модульный read-only PromiseCheckService с typed IDE-authored request, evidence reader port, PostgreSQL REPEATABLE READ/READ ONLY snapshot, CLI promise check и MCP psa_main_check_promises (inventory 19). Проверяются available capability, linked active facts, все current source revisions/hash/quote/locator; bad links/planned/stale/corrupt/oversized evidence блокируются. Ответ — hash-bound пакет для человеческого семантического review, без модели/бизнес-записей/публикации/approval. Добавлен --json UUID discovery для capability/claim list. Все 193 unit-теста, Alembic check и PostgreSQL concurrency/CLI/real-stdio smoke прошли; Docker offline/non-root/read-only/19-tools, docs (116), Ruff/diff и forbidden-paths/full-history прошли; Gitleaks: 0/0 находок, negative probes пройдены. Обновлены CI, планы, инструкция и диаграмма. Следующий срез — явное решение человека по обещаниям с transactional recheck и привязкой к артефактам. Отчёт reports/2026-11-08-promise-check.md. .env/зависимости/схема не менялись; synthetic smoke data остались в development-БД. Длительность отдельно не замерялась.

## Аудит ТЗ и архитектурного плана — 8 ноября 2026, 23:37 (Asia/Novosibirsk)

Полностью прочитан единственный specs/case.md, сверены основной план/roadmap и ключевые реализации. PostgreSQL/Docker не обязательны и не запрещены ТЗ; это прежние выбранные зависимости, требующие пользы и понятного setup. Выявлены конфликт PG/JSONL источника истины, двойной psa/psa-main путь, задержка IDE instructions/knowledge integration, отсутствие обязательных status_quo/stop ролей в новой options schema и полей baseline/metrics/window в experiment draft. Рекомендован переносимый IDE-first сценарий, повышение приоритета инструкций и обязательных результатов; PG/Docker — кандидаты на опциональные расширения, смена backend требует отдельного этапа. Файловые demo/table-demo повторно прошли replay без БД/Docker/LLM (первый запуск temp ограничен sandbox, повтор успешен). Основные планы, код, .env/зависимости/БД не менялись; аудит не считается выполненной миграцией. Отчёт reports/2026-11-08-specs-plan-audit.md. Длительность отдельно не замерялась.

## Файловый основной план по ТЗ — 8 ноября 2026, 23:50 (Asia/Novosibirsk)

Обновлены основной план/roadmap: PostgreSQL/Docker/Compose/SQLAlchemy/Alembic/SQLite/LangGraph исключены из целевого решения, файловые JSON/JSONL — один канон, IDE ведёт агентный цикл. Новый порядок R1 инструкции/skills/knowledge, R2 файловое ядро и безопасный перенос/retire прежнего PG-контура, R3 полнота результата (обязательные альтернативы, baseline/metrics/window/guardrails, corrections/revisit), R4 переносимость, R5 оценка, R6 сдача. Целевой CI без DB/Docker, включая native secrets scanner; код/зависимости/CI/data фактически пока не изменены. Сохранены модульность, replay/unknown-outcome guards, mapping/provenance/hashes и проверки переноса; M6/M8 не объявлены пройденными. Отчёт reports/2026-11-08-file-first-plan.md. Проверки документации/diff; unit не повторялись. .env/БД/контейнеры не менялись. Длительность отдельно не замерялась.

## R1: инструкции и контекст агента — 9 ноября 2026, 17:38 (Asia/Novosibirsk)

Созданы AGENTS.md, workflow/quality/safety, 4 canonical skills и stage-scoped read-only psa context с ID/version/contents/SHA-256 knowledge и instructions. Добавлены 9 generated host adapters/copies, sync --write/--check, CI check и source packaging; hidden auth/settings исключены. Knowledge delivery отмечена доступной, реальное поведение hosts/модели не объявляется проверенным. Все 200 unit-тестов, 4 skill validations (UTF-8), sync/Ruff, sdist assets и оба файловых demo прошли. Обновлены планы/README; R1 частично выполнен, новый живой кейс и host acceptance остаются открытыми, M6/M8 не закрыты. Реальные model API/БД/Docker не использовались, .env/данные не менялись. Отчёт reports/2026-11-09-r1-instructions.md. Длительность отдельно не замерялась.

## R2: безопасный файловый init/recovery — 9 ноября 2026, 17:55 (Asia/Novosibirsk)

Реальная IDE-проверка R1 отложена пользователем; начат R2. Добавлены инвентаризация/контракт docs/file-core.md, WorkspaceSeed/service/port и отдельные filesystem path/lock/manifest/repository modules. CLI/MCP init публикуют целый начальный кейс через staging+receipt hashes+OS lock+rename; занятые папки не меняются. Добавлены workspace pending/recover с явным operation UUID; partial/tampered data не публикуются, committed replay не сбрасывает author edits. Служебные staging/locks исключены из Git/release policy. Полный прогон 211 тестов прошёл, финальные 11 file/MCP и 6 CI tests повторены; оба demo, Ruff/sync/repository прошли. R2 не завершён: expected_version/многофайловые updates/import/retire старого backend впереди. Отчёт reports/2026-11-09-r2-workspace-init.md. DB/Docker/real LLM/.env не использовались, dependencies/data не менялись. Длительность отдельно не замерялась.

## R2: typed research artifact и atomic HEAD — 9 ноября 2026, 18:16 (Asia/Novosibirsk)

Добавлены отдельные domain/port/service/file bundle+journal/CLI/MCP modules для IDE-authored research_plan draft без API run. Expected_version artifact-журнала и case_hash, immutable request/artifact/Markdown/event/receipt/base snapshot + manifest, atomic HEAD, hash-linked history, replay/collision/recovery и safe bounds. Пять файловых MCP tools используют тот же core; legacy gates/реестры не меняются автоматически. Все 226 unit-тестов, включая 15 новых crash/concurrency/CLI/real-stdio, прошли; оба demo/Ruff/sync/repository прошли. Следующий срез — потребление structured плана в workflow и перенос нужных writers/readers, затем legacy import/retire. Отчёт reports/2026-11-09-r2-research-artifacts.md и контракт docs/research-artifacts.md. DB/Docker/real LLM/.env не использовались, dependencies/data не менялись, R1/M6/M8 отложены. Длительность отдельно не замерялась.

## R2: human gate конкретной версии research plan — 9 ноября 2026, 18:25 (Asia/Novosibirsk)

Research_plan gate CLI/MCP потребляет явно выбранный текущий structured operation/version, проверяет journal integrity/base inputs и сохраняет hash-bound ссылку в approval. Отсутствие selectors/человеческого имени, старый draft, changed inputs, busy lock и corrupt journal блокируют переход; legacy Markdown path сохранён только без committed structured плана. Общий OS lock охватывает gate и artifact writers. Все 234 unit-теста, включая восемь новых и real stdio, оба demo, Ruff/sync/repository/diff прошли; Markdown проверен после добавления отчёта. State/events ещё без multi-file atomic commit/recovery: это следующий R2-срез. Отчёт reports/2026-11-09-r2-research-plan-gate.md. DB/Docker/real LLM/.env/пользовательские данные не использовались/не менялись; R1/M6/M8 отложены. Длительность отдельно не замерялась.

## R2: write-ahead workflow recovery — 9 ноября 2026, 18:38 (Asia/Novosibirsk)

Gate state/events получили immutable before/after bundle с input hashes, ACTIVE guard, completion receipt, caller UUID replay/collision и optional gate-only expected_workflow_version. CLI workflow pending/recover и два файловых MCP tools используют отдельный recovery service/store; PG modules сохранены. Pending блокирует обычные файловые entry points, recovery проверяет scope/integrity и отказывает при посторонних edits. Все 244 теста, включая 10 новых crash/replay/conflict/concurrency/portable-copy/CLI/real-stdio, прошли; оба demo, Ruff/sync/repository/docs/diff прошли. Общая serializable транзакция остальных writers/readers ещё не реализована: их lock/read contract — следующий R2-срез. Отчёт reports/2026-11-09-r2-workflow-recovery.md, контракт docs/workflow-recovery.md. DB/Docker/real LLM/.env/зависимости/пользовательские данные не использовались/не менялись; R1/M6/M8 отложены. Длительность отдельно не замерялась.

## R2: общий read/write access lock — 9 ноября 2026, 18:48 (Asia/Novosibirsk)

Добавлен case_access с nonblocking OS lock, pending check после получения владения и reentrant synchronous thread/process scope. Подключены публичные файловые core функции, artifact/workflow stores, весь case dispatch CLI и inline MCP source list. Чтение при живом writer теперь получает busy; recovery не обходит активного владельца. Семь новых thread/process/nested/paused-mode/CLI/real-stdio тестов и весь набор 251 прошли; оба demo, Ruff/sync/repository/docs/diff прошли. Обновлены планы/README/контракты, отчёт reports/2026-11-09-r2-case-access.md. Остальные legacy writes ещё без write-ahead recovery: это следующий R2-срез, затем import/retire. DB/Docker/real LLM/.env/зависимости/пользовательские данные не использовались/не менялись; R1/M6/M8 отложены. Длительность отдельно не замерялась.

## R2: mode change через общий workflow recovery — 9 ноября 2026, 18:58 (Asia/Novosibirsk)

Смена режима перенесена на существующий write-ahead state/events bundle с ACTIVE/completion/recovery. Добавлены отдельные ModeChange, profiles, application service/port и kind-specific semantics; старые gate bundles без kind сохранены. CLI/MCP получили UUID replay/expected version, status показывает shared gate/mode workflow_version. Mode не меняет этап/approvals, minimum_sources/gap правила сохранены. Все 258 тестов, семь новых mode crash/replay/source/semantic/portable/CLI/real-stdio и целевой повтор прошли; оба demo, Ruff/sync/repository/docs/diff прошли. Обновлены планы/README/контракты; отчёт reports/2026-11-09-r2-mode-recovery.md. Далее source/revisit/render recovery, затем import/retire. БД/Docker/real LLM/.env/зависимости/пользовательские данные не использовались/не менялись; R1/M6/M8 отложены. Длительность отдельно не замерялась.

## R2: recoverable source revision review — 9 ноября 2026, 19:08 (Asia/Novosibirsk)

Review ревизии перенесён с одиночного append events на общий workflow state/events bundle, ACTIVE/completion/recovery, UUID replay и expected shared version. Добавлены отдельные domain command/dependency mapper, port/service и confined filesystem reader; legacy revisit wrapper стал тоньше. Проверяются current/archive hashes и полный explicit набор claims/decisions, включая option/rejected-alternative links; review меняет только workflow_version/updated_at и добавляет event, без stage/mode/approvals. Все 266 тестов, восемь новых crash/replay/dependency/hash/path/portable/semantic/CLI/real-stdio и целевой повтор прошли; оба demo, Ruff/sync/repository/docs/diff прошли. Обновлены планы/README/контракты, отчёт reports/2026-11-09-r2-revision-review.md. Далее — source import/revision creation recovery, затем остальные writers/import/retire. БД/Docker/real LLM/.env/зависимости/пользовательские данные не использовались/не менялись; R1/M6/M8 отложены. Длительность отдельно не замерялась.

## R2: source import/revision через workflow v2 — 9 ноября 2026, 19:25 (Asia/Novosibirsk)

Source add/fetch и создание revision перенесены на общий journal v2 с captured registry/current text/archive/event/state, derived targets, ACTIVE/completion и explicit recovery. Добавлены отдельные command/pure plan/service/ports/reader/codec; v1 bundles сохранены. CLI/MCP поддерживают UUID/expected version, exact replay до local/HTTP acquisition; changed/corrupt/unregistered targets не перезаписываются. Все 274 теста, восемь новых real-crash/replay/HTTP-mock/limits/conflicts/portable-copy/CLI/real-stdio и финальный targeted repeat прошли; review compatibility и оба demo прошли. Ruff/sync/repository/docs/diff прошли. Обновлены планы/README/контракты; отчёт reports/2026-11-09-r2-source-import-recovery.md. Далее render/остальные writers, затем mapping/import/retire. БД/Docker/real LLM/внешняя сеть/.env/зависимости/пользовательские данные не использовались/не менялись; R1/M6/M8 отложены. Длительность отдельно не замерялась.

## R2: recoverable render/adoption и manifest — 9 ноября 2026, 19:46 (Asia/Novosibirsk)

Render/adoption перенесены на workflow v3 bundle: generated Markdown, недостающие drafts templates, integrity manifest и state/events публикуются через общий ACTIVE/completion/recovery. Добавлены отдельные RenderRequest/pure plan, version-one builder/templates, port/service/codec, fixed target allowlist и semantic reconstruction. Existing drafts сохраняются, edits требуют explicit discard actor/reason с hashes в audit. CLI/MCP поддерживают UUID/expected version; compatibility manifest helper journaled как adoption. Набор 283 теста: первый full run 282 passed/1 CI demo error; после исправления optional capabilities ledger оба demo, все 6 CI tests и повтор 9 render tests прошли. Полный повтор 283 после fix не запускался. Ruff/sync/repository/docs/diff прошли; планы/README/контракты обновлены. Отчёт reports/2026-11-09-r2-render-recovery.md. Далее canonical ledger/usage recovery, затем mapping/import/retire. БД/Docker/real LLM/.env/зависимости/пользовательские данные не использовались/не менялись; R1/M6/M8 отложены. Длительность отдельно не замерялась.

## R2: canonical ledger/usage recovery — 10 ноября 2026, 00:47 (Asia/Novosibirsk)

Claims/gaps/options/decision-log/capabilities/usage перенесены на workflow v4 write-ahead append с typed payloads/pure builders, отдельными port/service/codec, фиксированным target и shared version/state/events. Replay UUID не дублирует запись; usage business ID отделён от journal UUID и не допускает double-count. CLI/MCP используют единые проверки, None/[] defaults канонизируются для cross-interface replay, owner/option/evidence и unknown cost правила сохранены. Полный набор 292 теста прошёл; финальные 9 ledger/crash/concurrency/usage/CLI/real-stdio tests повторены и прошли, оба demo/Ruff/sync/repository/docs/diff прошли. Обновлены планы/README/контракты, отчёт reports/2026-11-10-r2-ledger-recovery.md. Начатая итерация завершена; далее R2 inventory/parity/mapping/import/retire legacy. БД/Docker/real LLM/.env/зависимости/пользовательские данные не использовались/не менялись; R1/M6/M8 отложены. Длительность отдельно не замерялась.


## R2: файловый импорт документов — 10 ноября 2026, 01:09 (Asia/Novosibirsk)

PDF/DOCX/XLSX parsers подключены к файловому source service/journal v2 с typed document metadata, ограничениями extraction и точным page/cell verify. UUID replay и recovery не требуют исходного бинарного файла или повторного парсинга. Полный набор 301 теста прошёл; 9 новых document tests и оба demo прошли, model calls 0. Ruff/sync/docs/repository-history/diff проверки выполнены перед коммитом. Обновлены README, основной план и roadmap; созданы file-document-import и legacy-retirement contracts. Отчёт reports/2026-11-10-r2-file-documents.md. Далее public-HTTP policy/provenance и нужный mapping/import/parity/retire. БД не читалась, данные не переносились, Docker/real LLM/.env/зависимости не менялись; R2 открыт, R1 live/M6/M8 отложены. Длительность отдельно не замерялась.


## R2: public HTTP policy и provenance — 10 ноября 2026, 01:18 (Asia/Novosibirsk)

Файловый fetch использует shared public URL/DNS policy, pinned IP transport и strict HTML/text decoding; каждый redirect revalidated, credentials/private destinations/HTTPS downgrade запрещены. Добавлены отдельные web reader и typed offline capture metadata. Requested/final URL, MIME/charset/fetched_at/response SHA и extraction limits сохраняются в workflow v2; прежние receipts поддержаны без переписывания, replay/recovery не вызывают HTTP. Полный набор 311 тестов прошёл; 10 новых file-web, 16 web policy/transport и 8 source recovery tests прошли отдельно, оба demo прошли с 0 model calls. Ruff/sync/docs/repository-history/diff проверки прошли. Обновлены README/планы/контракты, отчёт reports/2026-11-10-r2-file-web.md. Далее ограниченный файловый поиск, нужный preflight и mapping/import/parity/retire. БД/real sites/Docker/LLM/.env/зависимости/пользовательские данные не использовались и не менялись; R2 открыт, live R1/M8 и M6 отложены. Длительность отдельно не замерялась.


## R2: поиск по файловым источникам — 10 ноября 2026, 01:31 (Asia/Novosibirsk)

Добавлены отдельные domain/service/port/files adapter и CLI/MCP модули: psa source search и psa_search_sources. Literal ignore-case поиск текущих hash-checked текстов, согласованный snapshot под общим lock, точные quotes/page/cell/paragraph locators, стабильный порядок и explicit truncation. Corrupt/missing/unsupported/over-limit corpus даёт ошибку без partial result; history/binaries/SQL/network/model/index writes отсутствуют. Полный suite 322 tests: OK, 1 skipped (Windows symlink privilege unavailable); targeted 11 tests: OK с тем же skip; остальные native-locator/verify, CLI/real-stdio parity, read-only/integrity/busy/bounds tests прошли. Оба demo прошли, 0 model calls. Ruff/sync/docs/repository-history/diff проверки прошли. Обновлены README/MCP docs/планы/legacy inventory, отчёт reports/2026-11-10-r2-file-search.md. Далее promise preflight/quality gate и mapping/import/parity/retire. БД/real sites/LLM/Docker/.env/зависимости/пользовательские данные не использовались и не менялись; R2 открыт, R1/M6/M8 отложены. Длительность отдельно не замерялась.


## R2: файловый promise preflight и quality gates — 10 ноября 2026, 01:50 (Asia/Novosibirsk)

Добавлены отдельные domain/port/service/files reader и CLI/MCP modules: psa promise check / psa_check_promises. Проверяются draft commitments, available capabilities, linked active facts без supersedes, точные locator quotes, current source hashes/revision events и v4 immutable claim bindings. Legacy unbound claims блокируются, approvals/bindings не выдумываются; explicit revision review не обновляет старый binding. Packet hash-bound/read-only, semantic/truthfulness/publication/workflow-approval flags false. Coverage/validate/verify и strategy/validation gates видят blockers; явный human gate сохраняет preflight hash в audit, historical UUID replay не выдаёт новое согласие. Полный suite: 332 tests OK, 1 skipped (Windows symlink privilege unavailable); final targeted 10 tests OK, оба demo OK с 0 model calls. Ruff/sync/docs/repository-history/diff проверки прошли. Обновлены README/MCP docs/планы/контракты; отчёт reports/2026-11-10-r2-file-promises.md. Далее нужные legacy данные/mapping/import/parity и retire PG/Alembic/Docker dependencies/CI с clean-install проверкой. БД/real cases/sites/LLM/Docker/.env/зависимости/пользовательские данные не использовались и не менялись; R2 открыт, live R1/M8 и M6 отложены. Длительность отдельно не замерялась.


## R2: вывод PG/Alembic/Docker runtime — 10 ноября 2026, 02:12 (Asia/Novosibirsk)

Пользователь подтвердил: в PostgreSQL только тестовые данные, сохранять не требуется. Удалены 108 tracked файлов старого PG/Alembic/Docker runtime, bootstrap/psa-main interfaces и DB-specific smoke scripts; SQLAlchemy/Alembic/psycopg и сопутствующие пакеты исключены из pyproject/lock, старые entrypoints и DB config defaults сняты. Пользовательские БД/volumes/backups/.env не читались и не удалялись; generalized import не выполнялся. CI/package/docs/README переведены на один файловый CLI и optional MCP; secret scanner native Gitleaks 8.30.1 с pinned official asset SHA, реальные history/tree/negative probes прошли без находок. AGENTS/canonical adapter sync обновлён. Сняты 18 tests старых dispatch/composition interfaces; domain/application tests сохранены, добавлены 4 retirement tests. Первый full314 и final full318 прошли (1 Windows symlink skip), Ruff/lock/docs166/sync/repository-history/diff прошли. Clean base (8 packages) прошёл completed workflow/copy resume без SQL/model/parser/MCP extras. Wheel и sdist установлены вне source tree и прошли doctor/help/оба demo/base workflow/copy resume с 0 model calls. Локальный archive dirty=true, тег/release не публиковались. Отчёт reports/2026-11-10-r2-runtime-retirement.md. R2 runtime завершён для текущего проекта; следующий R3 (стратегии/метрики/corrections), live R1/M8 и M6 не пройдены. Длительность отдельно не замерялась.


## R3: обязательные разделы стратегий — 10 ноября 2026, 23:25 (Asia/Novosibirsk)

Добавлены отдельные domain/port/service/files reader и CLI/MCP adapters: psa strategy check / psa_check_strategy. Проверяются восемь обязательных product/communication sections, plain RU/English H2 contract, prose вместо markers/placeholders/code/comments, duplicates и broken fences/comments. Hash-bound read-only report не выдаёт semantic/publication approval. Новые strategy/validation gates требуют полную структуру и сохраняют отдельный structure review hash; прежние promise/coverage checks остаются, frozen render/templates и historical journal/replay не переписываются. Обновлены CI/base/gate synthetic fixtures, README/MCP docs/планы и agent/quality.md; sync --write пересобрал9 generated adapters с новым canonical digest, --check прошёл. Новые8 structure tests и повтор10 promise tests прошли; full326 OK с1 Windows symlink skip, оба demo и base completed/copy-resume без SQL/model extras прошли. Native Gitleaks history/tree/negative probes без находок, Ruff/docs168/repository-history/sync/diff проверки прошли. Отчёт reports/2026-11-10-r3-strategy-structure.md. R3 открыт: далее metrics/unit/population/baseline/window/guardrails/owner/data source, semantic consistency и corrections. БД/Docker/.env/real cases/LLM не использовались и не менялись; live R1/M8 и M6 не пройдены. Длительность отдельно не замерялась.


## R3: typed measurement plan и future production roadmap — 10 ноября 2026, 23:45 (Asia/Novosibirsk)

Добавлены отдельные domain schema/parser/report, port/service/files store и CLI/MCP adapters: psa validation check / psa_check_validation_plan. В authored validation Markdown один psa-validation-v1 JSON block: hypothesis/change, metric definition/unit/population/data source, comparison/criterion, observation window, guardrails/stop rules и owners/decision rule. Baseline reported требует finite number/current active fact с v4 binding/exact quotes/source revisions; unknown — null/reason/method/owner/aware deadline. Numeric/semantic alignment, observed effect и permission не присваиваются. Новый validation gate сохраняет отдельный review hash; journal/case schema/frozen render и historical replay неизменны. Обновлены base/gate fixtures, README/MCP/quality docs/планы, 9 generated adapters пересобраны. Full336 OK с1 Windows symlink skip; первые9 новых tests отдельно OK, все10 вошли в full; base completed/copy resume без SQL/model extras, оба demo и native Gitleaks history/tree/negative probes прошли с0 model calls/без находок. Ruff/docs170/repository-history/sync/diff checks прошли. В основной план и roadmap записан будущий полный production-ready пересмотр после R3: subagents/hooks, CLI/FastMCP/host parity, tooling/retrieval, hardening/privacy/recovery, observability/cost, release/rollback и hackathon eval/demo milestones; это не готовность/гарантия победы, AGENTS opt-in ограничения сохранены. Отчёт reports/2026-11-10-r3-validation-plan.md. Далее semantic/numeric consistency и corrections/withdrawal; R3 открыт, live R1/M8 и M6 не пройдены. БД/Docker/.env/real cases/LLM не использовались и не менялись; длительность отдельно не замерялась.


## R3: claim withdrawal/effective evidence — 11 ноября 2026, 00:14 (Asia/Novosibirsk)

Добавлены отдельные model/projection/guards/port/service и CLI/MCP: claim withdraw/impact, psa_withdraw_claim/psa_claim_impact. Actor/reason обязательны; запись append-only в v1 state/events journal со snapshot/hash, expected version, UUID replay и pending/recover. Raw claims/sources/capabilities/options/decisions/approvals неизменны; derived inactive/needs_review не меняет человеческий выбор. Coverage/verify/promise/baseline/current-decision gates и новые supporting links учитывают effective status; CLI status/resume и critic-pack показывают audit. Renderer v2 исключает inactive statements из текущих оснований, маркирует affected capabilities/options/decision, хранит audit; frozen v1/historical receipts replay сохранены, после withdrawal новый validation gate требует свежую v2 generation. Full346 tests OK с1 Windows symlink skip; targeted10 withdrawal и9 render/recovery OK, base completed/copied resume без SQL/model extras, оба demo и native Gitleaks history/tree/negative probes прошли. Ruff/docs172/repository-history/sync/diff checks прошли; 9 adapters пересобраны после quality canon update. Отчёт reports/2026-11-11-r3-claim-withdrawal.md. R3 открыт: далее audited correction/supersede, source withdrawal, review/reopen и semantic/numeric consistency; production-ready roadmap сохранён, live R1/M8 и M6 не пройдены. БД/Docker/.env/real cases/LLM не использовались и не менялись, пользовательские данные не удалялись; длительность отдельно не замерялась.


## R3: audited claim correction — 11.11.2026 00:37 (Asia/Novosibirsk)

Добавлены psa claim correct / psa_correct_claim, отдельные domain/service/port/files codec, workflow v5 claims/state/events recovery и actor/reason/snapshots/hashes/impact. Original claims и решения/approvals сохраняются; current exact citations проверяются перед публикацией, v5 evidence binding поддержан в promises/reported baseline. Ветвление запрещено, withdrawn original не оживляется; после correction новый validation gate требует свежий render v2. Base smoke проходит через исправление. Quality canon, 9 adapters, docs и оба плана обновлены.

Проверки: полный suite 354 tests, 437.485 s, OK (1 skipped: Windows symlink privilege unavailable); targeted 8 tests, 48.234 s, OK, включая реальные process interruptions на семи границах и CLI/FastMCP stdio parity. Чистое base environment completed/copy-resume OK; оба demo OK, 0 model calls. Ruff/check formatting, instruction sync, docs174, repository-history, diff check и native Gitleaks 8.30.1 history/tree/negative probes прошли. Live R1/M8 и independent M6 отложены. Далее R3: явный review/reopen, source withdrawal и semantic/numeric alignment. Реальные кейсы/.env/БД не читались/не менялись, LLM API не вызывался; длительность итерации и стоимость IDE отдельно не измерялись. [Отчёт](2026-11-11-r3-claim-correction.md).


## R3: явный workflow review/reopen — 11.11.2026 00:55 (Asia/Novosibirsk)

Добавлены workflow review/reopen CLI и psa_review_workflow/psa_reopen_workflow FastMCP, отдельные domain planner/service/port и filesystem decision-proof reader. Snapshot review hash охватывает state/events/non-journal inputs; reopen требует actor/reason/target/hash/version и explicit human instruction по политике. Только completed workflow: выбранный stage in_progress, последующие not_started; approvals/choices сохраняются в истории. Общий workflow v1 journal с полным deterministic reconstruction/recovery/replay; historical v1–v5 не менялись. Новое решение после возврата к strategy/раньше подтверждается reconstructed ledger result/receipt, учитывая legacy v4 record_id=option_id; новый validation требует свежий render v2. Base smoke проверяет полный reopen/redecision/regate/recomplete/copy-resume путь.

Проверки: full360, 463.366 s, OK (1 Windows symlink skip); final targeted6, 54.755 s, OK, включая реальные process interruptions на 6 границах, copy/recover/later writes, rehashed bundle tamper, dirty draft/hash/version/actor/busy, altered decision proof и CLI/real MCP parity. Чистый base smoke и оба demo OK, 0 model calls. Ruff/formatting/sync9/docs176/repository-history/diff и native Gitleaks 8.30.1 history/tree/negative probes прошли. В первых прогонах исправлены CLI fixture invocation/option selection, предположение о v4 event record_id и shared-lock reader argument name. Quality canon/adapters/docs и оба плана обновлены. Далее source withdrawal и semantic/numeric alignment; active-workflow rollback, live R1/M8 и independent M6 открыты. Реальные кейсы/.env/БД не читались/не менялись, LLM API не вызывался; длительность/стоимость IDE отдельно не измерялись. [Отчёт](2026-11-11-r3-workflow-reopen.md).


## R3: source withdrawal и evidence impact — 11.11.2026 01:21 (Asia/Novosibirsk)

Добавлены psa source withdraw/impact и psa_withdraw_source/psa_source_impact FastMCP, отдельные domain/service/port/files codec. Workflow v6 сохраняет source snapshot/hash/actor/reason/time/impact и captured ledgers; публикует только state/events, old v1–v5 receipts сохранены. Registry/text/archive/claims/choices/approvals не переписываются. Derived source_withdrawn claims и их зависимости блокируются coverage/promises/baseline/support/gates; withdrawn sources исключены из search/citation hits, source integrity проверяется и для них. Новые refs/import/revision не реактивируют источник; old import UUID replay сохранён. Renderer/list/critic показывают effective evidence/audit; validation требует свежий render v2. Canon/adapters/docs/оба плана обновлены.

Проверки: full367, 819.079 s, OK (1 Windows symlink skip); targeted7, 33.740 s, OK. Реальные process interruptions на 6 границах, copy/recover/later writes, byte/choice preservation, malformed actor/version/busy/duplicates, metadata/rehashed impact tamper, supporting/baseline guards, независимый correction и CLI/real stdio parity. Первый targeted run обнаружил ошибку JSONL test fixture, исправлено; начатый full run перезапущен. Clean base с v6 и reopen/redecision/recomplete/copy-resume OK; оба demo OK, 0 model calls. Ruff/sync9/docs178/repository-history/diff/native Gitleaks 8.30.1 history/tree/negative probes прошли. Далее semantic/numeric alignment и новый разрешённый кейс; source reactivation, active workflow rollback и live R1/M8/independent M6 остаются открытыми. Реальные кейсы/.env/БД не читались/не менялись; платные API/модели не вызывались. Стоимость и длительность IDE-сессии отдельно не измерялись. [Отчёт](2026-11-11-r3-source-withdrawal.md).


## R3: numeric baseline literal preflight — 11.11.2026 01:33 (Asia/Novosibirsk)

По просьбе пользователя итерация разделена на небольшие смысловые коммиты: ac8566d — domain numeric anchor/parser/report + service и 7 tests; 361b88b — CLI validation numbers, FastMCP psa_check_baseline_numbers и real stdio parity; отдельный documentation/report commit обновляет quality canon/9 adapters/docs/оба плана. Проверяются author-selected number/unit spans в exact recorded current citation, Decimal value/единица и active factual/source proof; explicit decimal separator, без rounding/scaling. Literal match не подтверждает semantic/numeric alignment или experiment/workflow permission. Unknown baseline not_applicable; stale/withdrawn/unbound/mismatched inputs blocked. Пока отдельный read-only check, не новый обязательный gate.

Проверки: 8 новых domain/CLI/real MCP tests, 27.571 s, OK; 10 existing validation regression tests, 21.795 s, OK. В clean base без model/MCP/SQL extras 7 numeric tests, 12.061 s, OK и полный workflow/reopen/redecision/recomplete/copy-resume OK. Оба demo OK, 0 model calls. Ruff/sync9/docs180/repository-history/diff и native Gitleaks 8.30.1 history/tree/negative probes прошли. Полный suite в этой итерации не запускался; последний full367 относится к предыдущему source withdrawal срезу. Далее human semantic review с audit/freshness, более широкий numeric alignment и gate integration; R3/new-case acceptance, live R1/M8 и independent M6 остаются открытыми. Реальные кейсы/.env/БД не читались/не менялись, платные API/модели не вызывались; длительность/стоимость IDE отдельно не измерялись. [Отчёт](2026-11-11-r3-baseline-numbers.md).


## R3: human semantic audit и gate adoption — 11.11.2026 20:11 (Asia/Novosibirsk)

Смысловые коммиты: 25cc0d8 — domain/content binding, service/port, files audit/proof, workflow v7 reconstruction/recovery и первые 6 tests; 9a89b89 — CLI/MCP prepare/record, explicit gate selector/reference, cross-scope freshness/rejection guard, integration tests и clean-base smoke. Отдельный docs/report commit обновляет canon/9 adapters/contracts/планы/отчёт. Human actor/reason/verdict/6 strict checks/hash/version обязательны; accepted review не записывается с structural/evidence/numeric blockers. Record не меняет stage/approvals/decisions, не разрешает публикацию/эксперимент. После adoption latest accepted/current review UUID выбирается явно, strategy adoption также действует на validation; новое strategy review инвалидирует старое validation review. Recovery gate проверяет dependency bundle/receipt. Legacy без audit сохраняет прежний путь; global policy migration открыта.

Проверки: full386, 614.179 s, OK (1 Windows symlink skip); final targeted11, 83.912 s, OK. Реальные process interruptions review на 6 границах, copy/recover/later writes, immutable audit/tamper, current content vs render metadata, rejected/stale/old selector bypass, numeric reported baseline blockers, gate recovery без dependency receipt и CLI/real MCP parity. В анализе закрыт межэтапный обход strategy rejection через старое validation review; начатый full run перезапущен на окончательном коде. Clean base workflow с v7 assessments/gates/reopen/redecision/recomplete/copy-resume и оба demo OK, 0 model calls. Ruff/sync9/docs182/repository-history/diff/native Gitleaks 8.30.1 history/tree/negative probes прошли. Далее новый разрешённый кейс, более широкий numeric alignment и legacy policy migration; live R1/M8 и independent M6 не закрыты. Реальные кейсы/.env/БД не читались/не менялись, платные API/модели не вызывались; все тестовые actor/checklists синтетические, не product acceptance. Длительность и стоимость IDE-сессии отдельно не измерялись. [Отчёт](2026-11-11-r3-semantic-review.md).


## R3: required quality policy и завершение legacy enablement — 14.11.2026 19:22 (Asia/Novosibirsk)

Итерация начата 11.11, возобновлена и завершена 14.11 после прерванного full run без итоговой сводки. Смысловые code commits: e6219b6 — current init seed/receipt v2/strict policy model и frozen legacy support; 7a95cc5 — required first strategy/validation gate и snapshot-bound legacy enablement с workflow v1 recovery; 9d70167 — policy show/enable CLI и psa_quality_policy/psa_enable_quality_policy FastMCP; e03d326 — запрет policy changes в unrelated workflow after-state даже при rehashed manifest. Заключительный docs/report commit обновляет canon/9 adapters/README/contracts/оба плана. Code commits уже были на origin при возобновлении.

Новые public init cases требуют current accepted semantic review с первого strategy/validation gate. Explicit legacy enable требует actor/reason/snapshot hash/version, сохраняет stage/approvals/choices, делает прежние semantic assessments stale; old gate/init replay не сбрасывает later state. Null/unknown/removed policy не трактуется как legacy; receipt v2 и enablement history предотвращают штатный downgrade. Нет disable/автоматической массовой миграции; пользовательские кейсы/demo не мигрировались. В semantic-review doc исправлен CLI пример: --stage вместо позиционного stage.

Проверки: full397, 649.646 s, OK (1 Windows symlink skip) на окончательном коде 14.11; ранее targeted11, 115.305 s, OK; existing workspace11, 19.217 s, OK; real policy stdio parity1, 17.380 s, OK; isolated gate after-state negative1, 6.562 s, OK. Реальные interruptions на 6 границах, copy/recover/later writes, stale/removed/malformed policy, historical gate replay, immutable after-state tamper проверены. Clean base и оба demo прошли на окончательном коде до перерыва, model calls=0. После возобновления Ruff/sync9/docs184/repository-history/native Gitleaks 8.30.1 history/tree/negative probes снова прошли; код не менялся. Реальные кейсы/.env/БД не читались/не менялись, платные модели/API не вызывались. Новый разрешённый кейс и более широкий numeric alignment остаются открытыми, live R1/M8 и independent M6 не закрыты. Длительность и стоимость IDE-сессии отдельно не измерялись. [Отчёт](2026-11-11-r3-quality-policy.md).

## 14.11.2026 19:58 (Asia/Novosibirsk) — R3: current-evidence calculation check

Реализован строгий author-selected psa-calculations-v1: процентная доля, отношение, процентные пункты и относительное изменение. Точные Decimal → Fraction вычисления, явное half_even округление, current factual citation/span binding, единицы и авторские context/period labels; malformed/null/duplicate blocks, stale/withdrawn evidence, неверный знаменатель/результат блокируются. CLI psa validation calculations и FastMCP psa_check_calculations read-only и возвращают одинаковый packet. Semantic validation review не принимает accepted assessment при calculation blockers; historical completed gate replay не меняет поздние файлы. Новые state/journal formats не добавлены.

Смысловые коммиты: ecb9023 — domain/application; 8b1d88e — CLI/MCP и stdio parity; 845fe6e — semantic validation acceptance/replay; 7c9e696 — mixed-unit/cross-period negative tests. Отдельный docs/report commit обновляет canon/9 adapters/contracts/README/оба плана; в начале основного плана исправлен устаревший статус выведенного PG runtime.

Проверки: full407, 943.953 s, OK (1 Windows symlink skip); core8, 25.308 s, OK; targeted core7+stdio1+gate1, 34.309 s, OK. В clean base без MCP/model/SQL extras core8, 316.476 s, OK; полный workflow completed/reopen/reapprove/copy/resume прошёл. Оба demo прошли без моделей и изменения оригиналов. Ruff/sync9/docs186/repository history/native Gitleaks 8.30.1 history/tree/negative probes — OK. Semantic/numeric alignment/context truth/effect/permissions не подтверждаются арифметикой. Новый разрешённый кейс, numeric coverage произвольного prose, live R1/M8 и независимая M6 остаются открытыми; unfinished workflow rollback — отдельный R4. Реальные кейсы/.env/БД не читались/не менялись, платных model/API calls нет; test actors/approvals только synthetic. Длительность и стоимость IDE-сессии отдельно не измерялись. [Отчёт](2026-11-14-r3-calculation-check.md).

## 14.11.2026 20:08 (Asia/Novosibirsk) — R3: raw draft digit inventory

Добавлена read-only инвентаризация digit tokens трёх author drafts: отдельные domain/application port/service/files adapter; bounded existing readers под общим case lock, workflow/state freshness, координаты Unicode/CRLF и bounded context с hashes. CLI psa strategy numeric-inventory и FastMCP psa_numeric_inventory возвращают один packet. IDs/dates/URLs/code/comments остаются видимыми и unassessed. Missing draft — blocked/exit3; pending/invalid state/path и file/token/packet overflow — ошибка без partial report. Numeric coverage/evidence/arithmetic/approval всегда false; нет auto-approval, новых journal/state formats и записи в кейс.

Коммиты: d5aa30c — core/adapter/первые тесты; 676e939 — CLI/MCP/real stdio; 9f97d46 — pending/invalid state отрицательные проверки. Заключительный docs/report commit обновляет canon/9 adapters/README/MCP/основной план/roadmap. Проверки: новые9, 7.069 s, OK; existing strategy/calculation stdio/case access16, 25.163 s, OK; clean base9, 0.928 s, OK (1 MCP-extra skip), полный base workflow completed/reopen/reapprove/copy/resume OK, model_calls=0. Ruff/sync9/docs188/repository history/native Gitleaks 8.30.1 history/tree/negative probes — OK. Предыдущий full407 не выдаётся за полный прогон новой версии: в этой итерации выполнены targeted tests и meaningful smoke.

Новый разрешённый кейс и содержательная numeric coverage остаются открытыми; R3 не завершён. Live R1/M8 и independent M6 не закрыты; unfinished workflow rollback — отдельный R4. Реальные кейсы/.env/БД не читались/не менялись, платных model/API calls нет; test actors только synthetic. Длительность и стоимость IDE-сессии отдельно не измерялись. [Отчёт](2026-11-14-r3-numeric-inventory.md).

## 14.11.2026 20:29 (Asia/Novosibirsk) — R4: explicit active workflow rollback

Реализован явный backward-only workflow rollback: отдельные model/planner/service, current review hash/version/actor/reason, caller UUID и общий v1 journal с deterministic after-state/event reconstruction. Target должен быть строго раньше текущего активного этапа; same/forward/completed/inconsistent stages отвергаются. Материалы/реестры/decisions/approvals/reopen history сохраняются; suffix stages reset и rollback_history/event показываются в CLI resume/MCP status/review. Новые strategy/validation gates требуют нового явного решения после возврата, fresh render и обязательных current semantic assessments. Required policy сохраняется, rollback инвалидирует semantic content binding; old completed rollback/gate/semantic replay не сбрасывает поздние writes. Frozen v1–v7 history и старый semantic hash без rollback_history поддержаны; новые rollback receipts требуют обновлённый runtime.

Коммиты: e0dbd86 — core/journal/gates/7 tests; 448d11b — CLI/FastMCP/status/resume/stdio; 8bb1e11 — required-policy/fresh-review integration и уточнение guard messages. Заключительный docs/report commit обновляет workflow/quality canon/9 adapters/contracts/README/MCP/оба плана. Проверки: core7, 51.556 s, OK; policy/CLI/real stdio3, 20.502 s, OK; real crashes на preparation/ACTIVE/state/events/receipt/completion с copy/recover/later writes; clean base10, 63.129 s, OK (1 MCP-extra skip). Full426, 804.799 s, OK (1 Windows symlink skip) на окончательном коде. Ruff/sync9/docs190/repository history/native Gitleaks 8.30.1 history/tree/negative probes — OK.

R4 начат техническим срезом; R3 новый разрешённый кейс/numeric coverage, live R1/M8 и independent M6 остаются открытыми. Реальные кейсы/.env/БД не читались/не менялись, платных API/model calls нет; test actors/approvals только synthetic. Длительность и стоимость IDE-сессии отдельно не измерялись. [Отчёт](2026-11-14-r4-workflow-rollback.md).

## 14.11.2026 20:33 (Asia/Novosibirsk) — план R3.1: субагенты и хуки после R3

По прямому указанию пользователя в основной план и roadmap добавлен самостоятельный этап R3.1 непосредственно после R3 и перед продолжением R4. Зафиксированы роли research/evidence/critic, hooks validation/revisit/release, contracts/provenance/permissions/budgets, idempotency/failure/injection/timeout checks, host adapters/runbook, opt-in activation и последовательный fallback. Production roadmap должен сохранить этот порядок. Выполненный rollback R4 не отменён; R3 и отложенные R1/M6/M8 не закрыты. Это docs-only изменение, без запуска/реализации hooks/subagents или изменения runtime/canon/кейсов. Unit suite повторно не запускался; sync9/docs191/Ruff и git diff --check — OK. [Отчёт](2026-11-14-plan-hooks-subagents.md).

## 14.11.2026 20:39 (Asia/Novosibirsk) — R3: existing demo audit / case check protocol

Выполнены 20 read-only CLI проверок demo/table-demo. Validate/verify/coverage проходят у обоих; новый validation contract отсутствует у обоих (check/numbers/calculations blocked, exit3). Demo strategy structure complete; table-demo incomplete по 8 sections и validation semantic packet сообщает C-001 evidence snapshot missing / stale_or_unbound. Review prepare exit0 не означает accepted review; digit inventory 4/15 tokens остаётся needs_human_review. Legacy status completed не закрывает R3. Кейсы/реестры/policy/approvals не мигрировались, новый кейс не создан: пользователь сообщил, что опишет его, описание пока ожидается.

Добавлен docs/r3-case-check.md и ссылки/фактические результаты в оба плана. Протокол отделяет механические проверки, содержательную оценку, выбор человека и independent R5, сохраняет human gates и условия R3 → R3.1. Python runtime/canon не менялись; full unit suite не повторялся, meaningful smoke — 20 реальных CLI вызовов. Документационные проверки: sync9/docs193/Ruff и git diff --check — OK. Нет моделей/API/БД/.env и запуска hooks/subagents; R1/M6/M8 не закрыты. [Отчёт](2026-11-14-r3-existing-demo-audit.md).

## 14.11.2026 20:53 (Asia/Novosibirsk) — R3: полный synthetic кейс «Слот»

По прямому запросу пользователя придуман полный кейс студии мастер-классов: ручной перенос / отказ от self-service / узкий перенос без платежей. Пакет examples/slot-workshop содержит brief/research/materials/options/условные стратегии/measurement/calculations/methods и build_case.py; локальный projects/slot-workshop-synthetic исключён из Git. Источники/7 claims/3 gaps/3 options/2 capabilities/render созданы публичными сервисами. Три factual claims относятся только к содержанию вымышленного файла, synthetic обстоятельства отдельно типизированы. 40/200=20% — учебная арифметика, реальный baseline unknown. Stage intake, required policy, decisions/approvals=0; human choice/semantic gates не выдуманы.

Кейс выявил relative-path bug quality policy в default validate/verify. Исправлено Path.absolute перед confined guard, без обхода path checks; 95b6078. Пакет synthetic case — 7d89a7e. Проверки: new relative tests2, 0.491 s, OK; all policy13, 59.147 s, OK. Новый case CLI validate/verify/coverage/strategy/validation/calculations прошёл; numbers not_applicable, inventory91 needs_human_review; semantic prepare корректно блокируется отсутствующим человеческим выбором. Clean base: fresh build, 2 overwrite refusals без изменений, copy + 4 read-only checks, model calls0/approvals0. Ruff/sync9/docs201/repository history и native Gitleaks 8.30.1 history/tree/negative probes — OK. Full426 не повторялся; R3/R1/M6/M8 не закрыты, hooks/subagents не запускались. [Отчёт](2026-11-14-r3-slot-synthetic-case.md).


## 14.11.2026 21:07 (Asia/Novosibirsk) — R3: explicit human choice/gates/reviews, synthetic workflow completed

Пользователь явно выбрал O-003 и утвердил пять подготовительных gates от роли «Пользователь». Штатными сервисами записаны GATE-001…005 и D-001; после выбора применён psa-strategy, обновлены authored drafts/notes и render. Strategy packet v27/hash4146846e… показан человеку: приняты все шесть критериев и разрешён gate; SEMANTIC-0001/63e7d7a6-8da5-53ff-ac99-cc92ef3b18eb. Свежий validation packet v30/hash2c1b9705… отдельно принят по всем шести критериям с разрешением gate; SEMANTIC-0002/89de70f4-82cc-5505-9471-52290c0e8c87. Checks не подставлены до ответов пользователя. Итог local case: completed/version32, 7 approvals, все stages done, required policy сохранена.

Проверки: final validate/verify/resume; оба current review proof через for_gate; 3 historical completed receipt replays; перенос completed case + 9 read-only CLI команд и оба review proofs в копии. Hashes всех файлов оригинала/копии не изменились. R3 функционально пройден только на synthetic кейсе, без доказательства спроса/эффекта и разрешения реального пилота. Следом production roadmap и R3.1 contracts/subagents/hooks; live R1/M8/independent M6 не закрыты. Локальный case/approval journals не коммитятся; исходный example builder сохраняет unapproved default. Runtime не менялся, unit suite не перезапускался. docs202/sync9/Ruff и git diff --check — OK. [Отчёт](2026-11-14-r3-slot-human-acceptance.md).


## 14.11.2026 21:19 (Asia/Novosibirsk) — R3.1/P0: production roadmap и strict automation contracts

Подготовлен docs/solution_plans/production-readiness.md: P0–P9/dependencies/DoD/risks/capability matrix, сохраняя IDE-native/file-only/CLI-FastMCP и opt-in последовательный fallback. Контракт docs/automation-contracts.md реализован отдельными domain/automation modules: bounded packets, roles/excerpts/hash, task/result binding, nullable usage и reported-budget guards; hook triggers/targets/request binding/mandatory failure policy. Никакого runtime dispatcher/executor/native activation и actual resource enforcement пока нет. UUID/snapshot/role/permissions от untrusted input не дают human approval.

Коммиты: 39450f0 — план/спецификация; 69c31b3 — модели/guards/12 tests; 224a1f3 — strict JSON boundary regression; заключительный docs/report commit обновляет статусы и timestamp. Проверки: final targeted12, 0.020 s, OK; final clean base12, 0.025 s, OK; existing base completed/reopen/reapprove/copy/resume OK, model_calls0. Ruff/sync9/docs205/repository history и native Gitleaks 8.30.1 history/tree/negative probes — OK. Full suite не повторялся для не подключённых к runtime domain modules; meaningful tests проверяют negative boundaries и baseline smoke. Далее P1 snapshot/handoff service + role instructions + read-only CLI/MCP preparation, затем P2/P3/P4. R1/M6/M8 не закрыты. Кейсы/БД/.env не читались/не менялись; agents/hooks/models/API не запускались. [Отчёт](2026-11-14-r31-automation-contracts.md).


## 15.11.2026 17:21 (Asia/Novosibirsk) — R3.1/P1: read-only handoffs завершены

Завершён начатый 14.11 P1: versioned research/evidence/critic profiles с canon sync; coherent selected-material snapshot и provenance/ranges; HandoffService/port/readers, CLI subagent prepare и FastMCP psa_prepare_subagent. Пакет не запускает/не сохраняет задачи и не пишет в канон. Role/selection hashes связаны с task fingerprint; source lifecycle/hash, Unicode/CRLF, limits и shared pending/busy guards проверены. Диагностика не отражает validation input values. Кодовые commits b7939ae / 2bd617d / 51f54d2 / d46a8c4 сохранены, заключительный docs/report commit обновляет runbook и планы P1 complete / P2 next.

Финальные проверки заново после перерыва: 34 tests, 19.088 s, OK (P1/P0/instruction sync/real CLI-MCP); clean base14, 7.562 s, OK (1 MCP-extra skip), existing base completed/reopen/reapprove/copy/resume OK, model_calls0. Ruff/sync9/docs210/repository history, git diff --check и native Gitleaks 8.30.1 history/tree/negative probes — OK. Общий full suite не повторялся; реальных субагентов/моделей/hooks/native hosts не запускали. R1/M6/M8 открыты. Рабочие кейсы/секреты/.env не читались/не менялись. Далее P2 result journal/provenance/current-input checks и replay/conflict, затем P3 hooks/P4 native adapters. [Отчёт](2026-11-15-r31-subagent-handoffs.md).


## 15.11.2026 17:54 (Asia/Novosibirsk) — R3.1/P2: task/result/review journal

Реализованы immutable isolated records, parent/snapshot/budget guards, exact historical replay и явное pending/recovery. CLI и восемь FastMCP tools используют общее файловое ядро; result review не меняет канон и не подменяет human semantic acceptance. Crash/copy tests подтверждают восстановление шести границ публикации без потери последующих writes; прежние human reviews сохраняют силу. Коммиты c639c25 / a8cd37f / 077f2e4; заключительный docs commit обновляет runbook/планы.

Проверки: P2 12 (33.001 s), P1 14 (13.995 s), P0 12 (0.018 s) — OK; clean base12 (26.607 s, 1 MCP skip), base completed/reopen/reapprove/copy/resume OK, model_calls0. Ruff/sync9/docs/secret history/tree/negative probes и diff checks OK. Full suite не повторялся. Native execution/enforcement не реализованы, agents/hooks/models не запускались; R1/M6/M8 открыты. Далее P3 local hooks. [Отчёт](2026-11-15-r31-subagent-journal.md).


## 15.11.2026 18:02 (Asia/Novosibirsk) — R3.1/P3a: явный gate preflight

Добавлены read-only strategy/validation preflight, coherent hash/version/shared lock, фиксированные существующие checks, stale/recursion guards и безопасная диагностика. CLI prepare/check и FastMCP psa_prepare_hook/psa_check_hook имеют real-stdio parity; blocked/failed CLI exit1. Passed не подменяет human semantic review/gate, что проверено на обоих этапах. Коммиты 3b0d405 / 04ac679; итоговый docs commit фиксирует runbook и планы.

Проверки: P3a12 (22.831 s), P2 regression12 (33.803 s), P0 contracts12 (0.021 s), P1 CLI/stdio2 (8.837 s) — OK; clean base12 (13.959 s, 1 MCP skip), base smoke completed/copy/reopen/reapprove OK, model_calls0. Ruff/sync9/docs/secret history/tree/negative probes и diff checks OK. Full suite не повторялся. P3 ещё открыт: timeout/lifecycle/replay, notifications и release checks впереди; native activation выключена, R1/M6/M8 открыты. Рабочие кейсы/секреты не изменялись. [Отчёт](2026-11-15-r31-hook-preflight.md).


## 15.11.2026 18:15 (Asia/Novosibirsk) — R3.1/P3b: bounded hook execution/journal

Реализованы fixed worker с process timeout/watchdog, durable intent/completion, UUID/request/timeout conflicts, explicit recovery без повторного исполнения и historical replay с required_check_passed=false. CLI run/show/pending/recover и четыре FastMCP tools используют общие services; live check P3a сохранён. Current snapshot проверяется перед запуском и публикацией, gate/semantic approval не выдаётся. Коммиты 5952617 / a9862b1 / f844303; итоговый docs commit обновляет план и runbook.

Проверки: P3b11 (56.145 s), финальные core8 (29.817 s)/stdio2 (16.434 s), P3a12 (22.002 s), P012 (0.020 s) — OK; clean base11 (44.138 s, 1 MCP skip), base smoke completed/copy/reopen/reapprove OK, model_calls0. Fresh MCP worker, timeout/watchdog и три kill/copy boundaries проверены. Ruff/sync9/docs/native secret history/tree/negative probes и diff checks OK. Full suite не повторялся. P3 source notifications/release checks впереди; native activation выключена, R1/M6/M8 открыты. Рабочие кейсы/секреты не изменялись. [Отчёт](2026-11-15-r31-hook-runs.md).


## 15.11.2026 18:27 (Asia/Novosibirsk) — R3.1/P3c: source revision notifications

Добавлены bounded source notice поверх существующего revisit, отдельные port/service/reader, явные CLI prepare-notification/FastMCP prepare + общий worker/run journal. notification_delivered отделён от required_check_passed; domain helper запрещает source notices как required checks. Ошибка не откатывает committed import, не закрывает human review и не утверждает gate. Captured-copy recovery остаётся historical без delivery. Коммиты eb9971c / 89be4a7; итоговый docs commit обновляет план/runbook.

Проверки: source11 (52.429 s), before-gate runtime11 (118.830 s), P012 (0.033 s) — OK; clean base11 (34.956 s, 1 MCP skip), base smoke completed/copy/reopen/reapprove OK, model_calls0. Ruff/sync9/docs/native secret checks и diff checks OK. Full suite не повторялся. P3 release checks впереди; auto activation выключена, R1/M6/M8 открыты. Рабочие данные/секреты не изменялись. [Отчёт](2026-11-15-r31-source-notifications.md).


## 15.11.2026 18:43 (Asia/Novosibirsk) — R3.1/P3d: offline release hooks

Общие allowlist/required files и bounded archive inspector подключены к package/verifier; добавлены port/service/ReleaseRun, fixed read-only worker и CLI/FastMCP prepare-release/check-release. Hash/schema/SHA256SUMS/external assets, dirty/stale/tampering и безопасные paths проверяются без исполнения архива, установки или публикации. Release check live/stateless, case journal не меняется. Коммиты bd6be92 / ebb430d / 370ee65; итоговый docs commit сохраняет runbook и планы.

Проверки: release10 (27.056 s), distribution5 (1.127 s), P012 (0.032 s), прежний CLI/stdio2 (25.120 s) — OK; clean base10 (11.054 s, 1 MCP skip). Реальная offline clean-commit сборка370ee65, bounded hook passed, затем отдельный full wheel/sdist install/demo/base verifier OK, model_calls0. Ruff/sync9/docs/native secret history/tree/negative probes/diff OK. Full unit suite не повторялся. Локальный P3 реализован; далее P4 capability/adapters/fallback, R3.1 и R1/M6/M8 открыты. Tag/draft/publish и native activation не выполнялись, рабочие данные/секреты не изменялись. [Отчёт](2026-11-15-r31-release-hooks.md).


## 15.11.2026 18:56 (Asia/Novosibirsk) — R3.1/P4a: host matrix и fallback plans

Добавлены canonical schema1/catalog1.0.0 profiles пяти IDE с all-native not_verified, strict scoped plans и bounded reader. Native request предлагает последовательный fallback без activation/config writes/execution/permissions; наличие instruction files отделено от host loading. CLI host list/inspect/plan и три read-only FastMCP tools имеют real-stdio parity. Canon sync пересобрал9 adapters; host catalog не autoload в case context. Коммиты ad9f2cf / 99dc876 / 1fbe8ff; заключительный docs commit обновляет runbook/планы.

Проверки: host9 (14.113 s), context8 (5.443 s), P012 (0.030 s) — OK; clean base9 (3.123 s, 1 MCP skip), base completed/copy/reopen/reapprove OK, model_calls0. Ruff/sync9/docs/native secret history/tree/negative probes/diff OK; full suite не повторялся. P4 открыт: далее evidence/config previews, затем проверенные native adapters/activation/migration. Native/live R1/M6/M8 не закрыты, реальные IDE settings и рабочие данные не изменялись. [Отчёт](2026-11-15-r31-host-profiles.md).


## 15.11.2026 19:13 (Asia/Novosibirsk) — R3.1/P4b: evidence-bound host observations

Добавлены scoped acceptance task/checklist, bounded selected evidence capture и immutable private journal с pending/recovery/historical replay. CLI acceptance-prepare/record/show/pending/recover и пять FastMCP tools используют общее ядро. Records всегда recorded_not_verified и native_activation_allowed=false; matrix P4a не повышает capabilities по self-reported passes. Native tests/config changes не запускались. Коммиты184aa31 /920b230 /1287745; итоговый docs commit обновляет runbook/планы.

Проверки: acceptance10 (22.643 s), P4a9 (14.598 s), P012 (0.037 s) — OK; clean base10 (11.081 s,1 MCP skip), base completed/copy/reopen/reapprove OK,model_calls0. Три process-kill/copy boundaries и сохранность later instructions проверены. Ruff/sync9/docs/native secrets/diff OK; full suite не повторялся. P4 открыт: далее review/adoption/config previews; R3.1/R1/M6/M8 открыты. Рабочие данные/секреты не изменялись. [Отчёт](2026-11-15-r31-host-observations.md).


## 15.11.2026 19:33 (Asia/Novosibirsk) — R3.1/P4c: report review и disabled Codex preview

Добавлены exact report/evidence/checklist binding, immutable review journal/recovery и explicit preview-only adoption. Codex MCP renderer возвращает TOML enabled=false с existing absolute interpreter/fixed module/readonly tool allowlist; bootstrap и выбранный review отделены, native flags false, existing configs не читаются/не меняются. CLI/MCP parity проверена. Формат сверён с официальными OpenAI docs через openai-docs; native acceptance не выполнялась. Коммиты8827879 /987a58e /7df38bb /b7db5a7; итоговый docs commit обновляет планы.

Проверки: review/preview9 (22.622 s), observation10 (21.980 s), P012 (0.048 s) — OK; clean base9 (11.663 s,1 MCP skip), base completed/copy/reopen/reapprove OK,model_calls0. Три kill/copy boundaries и parent validation проверены. Ruff/sync9/docs/native secrets/diff OK; full suite не повторялся. P4 открыт: далее config lifecycle и native acceptance; R3.1/R1/M6/M8 открыты, live IDE отсрочка сохранена. [Отчёт](2026-11-15-r31-host-review-preview.md).


## 16.11.2026 16:53 (Asia/Novosibirsk) — R3.1/P4d: disabled config lifecycle завершён

Доделаны controlled plan/apply/install/refresh/disable/restore с private before/after journal, exact hashes/scope, ownership markers, ACTIVE/receipt и explicit recovery. CLI/MCP parity проверена; mutating tools destructive=true. Foreign comments/settings сохраняются, restore active PSA запрещён, completed replay не трогает later edits. Коммиты7a616b4 /e8052c8 /d4ca057; итоговый docs commit обновляет runbook/план. Предыдущее ограничение automatic approval review по usage снялось; пропущенные regression команды выполнены.

Проверки: config10 (18.309 s), review9 (12.714 s), P012 (0.051 s) — OK; clean base10 (8.564 s,1 MCP skip), base completed/copy/reopen/reapprove OK,model_calls0. Пять kill/copy boundaries и preservation conflict проверены. Ruff/sync9/docs/native secrets/diff OK; full suite не повторялся. Enable/native acceptance/cross-version migrations остаются открытыми. Реальный IDE config/рабочие данные не применялись, все mutations только synthetic temp fixtures. [Отчёт](2026-11-16-r31-host-config-lifecycle.md).


## 16.11.2026 17:10 (Asia/Novosibirsk) — P5a: config journal integrity

Завершён независимый hardening-срез: atomic ACTIVE/COMMITTED publication, preservation interrupted staging, explicit copy recovery и read-only audit CLI/FastMCP. Коммиты07338d7 /432a14c /ca405d9; итоговый docs commit фиксирует планы/runbook/отчёт.

Проверены15 разных config tests (initial13 + final integrity5 с пересечением3), P0 contracts12; clean base13 с1 MCP skip и base completed/copy/resume/reopen/reapprove smoke, model_calls0. Ruff/sync9/docs/native Gitleaks/diff OK; full suite не повторялся. Все mutations только synthetic temp fixtures; real IDE config/рабочие данные не менялись. P4 live acceptance отложена, P5 частичный; далее P5b journal/path/resource hardening. R1/M6/M8 открыты. [Отчёт](2026-11-16-p5-host-config-integrity.md).


## 16.11.2026 17:30 (Asia/Novosibirsk) — P5b: journal directory/path boundaries

Общий streaming helper ограничивает исходную enumeration и проверяет confinement до skip/ignore. Применён к task/hook/host observation/review/config journals, config audit и interrupted staging. Коммиты4ce57e2 /f8a4915; итоговый docs commit фиксирует runbook и планы.

Проверки: new4 (8.682 s), task12 (33.040 s), hook11 (55.778 s), host43 (53.303 s) —70 целевых tests OK. Реальные Windows junctions и lazy bound/closure проверены; clean base4 (9.456 s) и base completed/copy/resume/reopen/reapprove OK,model_calls0. Ruff/sync9/docs/native secrets/diff OK. Full suite не повторялся. Все mutations только temp synthetic fixtures; реальные settings/рабочие данные не менялись. P5 частичный; далее P5c compatibility/upgrade. Native/live P4 и R1/M6/M8 открыты. [Отчёт](2026-11-16-p5-journal-directory-boundaries.md).


## 16.11.2026 17:39 (Asia/Novosibirsk) — P5c: journal namespace compatibility

Общий guard блокирует unsupported/mixed namespace до v1 lookup в task/hook/host/config stores. Пустая история больше не выводится из отсутствия v1 при наличии v2. Published v1 schemas сохранены; compatible copy replay и read/write/recovery refusal проверены. Upgrade/rollback policy описан в runbook; cross-schema конвертер без целевой схемы не добавлен. Коммитыeadebaa /82d3a52; итоговый docs commit фиксирует планы/отчёт.

Проверки: namespace/directory7 (14.354 s), task12 (39.541 s), hook11 (59.701 s), host43 (58.171 s) —73 tests OK; clean base7 (11.950 s) и base completed/copy/resume/reopen/reapprove OK,model_calls0. Ruff/sync9/docs/native secrets/diff OK; full suite не повторялся. Все mutations только temp synthetic fixtures; реальные settings/кейсы не менялись. P5 частичный, далее P5d privacy/injection diagnostics; live/native P4 и R1/M6/M8 открыты. [Отчёт](2026-11-16-p5-journal-version-compatibility.md).


## 16.11.2026 17:48 (Asia/Novosibirsk) — P5d: automation privacy diagnostics

Fixed runtime I/O/encoding/model diagnostics для host/hook/subagent CLI и subagent MCP исключают private details; domain refusals сохранены. Existing role-catalog sanitation закреплён regression. Selected-material injection corpus не меняет role instructions/goal/authority или canonical case bytes. Коммитыb5fff83 /c95202d; итоговый docs commit фиксирует планы/runbook/отчёт.

Privacy5 (13.657 s), handoffs14 (16.170 s), task12 (38.229 s), hook11 (59.191 s), host43 (57.950 s) —85 tests OK. Clean base privacy5 (5.583 s,1 MCP skip). Ruff/sync9/docs/native secrets/diff OK; full suite/base workflow smoke не повторялись. Mutations только temp synthetic fixtures, моделей/native activation не было. P5 частичный; далее P5e dependency/artifact integrity и сверка рисков перед P6. P4/R1/M6/M8 открыты. [Отчёт](2026-11-16-p5-automation-privacy.md).


## 16.11.2026 18:07 (Asia/Novosibirsk) — P5e: dependency/artifact integrity

Backend setuptools82.0.1 закреплён в build-system/build group и uv.lock с hashes; runtime/extras версии не менялись. Package/verify проверяют stale lock offline до build/install, используют exported hash constraints. Verifier перешёл на общий bounded asset checker. Коммиты19b7232 /d06560f; итоговый docs commit фиксирует планы/runbook/отчёт.

Release/dependency15 (30.453 s), distribution5 (1.459 s) —20 tests OK; clean base5+5 (2.454/1.345 s) OK. Реальные wheel/sdist установлены вне source, doctor/help/demo/base completed/copy/resume/reopen/reapprove OK,model_calls0/sql_dependenciesfalse. Development artifact dirty=true, не clean release candidate; теги/публикация не выполнялись. Ruff/sync9/docs/native secrets/diff OK; full suite не повторялся. Пять локальных P5 срезов выполнены, весь P5 остаётся открытым по risk ledger; далее независимый P6a diagnostics. Native/live P4 и R1/M6/M8 открыты. [Отчёт](2026-11-16-p5-dependency-artifact-integrity.md).


## 16.11.2026 18:24 (Asia/Novosibirsk) — P6a: historical operation diagnostics

Добавлены text-free metadata projection/service/reader и read-only CLI/FastMCP для task/result/review/hook. Publication отделён от outcome; captured snapshot freshness not_checked. Self-reported usage сохраняет нули и unknown basis, отсутствующий usage остаётся null. Recovery/checks/gates/native activation не выполняются; actor/source/goal/reason texts не выводятся. Коммиты745b0ce /980a9fb; итоговый docs commit фиксирует планы/runbook/отчёт.

Projection6 (16.117 s), CLI/stdio2 (14.153 s), task12 (68.605 s), hook11 (104.286 s), privacy5 (21.216 s) —36 tests OK. Clean base8 (17.175 s,1 MCP skip). Ruff/sync9/docs/native secrets/diff OK; full suite/base completed smoke не повторялись. Mutations только synthetic temp fixtures; реальные данные/native settings не менялись. P6 частичный, далее P6b summaries/resume guidance; P4/P5/R1/M6/M8 открыты. [Отчёт](2026-11-16-p6-operation-diagnostics.md).


## 16.11.2026 18:43 (Asia/Novosibirsk) — P6b: selected-operation summaries

Strict 1–32 selection одного case, общий batch case lock, published/unpublished counts и прежние redacted packets. Guidance фиксирует только read-only status/pending argv и prerequisites; authorization/autorun false. Usage totals не вычисляются, zero/null/currencies сохранены. CLI/FastMCP parity проверена. Коммитыee179ff /a21be85; итоговый docs commit фиксирует планы/runbook/отчёт.

Core5 (6.352 s), CLI/stdio3 (17.165 s), P6a8 (29.725 s), privacy5 (21.001 s) —21 целевой test OK. Clean base summary8 (9.972 s,1 MCP skip). Ruff/sync9/docs/native secrets/diff OK; full suite/execution suites/base completed smoke не повторялись. Mutations только temp synthetic fixtures; реальные данные/native settings не менялись. P6 частичный; далее P6c usage/cost provenance. Host/native cancel отдельно; P4/P5/R1/M6/M8 открыты. [Отчёт](2026-11-16-p6-operation-summaries.md).


## 17.11.2026 01:24 (Asia/Novosibirsk) — P6c: usage declaration provenance

Добавлен bounded read-only canonical usage ledger report с source/row/business hashes, redaction и declared measured/estimated/unknown basis без independent verification. Unknown/null/zero сохранены; totals/automatic automation binding отсутствуют. Старые ledger/receipts/usage_report не изменены. CLI/FastMCP parity проверена. Коммиты96317de /dc0cdb9; итоговый docs commit фиксирует планы/runbook/отчёт.

Final provenance7 (13.601 s), P6a8 (18.118 s), P6b8 (14.630 s) —23 tests OK. Clean base7 (5.163 s,1 MCP skip). Ruff/sync9/docs/native secrets/diff OK; full suite/writer suites/base completed smoke не повторялись. Mutations только synthetic temp fixtures, реальные cases/native settings не менялись, моделей не было. P6 частичный; далее P6d capability-aware retry/cancel/resume policy. P4/P5/R1/M6/M8 открыты. [Отчёт](2026-11-17-p6-usage-provenance.md).


## 17.11.2026 01:44 (Asia/Novosibirsk) — instruction bundle/profile refresh1.1.0

Обновлены AGENTS/workflow/quality/safety, новый agent/automation router,4 canonical skills и3 role profiles. README/automation доставляются в context и входят в fingerprints; optional navigation поддерживает legacy manifests и запрещает role/host autoload/escape. Все9 generated adapters пересобраны. Human gates/opt-in/sequential fallback сохранены; native activation не включена. Коммиты52e1620 /4359353; итоговый docs commit фиксирует runbook/планы/отчёт.

Context10 (5.130 s), handoffs14 (15.927 s), task12 (35.776 s), host9 (10.173 s) —45 tests OK; final base context10 (4.599 s) OK. Skill validator8 UTF-8 /CLI parser8/sync9/Ruff/docs/native secrets/diff OK; full suite/hook workers/base completed smoke не повторялись. Реальные configs/кейсы/согласования не менялись; модели/native dispatch не запускались. P6d остаётся следующим функциональным срезом, P4/P5/R1/M6/M8 открыты. [Отчёт](2026-11-17-instructions-refresh.md).


## 17.11.2026 01:59 (Asia/Novosibirsk) — P6d: advisory controls policy

CLI/FastMCP controls projection разделяет inspect/case resume, pending forward recovery, exact UUID replay и fresh-request new attempt. Generic cancel/checkpoint executor отсутствуют в CLI, native controls not_verified. Policy не исполняет действия и не оценивает/не предоставляет authorization. Канон/resume skill актуализированы, bundle1.1.1 и9 adapters пересобраны. Коммитыdbedee4 /bbdee60 /7c45fa6; итоговый docs commit фиксирует планы/отчёт.

Controls8 (17.062 s), P6a8 (19.408 s), P6b8 (14.908 s), context10 (5.388 s) —34 tests OK; clean base8 (10.245 s,1 MCP skip). Skills validator2/sync9/Ruff/docs/native secrets/diff OK. Full suite/base completed/worker execution suites не повторялись. Explicit recovery только на temp synthetic fixtures, реальные кейсы/native settings не менялись. Локальные P6a–P6d выполнены, весь P6 и P4/P5/R1/M6/M8 открыты. Далее независимый P7a tools inventory/eval protocol. [Отчёт](2026-11-17-p6-operation-controls.md).


## 17.11.2026 19:28 (Asia/Novosibirsk) — P7a: inventory и retrieval baseline

Сверены research/knowledge/retrieval tools и границы permissions/provenance/limits/offline. Добавлен runnable synthetic kernel eval:5 sources/8 gold queries, TP5/FP1/FN1, precision=recall5/6;6 exact quotes. Размеченный semantic miss и неоднозначный FP сохранены. Cost unknown/null,0 model/external calls; это не agent-level benefit или independent review. Зафиксирован holdout/candidate protocol до RAG/provider. Код/tests commit aa5ce89; отдельный docs commit фиксирует inventory/планы/отчёт.

Новые5 tests (0.012s), file search11 (22.179s,1 Windows symlink skip):16 различных tests. Clean base повтор5 (0.007s). Generator write/check9 без differences, docs/Ruff/native Gitleaks/diff OK. Full suite/web/binary parser suites/native host/final release не повторялись. P7a выполнен; далее P7b holdout и local candidate comparison. Весь P7, P4/P5/P6 и R1/M6/M8 открыты. [Отчёт](2026-11-17-p7-retrieval-baseline.md).


## 17.11.2026 19:37 (Asia/Novosibirsk) — P7b: frozen retrieval comparison

Holdout/protocol10 sources/16 queries до candidate:88960f1; isolated token-window candidate/comparison/tests:adae42f. Development run fa36406/dirty=true сохранён в JSON с commit/hashes/versions: baseline precision1/recall5/11, candidate precision9/11/recall9/11. Recall gain не компенсирует precision loss; candidate отклонён, production literal search сохранён. False positives и null/unknown оставлены видимыми, model/network calls0.

Candidate7 (1.889s), evaluator5 (0.010s), file-search11 (21.573s,1 Windows symlink skip):23 различных tests. Clean base повтор12 (1.793s). Lifecycle/revision/withdrawal через real temp store и read-only bytes проверены. Sync/docs/Ruff/Gitleaks/diff OK; full suite/native host/independent review/final release не выполнялись. P7b завершён; далее P7c versioned registry existing tools, без adoption candidate. Весь P7, P4/P5/P6 и R1/M6/M8 открыты. [Отчёт](2026-11-17-p7b-retrieval-comparison.md).


## 17.11.2026 19:57 (Asia/Novosibirsk) — GitHub Actions portability fixes

По реальным remote logs найдены LF/CRLF drift generated demos и сравнение resolved child с unresolved Windows TEMP root.1189669 сохраняет manifest-matching bytes10 generated demo файлов и задаёт case -text policy;615d507 сравнивает canonical root/child с сохранением lexical symlink/junction/traversal отказов. Добавлены Git-index checkout true/false regression и path alias negatives; attributes включены в source archive allowlist. YAML/required checks/evidence policy/gates не ослаблялись.

Целевые15 tests OK:paths3 (0.014s),checkout1 (1.065s),CI6 (10.937s),distribution5 (0.856s). Ruff/sync9/docs254/Gitleaks/diff OK; exact demo2 cases/14 paragraphs/model_calls0 OK. Полный local suite выполняется, remote verification следует после push. Эта timestamp-запись не утверждает заранее зелёный Actions run. [Отчёт](2026-11-17-ci-portability-fixes.md). После CI вернуться к P7c; R1/M6/M8 открыты.


## 17.11.2026 20:19 (Asia/Novosibirsk) — CI Windows oracle/encoding follow-up

46dc863 remote Linux matrix/demo зелёные, Windows full620 выявил CRLF privacy oracle,3 short-name/canonical path assertions и cp1252 resume error. Локальный full620/1092.337s подтвердил только3 privacy subfailures (1 symlink skip). Test oracles приведены к raw UTF-8/canonical paths; CI/demo/release явно PYTHONUTF8=1. Runtime safety/gates и required checks сохранены. Повтор privacy5/workspace11/CI6 OK; отдельный cp1252 reproduction и UTF8 success. Всего31 различных targeted tests включая предыдущие. Повторная полная remote matrix ожидается после push. [Отчёт](2026-11-17-ci-portability-fixes.md).


## 17.11.2026 20:46 (Asia/Novosibirsk) — P7c: versioned research-tool registry

Typed schema/registry1.0.0 восьми existing research capabilities, read-only service и CLI tools list/describe + FastMCP psa_research_tools. Permissions/provenance/limits/offline fallback/choose-exclude и evaluation status — декларации, не ACL/authorization/dispatch. Availability/freshness not_checked, cost null, runtime effects false. Нельзя подставлять aggregate caps для legacy checks или hard watchdog для fetch. P7b candidate не включён.

Коммиты468ef88/c0325ae/a07a8f2. Canon README/workflow/research skill и bundle1.1.2 обновлены,9 adapters пересобраны. Registry7 (10.569s),context10 (5.062s):17 tests OK. Clean base повтор7 (1.736s,1 expected MCP skip). Skill validators2/sync9/Ruff/docs256/diff/native secrets OK перед push. Full suite/release/native host не повторялись; прежний remote green179640d не объявляется результатом нового HEAD. Кейсы/решения/gates не создавались, model/fetch/roles не запускались. Далее P7d offline research scenarios/сверка P7; весь P7 и P4/P5/P6/R1/M6/M8 открыты. [Отчёт](2026-11-17-p7c-research-tool-registry.md).


## 17.11.2026 21:05 (Asia/Novosibirsk) — P7d: offline research contracts и сверка P7

Frozen own synthetic fixture/protocol2e2216f; fixed offline runner/fault tests390db41; base demo CI step/summary и AGENTS/bundle1.1.3/adapters86b076c. Registry/local fallback/context → revision/search → synthetic exact quote/verify/coverage → draft UUID replay → invalid/corrupt refusal → withdrawal. DNS/socket/process guard,0 model/external requests; human status/stages/approvals/decision log сохранены. Нет permanent case, real fetch, gates или native activation. Actual base JSON11 checks/4.3602932s, code86b076c/dirty=true, cost/human null; final_case_ready=false после проверенного withdrawal blocker.

Smoke7 (7.404s),context10 (4.414s),registry7 real stdio (8.558s):24 разных tests OK. Base повтор7 (8.513s) и CLI OK, optional extras absent проверены. YAML/Bash syntax, sync9/Ruff/docs259/diff/native secrets OK перед push. Предыдущие P7c CI/demo76be0c0 green подтверждены отдельно, новый HEAD ещё требует нового CI. Full suite/release/native host/independent review не выполнялись. P7 measured benefit не закрыт; далее независимая P8a prep при открытых P4–P6/R1/M6/M8. [Отчёт](2026-11-17-p7d-offline-research-smoke.md).


## 17.11.2026 21:29 (Asia/Novosibirsk) — P8a paired IDE preparation

Frozen own synthetic scenario/protocol99c7d2c; schema/payload + bounded new-directory publisher800a6ef; scope-aware rubric clarification72614da. Общие inputs sequential/opt-in automation, owner-only key и neutral reviewer templates, pending prerequisites/caps/authorization, null measurements/scores, outputs отсутствуют. Actual base CLI подготовил10 payload files+manifest в ignored каталоге, hashes verified; metadata72614da/dirty=true сохранены без owner key/ответов. Никаких case/role/model/native/gate/reviewer transmission действий. Bundle1.1.3/skills не менялись.

9 tests OK dev1.611s/base1.748s: hashes, blank records, neutral labels, no dispatch, overwrite/case/link/bounds/input/partial-failure/CLI refusal. Full suite/release/independent eval не выполнялись. P7d remote Windows отменён по actual annotation15m timeout, остальные CI jobs/demo прошли;4232419 увеличивает только Windows unit job до25min, Ubuntu15/test deadlines/required suite сохранены. Новый CI ещё требует своего результата. Ruff/sync9/docs262/diff/native secrets OK перед push. Далее P8b readiness реального парного запуска, без вывода permissions из templates/budget. P7 benefit/M6/P8/R1/M8/P4–P6 открыты. [Отчёт](2026-11-17-p8a-paired-ide-preparation.md).


## 17.11.2026 21:51 (Asia/Novosibirsk) — полный specs/implementation audit

Прочитан specs/case.md §1–13 и сверены код, canonical instructions/knowledge, demos/evals, host catalog, release policy и доступные deliverables на e67bf3f. Полного соответствия пока нет: actual IDE/new-task/portability acceptance, measured full cost/benefit и комплект §11 не закрыты. Конкретные gaps: release ZIP исключает README-linked examples/slot-workshop; source published/reliability defaults/owner proxy; optional пустые option tradeoff fields; P8 C1↔C2 не заменяет manual/plain-chat C0 baseline; diagrams/mvp README содержит obsolete planned Postgres. Optional media/respondents/RAG/native5hosts не объявлены обязательными; новый autonomous runtime не нужен.

Doctor ready; existing demo2 cases/2 citations/14 paragraphs OK, corpus preserved. Offline research11 checks/4.5305614s OK, no human gates/model/network. Sync9/docs/Ruff OK, archive predicates/option builder проверены без case writes. Remote e67 CI/demo completed/success подтверждены к завершению аудита; локальный full suite/release/native/independent eval не запускались. Итоговый audit export: sync9/docs263/Ruff/diff/native secrets OK. Code/plans/authorizations не изменялись; сохранён только audit/report log. [Полный отчёт](2026-11-17-specs-implementation-audit.md).


## 18.11.2026 14:58 (Asia/Novosibirsk) — source assessment

Добавлены snapshot-bound author/owner/publication date, reliability, rationale, limitations/unknowns; CLI source assessment/assess и optional FastMCP на общем service. Journal v8 сохраняет before/after и deterministic recovery; UUID replay не перезаписывает текущую оценку. Новые imports используют metadata policy2 без owner из папки/hostname и сбрасывают прежнюю оценку даже для тех же bytes; старые format2 receipts воспроизводятся с прежней политикой. Технические extraction limitations/accessed_at и человеческие decisions/gates сохраняются. Render показывает attribution и границы оценки, изменение metadata обновляет review fingerprint.

Registry1.1.0, bundle1.1.4, canonical workflow/research skill и9 generated adapters обновлены. Проверены 11 source-assessment tests с real local stdio, CLI, stale/corrupt/withdrawn отказами, tampered bundle, crash/recovery и legacy replay; связанные import/render/lifecycle/registry/smoke suites. Offline research smoke без сети/моделей/gates успешен. Native IDE acceptance и M6/M8 не закрывались; следующий срез — полнота альтернатив.


## 18.11.2026 20:22 (Asia/Novosibirsk) — сравнение альтернатив

Добавлены psa option check, FastMCP psa_option_check и проверка на этапе options. Для каждой обязательной роли нужен вариант с описанием, пользой, издержками, рисками и сильнейшим возражением. Проверка показывает затронутые основания и пропуски по ID. Обновлены основной план и инструкции. Проверены base smoke, offline research smoke, локальный CLI/FastMCP stdio и тесты отзыва оснований и повторного открытия workflow.


## 18.11.2026 20:30 (Asia/Novosibirsk) — контекст пересмотра

В roadmap добавлены шесть направлений дополнительного уровня. CLI и FastMCP получают выбранную пару ревизий с проверкой хешей, ограниченные выдержки и затронутые записи. Проверены историческая пара после следующего обновления, отказ при повреждении архива, соответствие CLI и MCP stdio, offline research smoke, Ruff, docs и sync.


## 18.11.2026 20:34 (Asia/Novosibirsk) — черновик пересмотра

Добавлены хеш контекста, авторский JSON с keep/recheck/revise и read-only проверка через CLI/FastMCP. Покрытие зависимостей отражено счётчиками. Проверяются устаревание после правки стратегии и ревизии, посторонние ID и обязательный следующий шаг. Прошли целевой тест, CLI/MCP stdio, offline research smoke, Ruff, docs и sync.


## 18.11.2026 20:38 (Asia/Novosibirsk) — поддержка решений

Добавлены CLI decision summary и FastMCP psa_decision_summary. Сводка объединяет последнее решение, текущий план измерений и сигналы внимания. Проверены отсутствие решения и плана, неизвестная база с просроченным измерением, ревизия связанного источника и снятие сигнала после review. CLI/MCP stdio и offline research smoke прошли.


## 18.11.2026 20:44 (Asia/Novosibirsk) — анализ таблиц

Добавлены CLI source table и FastMCP psa_analyze_table. Профиль CSV/XLSX показывает пропуски, дубликаты и типы, расчёт — точные дроби, фильтры, единицу, период, числитель и знаменатель. Результат привязан к SHA-256 сохранённой ревизии. Проверены реальные временные CSV/XLSX, формулы, скрытый лист, отказ на старом хеше, parity CLI/MCP и offline research smoke.


## 18.11.2026 20:49 (Asia/Novosibirsk) — интервью и качественное кодирование

Добавлены гайд интервью, формат тематического черновика и проверка через CLI/FastMCP. Цитаты сверяются с указанным локатором и хешем источника, реальные и синтетические материалы имеют отдельные области применимости. Проверены контрпримеры, ошибочный локатор, устаревший хеш, декларации, проверка без записи, parity CLI/MCP и offline research smoke.


## 18.11.2026 20:53 (Asia/Novosibirsk) — модельный респондент

CLI и FastMCP готовят бриф вымышленной роли и экспортируют диалог с меткой синтетики и проверяемыми гипотезами. Экспорт проверяет хеш брифа, порядок ответов и ссылки на вопросы. В проверке интервью маркированный транскрипт отклоняется как реальное интервью, включая CRLF. Проверены импорт и тема по цитате, CLI/MCP stdio, offline research smoke и синхронизация инструкций.


## 18.11.2026 20:58 (Asia/Novosibirsk) — разбор пользовательского пути

Добавлены подготовка PNG-манифеста и проверка авторских UX-наблюдений в CLI/FastMCP. Отдельно записываются регион, видимое наблюдение, гипотеза и способ проверки. Проверены замена скриншота, выход за область и путь кейса, неверный заголовок PNG, CLI/MCP stdio и offline research smoke.


## 18.11.2026 21:04 (Asia/Novosibirsk) — локальные медиа

Добавлены CLI media prepare/check и FastMCP для PNG, PCM WAV и метаданных нефрагментированного MP4. Привязки проверяются по размерам, таймкодам и хешу файла. Покрыты PNG, WAV, синтетические контейнеры MP4, отказы по формату и границам, прежний UX, CLI/MCP stdio и offline research smoke.


## 18.11.2026 21:09 (Asia/Novosibirsk) — перенос свежего синтетического кейса

В текущей сессии Codex через реальные процессы CLI подготовлен кейс о времени выдачи, два источника, две проверенные цитаты, пробел о сопоставимости периодов и три альтернативы. CSV даёт 25 завершений, сводка утверждает 40 при неизвестных периоде и исключениях. В другом корне повторены resume/context/status, option check, source table и verify. Байты файлов совпадают после копирования и точного replay UUID. Через отдельный FastMCP stdio совпали результаты options/table, status и verify успешны. Приостановлено на intake v8, выбор и gates отсутствуют. Подтверждён Qwen Code 0.25.2 через --version. Native host acceptance, R1/M6/M8 не закрыты.


## 18.11.2026 21:12 (Asia/Novosibirsk) — матрица IDE

Codex зафиксирован как основная IDE и единственная цель живой приёмки. Инструкции и адаптеры других сред сохранены. Для файловой переносимости активный сценарий использует перенос каталога и новую сессию Codex. R1/M6/M8 остаются открытыми.


## 18.11.2026 21:21 (Asia/Novosibirsk) — время и расходы по кейсу

Добавлены category и duration_certainty для usage add, сводка CLI/FastMCP usage summary и инструкции. Отдельно показаны измеренные и оценочные значения, валюты, повторы, непрокрытые категории и отсутствующие поля. Legacy записи и повтор по UUID сохранены. Прошли 17 целевых и регрессионных тестов, запись/чтение CLI и MCP stdio.


## 18.11.2026 21:25 (Asia/Novosibirsk) — сводка качества источников

Добавлены CLI source quality и FastMCP psa_source_quality. Сводка выводит активные ссылки, неизвестные поля и пропущенные, сброшенные или несогласованные оценки. Подсказка включена в status/resume этапа evidence_review. Прошли 12 тестов оценки и FastMCP, реальный CLI на двух источниках синтетического кейса и offline research smoke.


## 18.11.2026 21:32 (Asia/Novosibirsk) — защита фактов от синтетических источников

Добавление и исправление fact проверяют заголовок маркированного экспорта модельного респондента. Verify и проверка оснований обещаний/базы отмечают такие связи в старых фактах. Проверены отказ без записи, допустимый synthetic, обновление источника, CLI/FastMCP stdio, 28 целевых и регрессионных тестов и offline research smoke.


## 18.11.2026 21:37 (Asia/Novosibirsk) — пример «Слот» в ZIP

Исходный архив включает 11 перечисленных файлов примера. Проверка отклоняет неполный комплект и принимает прежние архивы без примера. Прошли 16 тестов упаковки и release hooks. Локальный ZIP из рабочего дерева собран из кеша, verifier установил wheel и sdist отдельно, дважды собрал «Слот» из распакованных материалов и проверил цитаты. Также прошли демо и базовый smoke для обоих пакетов.


## 18.11.2026 21:44 (Asia/Novosibirsk) — P8b: проверка owner record

Добавлен read-only CLI checker, который сверяет подготовленные synthetic input hashes и проверяет полноту сведений о host/model/settings, prerequisite evidence refs, authorization declaration, конечных общих caps, порядке и preregistered правилах. Pass не подтверждает внешние заявления и не разрешает/не запускает эксперимент или передачу reviewer. Шаблон обновлён для статуса prerequisites и ссылок на свидетельства. Прошли 12 целевых тестов и Ruff; полный CI-набор ещё не запускался.


## 18.11.2026 22:11 (Asia/Novosibirsk) — завершён учебный кейс о времени выдачи

В текущей сессии Codex возобновили перенесённый кейс через CLI. Оценили два синтетических источника, сохранили открытый вопрос о периоде и исключениях, сравнили три варианта. Пользователь явно выбрал O-001, утвердил семь этапов и принял две смысловые оценки. Статус completed, версия 22. Итоговые validate, verify и coverage прошли, проверено девять абзацев стратегии. Базовая доля выдач остаётся неизвестной. Свежая сессия Codex и нативное подключение FastMCP остаются отдельными проверками.


## 18.11.2026 22:14 (Asia/Novosibirsk) — перенос завершённого кейса

Отдельные процессы CLI из нового каталога восстановили completed v22, решение D-001/O-001 и обе пользовательские оценки. Context загрузил набор инструкций 1.1.16. Прошли validate, verify и coverage. SHA-256 всех 282 файлов совпали у оригинала и копии до и после проверок. Результат подтверждает файловый перенос завершённого кейса. Загрузка инструкций в свежей сессии Codex и нативный FastMCP ещё открыты.


## 18.11.2026 22:25 (Asia/Novosibirsk) — FastMCP в Codex App Server

В отдельном процессе установленного Codex App Server 0.169.0-alpha.11.1 обнаружены и вызваны четыре инструмента FastMCP 4.1.6 по stdio. С CLI совпали поля статуса, результаты validate и verify и полный JSON coverage. Хеши всех 282 файлов копии совпали до и после вызовов. В свежем чате ранее подтверждено наличие AGENTS.md в стартовом контексте и возобновление кейса через CLI. Постоянное подключение в чате и сравнение операций записи остаются открытыми по M8.


## 18.11.2026 22:32 (Asia/Novosibirsk) — операции записи FastMCP через Codex

Через Codex App Server и CLI пройдены два парных сценария на одноразовых синтетических кейсах. Совпали ID источника, точная цитата, три альтернативы, тестовое решение и результаты validate/verify. Повторный импорт дал одну и ту же ревизию и зависимости. После тестового пересмотра счётчик открытых ревизий в обеих ветках снизился с одного до нуля. Для M8 осталась проверка обнаружения и вызова инструментов из обычного чата Codex.


## 19.11.2026 18:19 (Asia/Novosibirsk) — план до сдачи

Сверили ТЗ с приёмкой Codex и зафиксировали [порядок работ до сдачи](../docs/solution_plans/finish-plan.md). План включает проверку FastMCP в обычном чате, новый кейс на открытых материалах, независимое сравнение с исходным способом работы, выбранные сценарии автоматизации и полный комплект сдачи. Отмечена граница проверки переносимости при текущем объёме приёмки в Codex.


## 19.11.2026 18:23 (Asia/Novosibirsk) — подготовка подключения FastMCP для M8

Подготовлен локальный TOML для проектного подключения FastMCP. Проверены синтаксис, путь интерпретатора, четыре инструмента чтения и режим подтверждения вызовов. Кандидат хранится в игнорируемом каталоге. Подключение и вызовы из обычного чата ожидают согласования.


## 19.11.2026 18:24 (Asia/Novosibirsk) — M8 принят в чате Codex

По согласованию пользователя включён FastMCP в проектных настройках. Трасса обычного чата подтверждает четыре вызова чтения. Статус completed v22, validate, verify и coverage совпали с CLI. SHA-256 всех 282 файлов копии совпал с оригиналом. Результат и отключение описаны в [приёмке FastMCP](../docs/mcp-host-acceptance.md).


## 19.11.2026 18:30 (Asia/Novosibirsk) — пример брифа для демонстрации

Полученный от пользователя [пример брифа](<../specs/Пример брифа.pdf>) добавлен без изменений. SHA-256 копии совпал с оригиналом. План подготовки демо дополнен требованиями примера к стратегии вымышленного оператора, сценариям экономики, квартальным решениям и ресурсам.


## 19.11.2026 18:34 (Asia/Novosibirsk) — постановка демонстрационного кейса

В локальном кейсе по примеру брифа подготовлены постановка задачи и вопросы исследования. План охватывает выбор первого сегмента, согласия и условия тарифа, сравнение вариантов, дизайн пилота и прогноз по пяти показателям в двух сценариях. Исходный PDF скопирован с проверкой хеша. Validate и verify прошли на этапе intake. В журнале кейса зафиксировано 7,155 с локальных команд создания и проверки. Кейс подготовлен к пользовательскому согласованию первых двух этапов.


## 19.11.2026 18:37 (Asia/Novosibirsk) — исходные данные демонстрационного кейса

По явному согласию пользователя пройдены intake и research_plan. Импортирован PDF с локаторами страниц, сохранена оценка источника, пять учебных утверждений и три пробела. Таблица пяти показателей сверена с изображением страницы 3. Validate и verify прошли. Кейс на source_collection v16. Журнал содержит 32,345 с измеренного времени локальных команд. Расходы в журнале не указаны.


## 19.11.2026 18:40 (Asia/Novosibirsk) — сравнение вариантов демонстрационного кейса

По явному согласию пользователя пройдены source_collection и evidence_review. Сохранены четыре варианта, включая статус-кво и закрытие направления. Для выбора предложена проверка семейного предупреждения на одном тарифе. Точные цитаты о действующих возможностях привязаны к странице 1 PDF. Option check, validate и verify прошли. Кейс на options v25, решение ожидает выбора пользователя.


## 19.11.2026 18:45 (Asia/Novosibirsk) — стратегия по выбранному O-003

По согласию пользователя утверждено сравнение и записано D-001. В локальном кейсе подготовлены обе стратегии, план проверки и сводный документ из пяти частей. Два условных прогноза по пяти метрикам воспроизводятся скриптом. Расчёт даёт 279,25 и 278,65 млн руб. валовой прибыли при учебной цели 285 млн руб. В плане проверки база ограничения связи остаётся неизвестной. Render, validate, verify, coverage и структурные проверки прошли. Пакет strategy v30 без блокирующих замечаний ожидает оценки пользователя.


## 19.11.2026 18:47 (Asia/Novosibirsk) — стратегия принята, план проверки готов к оценке

По явному согласию пользователя записана оценка SEMANTIC-0001 для пакета strategy v30. Кейс перешёл на validation v32. Проверена структура плана и собран пакет оценки без блокирующих замечаний. База доли ограничений остаётся неизвестной, семь дней — предлагаемое окно наблюдения за индексным номером. Порог эффекта, поток набора и ресурсы подлежат проверке в Q1 учебного плана.


## 19.11.2026 18:49 (Asia/Novosibirsk) — завершён кейс по примеру брифа

Оценка плана проверки записана как SEMANTIC-0002, переход validation согласован пользователем. Кейс telecom-family-connectivity в состоянии completed v34. Validate, verify и coverage прошли, проверено восемь абзацев стратегий. В журнале кейса 61,133 с измеренных длительностей локальных команд. Время модели, активное время человека и расходы в журнале отсутствуют. На следующем этапе проверим продолжение после паузы и пересмотр на копии этого кейса.


## 19.11.2026 18:54 (Asia/Novosibirsk) — репетиция возобновления и пересмотра

Перенесённый кейс возобновился через CLI в completed v34 с неизменными 438 файлами. В копию добавлена отдельная учебная страница PDF про ставку 400 руб. и задержку сигнала. Повторный импорт создал SRC-REV-0001, точный повтор по UUID сохранил состояние без новой ревизии. Выявлены семь зависимых утверждений и D-001. Validate и verify прошли, а проверка черновика пересмотра не нашла пропущенных зависимостей. Предложено вернуться к options на копии. Оригинал, историческое решение и согласования сохранены.


## 19.11.2026 18:57 (Asia/Novosibirsk) — копия возвращена к сравнению вариантов

По явному указанию пользователя записан REOPEN-001 для SRC-REV-0001. Копия возобновляется на options, исходное решение сохранено в истории. Повторно оценён текущий PDF, черновик пересмотра сверён с актуальным контекстом, validate и verify прошли. Подготовлена замена C-005 с цитатой страницы 12. Кейс на options v38, исправление и повторный выбор ещё впереди.


## 19.11.2026 19:00 (Asia/Novosibirsk) — исправлена ставка на учебной копии

По явному разрешению пользователя создан C-008 (400 руб. за номеро-месяц, PDF страница 12) с сохранением C-005 в истории. Обновлён экономический абзац черновика. Варианты O-005 и O-006 используют актуальное основание, O-002 и O-004 остаются историческими записями с затронутым основанием. Validate, verify, coverage и option check прошли. Черновик пересмотра охватывает все зависимости. Копия на options v41, SRC-REV-0001 ожидает решения пользователя.


## 19.11.2026 19:03 (Asia/Novosibirsk) — закрыта ревизия, записан выбор O-001

Пользователь подтвердил рассмотрение C-001–C-008 и D-001. SRC-REV-0001 закрыта, открытых ревизий нет. После согласования сравнения записан D-002/O-001. Действующее обслуживание сохраняется, следующий предмет проверки — пригодность и своевременность сигнала. Черновики стратегии и плана проверки обновлены, исходный документ по D-001 сохранён. Validate, verify, coverage и структурные проверки прошли. Стратегия на копии v46 готова к пользовательской оценке.


## 19.11.2026 19:05 (Asia/Novosibirsk) — принята обновлённая стратегия O-001

По явному согласию пользователя записана оценка SEMANTIC-0003 для стратегии O-001, версия 46. Копия перешла на validation v48. План проверки пригодности сигнала прошёл проверку структуры. Пакет оценки без блокирующих замечаний. Исходная доля своевременных сигналов неизвестна.


## 19.11.2026 19:07 (Asia/Novosibirsk) — завершён повторный проход после пересмотра

Записана пользовательская оценка SEMANTIC-0004, повторный проход на копии завершён в completed v50. Действующее решение D-002/O-001, открытых ревизий нет. Validate, verify и coverage прошли, проверено восемь абзацев. Исходное решение сохранено в истории, оригинальный кейс остаётся контрольной копией первого прохода. План до сдачи отмечает проверку возобновления и пересмотра выполненной.


## 19.11.2026 19:09 (Asia/Novosibirsk) — подготовка сравнения с обычным чатом

Подготовлены [протокол M6](../docs/evaluation/telecom-m6.md) и общий запрос на учебном брифе оператора. Сверены SHA-256 PDF и запроса. Предусмотрены выбор человека, одинаковая пауза, учёт времени, расходов и помощи, независимая оценка. Новые прогоны ещё не начаты.


## 19.11.2026 19:19 (Asia/Novosibirsk) — первая фаза сравнения M6

По разрешению пользователя запущены два свежих чата с одинаковыми PDF и запросом. Для обоих запрошены gpt-6.2-sol и reasoning medium. Обычный чат начал первым, PSA стартовал на 14 секунд позже, ходы частично шли параллельно. Оба предложили четыре варианта и рекомендовали предпилотную проверку семейного сигнала. Длительности ходов по данным Codex — 80,576 с и 463,980 с соответственно. Это отдельные замеры первого этапа вместе с инструментами. Время модели и расходы пока неизвестны. PSA сохранил вариантное сравнение и прошёл option check, validate и verify. Оба чата ожидают общего выбора пользователя.


## 19.11.2026 19:34 (Asia/Novosibirsk) — оба результата M6 готовы к оценке

Передан общий выбор O-003, в кейсе PSA выполнены пять согласований и записан D-001. Оба чата сохранили выбор, возобновились без повторного объяснения и подготовили по одному пятичастному документу. Календарное время — 16:48 и 21:33, сумма длительностей ходов — 5:27 и 18:24 соответственно. Стоимость, время модели и время человека неизвестны. Проверки PSA прошли на strategy v38. Собран пакет с нейтральными метками и хешами, независимая оценка ещё не проведена.


## 21.11.2026 00:03 (Asia/Novosibirsk) — проверен пакет M6 для рецензента

Сверены хеши пяти файлов. ZIP содержит только общий PDF, запрос, две версии A/B и рубрику. Проверена арифметика 20 разрывов между прогнозом и целями. Итоговые баллы и оценка допущений остаются задачей рецензента.


## 21.11.2026 00:06 (Asia/Novosibirsk) — предварительная сверка сравнения M6

Проверены формулы валовой прибыли и пример расчёта размера набора. Различия прогноза связаны с допущениями об охвате, удержании и расходах. Отдельно зафиксированы вопросы про пропуски, сроки набора и критерий расширения. Пакет A/B оставлен без изменений. Независимая оценка ещё впереди.

## 21.11.2026 00:14 (Asia/Novosibirsk) — зафиксирован результат M6

Блок 00:13–00:14. Отдельный чат Codex оценил проектный агент с PSA на 13/14, обычный чат на 11/14. Сверены полная рецензия, ключ A/B и журналы двух прогонов. Зафиксированы разница календарного времени, ограничения пакета и неизвестные расходы. Обновлены отчёт M6 и планы. Следующий шаг — воспроизводимое демо R3/R4.
