# Исправление основного плана по ТЗ — 8 ноября 2026, 23:50 (Asia/Novosibirsk)

По прямому указанию пользователя обновлены [основной план](../docs/solution_plans/plan-main.md) и [краткий roadmap](../docs/solution_plans/roadmap-full-solution.md). Основания: полное [ТЗ](../specs/case.md) и [аудит](2026-11-08-specs-plan-audit.md).

## Принятые решения

- Основной продукт — проект-папка для IDE-агента с инструкциями, skills, knowledge/ и файловым состоянием. Модель IDE ведёт цикл, CLI/FastMCP вызывают одно прикладное ядро.
- PostgreSQL, Docker/Compose, SQLAlchemy/Alembic, SQLite и LangGraph исключены из целевой архитектуры. Они не перенесены в обязательный поздний этап. LiteLLM остаётся только необязательным инструментом, а успешный API run не является обязательным входом для IDE-authored артефактов.
- Один канон JSON/JSONL: structured records/history, source revisions и committed operations; Markdown и индексы — производные. decision.md больше не объявлен вторым главным реестром решения. Файловая реализация также требует project lock, expected_version, многореестрового commit/recovery и безопасного replay.
- Модульность сохранена: domain/application/ports, отдельные предметные services/filesystem adapters и тонкие CLI/MCP. Долгосрочно не поддерживать два разных бизнес-ядра psa и psa-main.

## Новый порядок работ

R1 — AGENTS.md, рабочие skills/IDE adapters, фактическое подключение knowledge/ и короткий IDE-native сценарий на существующем файловом MVP. Это следующий этап, а не работа после завершения backend.

R2 — единое файловое ядро и перенос полезных функций/нужных старых кейсов, direct artifact input от IDE, safe writes/recovery; после подтверждённой замены — вывод PG/Docker runtime/code/dependencies, второй цепочки entrypoints и переработка README/uv.lock/packaging/CI.

R3 — обязательная полнота результата: status_quo/stop/change, полноценные product/communication sections, baseline/metric definitions/window/guardrails, семантическое review, исправление/отзыв/revisit и проверка обещаний внутри quality gate. Контракты R3 фиксируются до переноса R2, чтобы не переносить недостаточные старые schemas.

R4 — переносимость, stop/correct/resume, второй IDE host, safe paths/injection и clean install. R5 — сопоставимый baseline и независимая оценка времени/стоимости/качества. R6 — обязательные материалы: репозиторий/архив, demo, видео до 10 минут, PDF/документ со скриншотами. Ранее отложенные M6/M8 остаются открытыми.

## Переход и CI

В разделе 4.2 явно описаны inventory, source texts/revisions и ID/schema mapping, сохранение provenance/ссылок/статусов/истории/исходных hashes, counts/links/quotes verification, импорт во временный каталог, проверка копии в новом процессе/директории и сохранение исходной выгрузки для сверки/отката. Неизвестные поля не отбрасываются молча, unknown outcome платного вызова не повторяется из-за импорта, старый receipt не расширяет права. Автоматическое удаление исходной БД/volume не является шагом import.

Целевой CI/release также без БД и Docker daemon. Полезные инварианты текущих PG smoke должны перейти на файловую реализацию; Gitleaks — native pinned scanner/checksum вместо Docker-based запуска, с теми же отрицательными пробами. Удаление Alembic/Docker из package required files и основного набора зависимостей запланировано после переноса, не объявлено уже выполненным.

Матрица соответствия обновлена для всех разделов ТЗ; сохранены подробные рабочие требования к данным/безопасности/стоимости/демо в приложениях. Старый M0–M10 порядок явно помечен историей MVP. Убраны оставшиеся указания вводить PostgreSQL FTS и делать собственный Qwen API основным обязательным циклом.

## Проверка и границы

Изменения только в планах и отчётах. Код, зависимости, .env, CI YAML, БД, контейнеры и исходные данные не менялись. Существующий PG-контур пока нуждается в прежнем окружении; file-only parity ещё не готова. Unit/integration tests не повторялись, поскольку runtime не менялся; проверяются docs links и git diff. Длительность отдельно не замерялась.
