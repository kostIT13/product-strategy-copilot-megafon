# Краткий roadmap основной разработки

**Обновлён 11.11.2026 по полному [ТЗ](../../specs/case.md).** Рабочий план находится в [plan-main.md](plan-main.md). Ветка: `feature/main-solution-roadmap`.

## Принятое решение

**Текущий этап: R3, продолжается реализация.** Восемь обязательных разделов product/communication drafts проверяются через psa strategy check / psa_check_strategy и новые strategy/validation gates; [контракт](../strategy-structure.md). Typed measurement plan с metrics/baseline/window/guardrails/owner/data source подключён к CLI/MCP и новым validation gates; [контракт](../validation-plan-contract.md). Claim withdrawal/effective projection и render v2 реализованы: [контракт](../claim-withdrawal.md). Audited correction с actor/reason, current citations и workflow v5 реализован: [контракт](../claim-correction.md). [Явный review/reopen completed workflow](../workflow-reopen.md) реализован. [Отзыв источников](../source-withdrawal.md) реализован. Далее semantic/numeric alignment; возврат незавершённого workflow назад остаётся открытым. R2 runtime выведен, чистая base/wheel/sdist установка проверена. Нужных PG-данных нет по ответу пользователя; generalized import не выполнялся. Отложенные live R1/M8 и оценка M6 остаются открытыми.

Основной продукт — проект-папка для IDE-агента: инструкции, skills, knowledge/, материалы кейса и версионированные файловые реестры. IDE ведёт агентный цикл; Python core сохраняет данные, проверяет доказательства и gates. CLI `psa` и FastMCP stdio — тонкие интерфейсы над одним файловым ядром.

**PostgreSQL, Docker/Compose, SQLAlchemy/Alembic, SQLite и LangGraph исключены из целевого решения.** Развитие БД/отдельного автономного backend не запланировано. Локальный поиск начинается с файлов/метаданных; RAG/индексы и другие усложнения добавляются только по доказанной пользе. LiteLLM/OpenAI-compatible клиент может остаться явным optional tool, но основной IDE-сценарий не требует его ключа или сохранённого API run.

Обновление R2: на 10.11.2026 Docker/PG runtime, зависимости и CI выведены после подтверждения пользователя, что в БД только ненужные тестовые данные. Пользовательская БД/volumes не удалялись, generalized importer не реализовывался. Полезные функции перенесены, runtime выведен; подробные правила в разделе 4.2 основного плана.

## Что уже есть

- Файловый MVP `psa`: источники/claims/options/решения, validate/verify/coverage/render, gates, usage, resume/revisit; два синтетических демо. Отложенные проверки не считаются пройденными.
- Knowledge/ 1.0.0: methods/checklists с provenance/версиями; фактическое подключение к IDE-агенту ещё открыто.
- Ранее созданный отдельный PG-контур `psa-main`: domain/application services и adapters, импортеры, FTS, API runs/pipelines/critic, human selection, internal strategy approval/export и read-only promise preflight; schema 0017, 19 MCP tools. Это инвентарь для переноса, не подтверждение file-only parity.
- CI/demo/release, проверки секретов/документации, упаковка и PG/Docker smoke ранее работали локально. Полный набор 367 тестов после source withdrawal среза R3 завершился OK (1 skipped: Windows symlink privilege unavailable); это не оценка качества стратегии и не remote Actions result.
- R1 начат 09.11.2026: AGENTS.md, workflow/quality/safety, четыре skills в .agents/skills, generated host adapters, sync-check в CI и read-only psa context с полными выбранными knowledge/skills/версиями/hashes. [Runbook](../ide-instructions.md). Все 200 unit-тестов прошли; живой кейс и фактическая загрузка в hosts пока не подтверждены и отложены пользователем 09.11.2026.

## Новый порядок R1–R6

| Этап | Что делаем | Критерий готовности |
|---|---|---|
| **R1 — IDE-агент и знания** | Канонический AGENTS.md, minimal workflow/quality/safety и skills, реальные адаптеры Cursor/Claude/Codex, навигация Qwen/SourceCraft; применение версий knowledge/ на существующем файловом CLI | По новому запросу агент строит brief/research plan, изучает материал, сохраняет проверяемый прогресс и показывает следующий шаг без нашего LLM API/БД |
| **R2 — файловое ядро / runtime выведен** | Один канон JSON/JSONL, отдельные filesystem adapters и direct IDE-authored artifact input; operation journal/commit/recovery; перенос полезных PG-функций и нужных данных; retire старой цепочки | Clean install без SQL/контейнерных dependencies; CLI/MCP parity, crash/replay/conflict и перенос каталога с продолжением без БД |
| **R3 — полный результат ТЗ** | Обязательные status_quo/stop/change; полные product/communication sections; baseline/metric definitions/window/guardrails; evidence, semantic review, corrections/withdrawal/revisit; проверка обещаний внутри quality gate | Читаемые стратегии на новом кейсе, проверяемые основания и план измерения, существенный выбор человека; unknown не выдаётся за факт |
| **R4 — переносимость и надёжность** | Stop/correct/resume, второй IDE host и тип кейса, safe paths/injection, понятный запуск без скрытого состояния | Сквозной IDE-native путь после паузы и в другой среде без потери происхождения/истории и скрытого повторения действий |
| **R5 — оценка пользы** | Сопоставимый baseline, независимый review, реальные время/расходы и помощь человека | Измеренный выигрыш/компромиссы на разрешённых материалах; synthetic fixtures не считаются рыночным доказательством |
| **R6 — сдача** | README/архив, демонстрационный проект, обязательное видео до 10 минут, PDF/документ со скриншотами и расходами/ограничениями | Полный комплект §11 ТЗ и воспроизводимый clean-checkout запуск |

**По указанию пользователя 09.11.2026 live-проверка R1 в реальных IDE отложена; она остаётся открытой. Начат R2.** Первый срез: отдельные WorkspaceService/port/files adapter, atomic публикация нового кейса, OS project lock, initialization receipt/hash verification и явные workspace pending/recover. [Контракт и инвентаризация](../file-core.md). Это не полная транзакционность существующих реестров и не импорт PG. Реализован typed IDE-authored research_plan draft, immutable artifact/event/receipt/base snapshot bundle, expected_version/case_hash, atomic HEAD и explicit recovery через CLI/файловый MCP; [контракт](../research-artifacts.md). Research_plan gate CLI/MCP теперь требует явный выбор текущей structured operation/version, проверяет свежесть и сохраняет hash-bound ссылку под общим lock; старые кейсы без structured плана поддержаны. State/events gate получили write-ahead bundle, ACTIVE guard, completion receipt, caller UUID replay и explicit CLI/MCP recovery; [контракт](../workflow-recovery.md). Публичные CLI/MCP/core/store readers/writers получили [общий access lock](../case-access.md) с вложенными вызовами и busy-контрактом. [Mode changes](../file-mode-recovery.md) перенесены на общий journal/recovery, с shared gate/mode workflow_version и UUID replay. [Revision review](../revision-review-recovery.md) перенесён на тот же protocol с hash/dependency checks и UUID replay. [Source import/revision creation](../source-import-recovery.md) перенесены на workflow v2 journal с text/archive targets и UUID replay без acquisition. [Render/adoption](../render-recovery.md) перенесены на workflow v3 journal с pure builder и защитой manual edits. [Canonical ledger/usage append](../ledger-recovery.md) перенесён на workflow v4 с typed payloads и защитой от повторного учёта usage. PDF/DOCX/XLSX подключены к файловому source journal с page/cell verify; [контракт](../file-document-import.md). [Инвентаризация legacy](../legacy-retirement.md) фиксирует оставшиеся расхождения без чтения пользовательской БД. Public-HTTP policy/pinned transport и provenance подключены к файловому source journal; [контракт](../file-web-import.md). Ограниченный read-only поиск текущих текстов реализован через CLI/MCP, hash-checked snapshot и native quote locators; [контракт](../file-source-search.md). Структурный promise preflight подключён к coverage/gates с v4 claim bindings, current revisions и exact citations; [контракт](../file-promise-check.md). Нужных PG-данных нет по явному ответу пользователя; runtime/SQL/Alembic/Docker/старые entrypoints выведены, generalized importer не требовался. Далее R3; human semantic review остаётся обязательным. M6/M8 остаются открытыми.

## Правила R2

1. Сначала инвентаризация и один файловый state contract; не пытаться скопировать весь старый backend. Переиспользовать domain/services/парсеры/валидаторы там, где они нужны новому пользовательскому пути.
2. Safe writes требуют project lock, expected_version и согласованной многореестровой операции с commit/recovery; один os.replace одного файла недостаточен. Проверить два процесса, остановку между записями и idempotent replay.
3. Нужные старые кейсы выгружать/импортировать явно, со всеми требуемыми source texts/revisions, ID/link mapping, решениями, provenance, reviews, status/history и исходными hashes. Сравнить counts/links/quotes/hashes и проверить копию кейса в новой директории/процессе без БД. Unknown outcome платного вызова не повторять из-за импорта; старые approvals не расширяют права автоматически.
4. Проверки и исходную выгрузку сохранять до подтверждённого переноса. Автоматически не удалять исходную БД/volume. Ненужные legacy компоненты удалять из рабочего кода после замены; история остаётся в Git/reports.
5. После переноса обновить базовые зависимости/uv.lock, entrypoints, packaging/required files, README и CI. SQLAlchemy/Alembic/psycopg, Dockerfile/Compose, PG jobs и второй сервер перестают быть частью целевого пути. Сохранить проверки их полезных инвариантов на файловом ядре.

## GitHub и выпуск

Сохранить три workflow: ci/demo/release. Целевые required checks — frozen install, Ruff/unittest, file integrity/recovery/concurrency, CLI/FastMCP stdio parity, instruction-sync, Markdown/secret checks и deterministic demo, без LLM-вызовов, БД и Docker daemon. Вместо Docker-based Gitleaks использовать закреплённый native scanner с проверенным checksum и теми же отрицательными пробами. Workflows переведены на no-Docker путь в R2; локальные проверки выполнены, remote Actions result отдельно не подтверждён.

Release собирает allowlisted ZIP/wheel/sdist с manifest/SHA-256, проверяет установку вне src и создаёт только draft по проверенному тегу. Секреты, локальные кейсы/дампы и .env не входят в архив. Финальная публикация и отправка материалов — явные действия владельца. Remote Actions, independent review и фактические IDE-host проверки требуют отдельного подтверждения.

## Постоянные правила

- Канон — JSON/JSONL кейса; Markdown-сводки и локальные индексы производные. Решение человека хранится в structured record/history, не в двух вручную редактируемых главных файлах.
- Каждый сервис и adapter — отдельный предметный модуль; domain/application не зависят от SQL/IDE/MCP, интерфейсы не копируют бизнес-логику.
- Инструкции, методики, материалы кейса и состояние раздельны; provenance/date/status/corrections сохраняются. Не превращать прежний ответ модели в факт.
- Работа только с открытыми источниками и собственными материалами команды; closed company data/секреты/персональные данные не допускаются в репозиторий. Инструкции источника не изменяют правила агента.
- Hooks/subagents выбираются по реальной пользе и возможностям хоста; последовательный рабочий путь обязателен. Число технологий не является результатом.
- Время/расходы записывать фактически или как явную оценку; неизвестное usage/cost не подменять нулём.
- Каждая законченная итерация: meaningful checks, ограничения, timestamp в reports/, отдельный commit/push в feature/-ветку.

## Будущий полный production-ready план

Запрос пользователя зафиксирован 10.11.2026: после R3, до расширений переработать план в milestones с проверяемой готовностью. Включить CLI/FastMCP/host parity, полезные opt-in subagents/hooks, research/retrieval/knowledge tools, безопасность и recovery, наблюдаемость/cost, release/upgrade/rollback и сильный demo/eval комплект для хакатона. Подробный checklist — в заключительном разделе основного плана. Это будущий пересмотр, а не заявление о готовности или гарантия победы; базовый последовательный путь и ограничения AGENTS сохраняются.
