# R2: вывод PostgreSQL, Alembic и Docker runtime

Дата: 10 ноября 2026, Asia/Novosibirsk; время завершения — в development log. Ветка `feature/main-solution-roadmap`. Длительность отдельно не замерялась.

## Основание и границы

Пользователь явно ответил: **«Нет, там только тестовые данные»** на вопрос о нужных PG-кейсах перед удалением старого контура. Поэтому generalized export/import не требовался, не реализовывался и не объявляется проверенным. К БД не подключались; пользовательские БД/volumes/backups и локальный .env не читались/не удалялись. Старый код и инструкции восстанавливаются из Git на eaa65c26007fe9a08f4d7a63ffc9e85658be310b в отдельном окружении, если когда-либо понадобятся прежние тестовые данные.

## Сделано

- Выведены 108 tracked файлов прежнего runtime: PG models/repositories/database/bootstrap, Alembic/migrations, Dockerfile/Compose/.dockerignore, старые CLI/MCP dispatch modules и DB-specific smoke/backup scripts. Остаются entrypoints `psa` и optional `psa-mcp`.
- SQLAlchemy/Alembic/psycopg удалены из pyproject и uv.lock; сопутствующие Mako/tzdata также вышли из lock. Pydantic указан явно. DATABASE_URL/POSTGRES_* убраны из .env.example, database_url — из Settings. Реальный .env не менялся.
- CI больше не содержит PG service, migration или Docker jobs. Native Gitleaks 8.30.1 скачивается с официального GitHub release; SHA-256 Linux/Windows x64 assets закреплены в installer. Сканер сохраняет redaction, Git-history/working-tree/negative probes; native process не имеет прежней контейнерной network isolation.
- Packaging/manifest/docs requirements/verifier переведены на файловый путь. Verifier проверяет wheel и sdist вне исходников, оба демо и новый base smoke. Отдельный base smoke требует отсутствие SQL/model/parser/MCP extras, проходит семь human-fixture gates до completed и продолжает скопированный кейс. Это временные синтетические тесты, не реальные продуктовые решения.
- README и CI/distribution инструкции обновлены. Старые PG инструкции помечены историческими. Обновлены AGENTS.md и 9 generated adapters через sync --write, основной план/roadmap и legacy inventory. Следующий этап — R3, полные стратегии/метрики/corrections; live R1/M8 и независимая M6 оценка остаются отложенными.

## Проверки

Финальный полный suite: **318 тестов, OK (1 skipped: Windows symlink privilege unavailable)**, 312.591 s.

Первый полный suite после удаления: **314 тестов, OK (1 skipped)**, 316.486 s. Новые 4 retirement tests отдельно прошли: отсутствие SQL/старых entrypoints/CI jobs, checksum-gated binary extraction, отказ tar symlink, native redacted scan. Сняты **18 tests только удалённых dispatch/composition интерфейсов** (7 в test_main_mcp и 11 в других adapter classes/methods). Остальные domain/application unit-проверки сохранены; текущие file CLI/MCP, replay/recovery и preflight tests сохраняют необходимые инварианты. Финальный полный suite фиксируется в development log.

Чистое base environment: 8 установленных пакетов, SQL/model/parser/MCP extras отсутствуют, workflow completed/copy resume passed. Первый запуск обнаружил только namespace от оставшегося локального Alembic __pycache__; после проверки абсолютного пути и отсутствия не-cache файлов удалён этот compiled cache (также очищен только compiled cache снятого PG-adapter), повтор прошёл. Это не очистка пользовательских данных.

Нативный Gitleaks Windows x64 установлен с проверкой pinned SHA и версии: Git history/working tree findings пусты, negative probes passed. Оба wheel/sdist установлены во временном окружении; импорт из site-packages, doctor/help, оба demo и base workflow/copy resume прошли, model_calls=0. Локальный архив собран с dirty=true; публикация/тег/GitHub Release не выполнялись.

uv lock --check, Ruff, docs links, sync и repository/history checks прошли; итоговые результаты записаны в development log. Remote Actions/Linux matrix не запускались локально. Windows symlink integration остаётся единственным skipped test. R2 runtime выведен для текущего проекта без нужных legacy данных; generalized migration parity не заявляется.
