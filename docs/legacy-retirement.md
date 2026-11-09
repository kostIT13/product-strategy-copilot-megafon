# R2: инвентаризация переноса и retire

Срез 10.11.2026 основан на коде старого `psa-main` и файлового `psa`, не на проверке содержимого пользовательской БД. Пользователь 10.11.2026 подтвердил: в PostgreSQL только тестовые данные, сохранять их не требуется. Экспорт/миграция реальных данных не выполнялись; шаг переноса для текущего проекта не нужен. Наличие похожей команды не означает полную семантическую parity.

| Семейство старых функций | Файловый путь | Что остаётся проверить/перенести |
| --- | --- | --- |
| project / source / claim / option / decision / capability / workflow | Init, реестры, source revisions, gates, usage, render и recovery | Mapping старых ID, provenance, история и ограничения; correction/lifecycle в R3 |
| document | PDF/DOCX/XLSX подключены к source journal, native page/cell verify | Проверка нужных реальных разрешённых материалов; [границы парсеров](file-document-import.md) |
| web | Локальный HTML, shared public-HTTP policy/pinned transport, strict decoding и provenance подключены к файловому journal | [Контракт](file-web-import.md); legacy v2 replay сохранён. Это не проверка реальных пользовательских источников или ID mapping |
| search | Literal поиск по hash-checked текущим текстам через CLI/MCP, native quote locators, bounded coherent snapshot | [Контракт](file-source-search.md); SQL FTS/ranking/stemming не переносится как prerequisite |
| agent / pipeline | Цикл ведёт IDE | Собственный API-оркестратор не переносится как prerequisite; старые runs, расходы и неизвестные исходы сохраняются как история |
| critic | Файловый critic-pack | Пакет контекста не равен выполненной независимой критике; semantic checks и результаты — R3/R5 |
| selection / strategy | Options, decision log, drafts, render и human gates | Полные typed sections, binding выбранной альтернативы, approval/export и обязательные альтернативы — R3 |
| promise | Read-only draft preflight с active facts, capability links, v4 source bindings, current hashes/revision events и exact locator quotes; coverage/gates сохраняют blockers/review hash | [Контракт](file-promise-check.md); legacy unbound claims не становятся актуальными автоматически, full semantic/correction lifecycle остаётся R3 |

## Вывод runtime выполнен

Удалены tracked PG repositories/models/bootstrap, Alembic/migrations, Dockerfile/Compose, прежние psa-main/psa-main-mcp entrypoints и связанные transport/smoke scripts. SQLAlchemy/Alembic/psycopg исключены из pyproject/uv.lock, DATABASE_URL/POSTGRES_* — из примера конфигурации. Остаются один файловый CLI psa и optional psa-mcp. Предметные domain/application unit-тесты сохранены для дальнейшей консолидации R3; сняты только tests старых dispatch/composition интерфейсов.

CI использует unit/docs/sync/clean-base/demo/release и checksum-pinned native Gitleaks; PG services и Docker daemon не нужны. Clean-base smoke достигает completed и продолжает скопированный кейс без SQL/model/parser/MCP extras. Генерализованный PG importer не реализовывался и не объявляется проверенным: нужных данных нет по явному ответу пользователя. Исторические инструкции помечены; прежний код доступен в Git на eaa65c2.

Следующий этап разработки — R3: полнота product/communication strategies, обязательных альтернатив, metrics/baselines/guardrails и correction lifecycle. Live R1/M8 и независимая оценка M6 остаются отложенными.

## Данные и условия удаления старого контура

1. Определить нужные проекты и разрешённый экспорт; сохранить backup и версию схемы. UUID → case/string ID mapping должен быть явным и проверяемым.
2. Перенести current и исторические source texts/hashes/provenance, claims/evidence, options с rejected links, capabilities, решения/reviews и workflow history. Пересчитать ссылки и hashes, не терять неизвестные поля молча.
3. Runs/pipelines/usage экспортировать с original IDs/status/cost certainty. Неизвестный исход платной операции не превращается в повторный запуск. Старое approval хранится как история и не выдаётся за новое разрешение человека.
4. Импортировать в отдельный каталог, проверить validate/verify/coverage, counts/refs, parity нужных операций, interruption/replay/conflict и продолжение после копирования. Не исправлять исходную БД на месте.
5. После проверки переноса изменить зависимости, entrypoints, CI/release и инструкции; подтвердить clean install и CLI/MCP путь без SQL/Docker/DATABASE_URL/нашего LLM API-ключа.
6. Только после проверенного экспорта и сохранения backup выводить legacy entrypoints и runtime dependencies. Удаление пользовательских БД/volumes не является автоматическим шагом разработки.

Пользовательские БД, volumes, backups и локальный .env не читались/не удалялись. Для будущего переноса неожиданно понадобившегося старого кейса восстановите прежний код из Git в отдельном окружении и выполните осознанный export/import по правилам выше; удаление runtime не превращает старые approvals в новые разрешения.
