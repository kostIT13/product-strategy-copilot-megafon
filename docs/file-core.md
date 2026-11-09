# R2: файловый контракт и безопасное создание кейса

Реализован первый срез R2: существующий `psa init` использует отдельный WorkspaceService, порт WorkspaceStore и filesystem adapter. Файловый FastMCP `psa_init` вызывает тот же путь. Схема кейса остаётся v1; импорт из PostgreSQL и полная транзакционность обновлений существующего кейса ещё не реализованы. Проверки R1 в реальных IDE отложены пользователем 09.11.2026, не пройдены.

## Инвентаризация и контракт переноса

| Сценарий | Уже есть в файловом MVP | Старый PG-контур | Решение R2 |
| --- | --- | --- | --- |
| Создание/чтение/этапы | psa init/status/next, schema_version=1, строковый project ID | UUID project и отдельные workflow records | Сохранить читаемый ID/текущую v1 совместимость; atomic init выделен сейчас. UUID↔ID mapping при импорте — отдельный контракт |
| Источники | Text/HTML/CSV/JSON, source cache, hashes/revisions/revisit | PDF/DOCX/XLSX, web provenance, source repositories | Переносить нужные парсеры через общий файловый service; полный revision text сохранять с проверкой hash |
| Claims/решения/capabilities | JSONL, CLI записи и refs, обязательные роли options, coverage | Typed entities, FK/linked selection/critic | Сохранить бизнес-правила, внедрить файловые операции с ожидаемой версией и lifecycle; не копировать SQL locks/FKs как новое обязательное хранилище |
| Авторские стратегии | drafts и generated Markdown, native IDE может создавать текст | API strategy_plan → critic → internal receipt/export | Сделать typed IDE-authored вход без обязательного API run; версии/quality gate и trace нужны до записи |
| Promise check | Файловый coverage/capability gate | Более строгий read-only preflight по snapshot | Переиспользовать правила через coherent file snapshot; не вводить новый PG approval ledger |
| Resume/история | State/events, usage, источники и revisit | Pipeline/input snapshots, unknown paid outcome guards | Старые runs импортируются как история с original hashes/status; импорт не повторяет платный вызов |
| Поиск/транспорт | Файлы/метаданные и файловый FastMCP | FTS и отдельный psa-main-mcp | Основной namespace psa/file core; reader/index только производный. Retire legacy после проверенной замены |

Канон — files/records текущей схемы, не строки Markdown и не PostgreSQL export. В этом срезе schema v1 не объявлена общей новой схемой всех PG entities. Новые mapping/versioning и многофайловое обновление существующих реестров требуют следующего ограниченного среза, а не массовой конвертации файлов на месте.

## Почему изменён init

Прежний init создавал state.json, бриф и пустые реестры непосредственно в конечном каталоге: остановка могла оставить неполный проект. Теперь все 11 начальных файлов и sources/ сначала создаются под `.psa-staging/ID/OPERATION_UUID/` внутри того же projects root. `.psa/initialization.json` содержит project/operation ID, created_at и SHA-256 каждого начального файла.

Под блокировкой проекта adapter пишет UTF-8 bytes, flush/fsync, проверяет точный набор файлов/каталогов, state/project ID и hashes. До публикации конечный `projects/ID` отсутствует; после same-filesystem directory rename он содержит весь начальный набор. Существующий каталог не дополняется и не перезаписывается: даже папка с notes.md без state отклоняется. Это осознанное усиление безопасности относительно старого init; для работы в своей папке используй родительский `--projects-dir` и новый ID.

Блокировка — OS file lock, не признак существования lock-файла. Она неблокирующая: конкурирующая операция получает busy/conflict; смерть процесса освобождает ownership автоматически. Служебные lock-файлы остаются, удалять их для «снятия блокировки» нельзя. ID casefold используется для lock name, чтобы разные регистры не обходили взаимное исключение на Windows. Locking рассчитан на участвующих writers этого adapter; ручная запись в staging/обход протокола не поддерживается.

Область гарантии — завершение/сбой процесса на локальной файловой системе с поддержанным OS lock/rename. Fsync выполняется для файлов и POSIX-каталогов; это не сертификация восстановления после физического сбоя питания/контроллера и не обещание NAS/object-store поддержки. Корень выбирается пользователем явно; внутренние пути не проходят через symlinks/junctions и не выходят из него.

## Просмотр и восстановление

```powershell
psa init CASE --projects-dir CASES_PARENT
psa workspace pending CASE --projects-dir CASES_PARENT
psa workspace recover CASE --operation OPERATION_UUID --projects-dir CASES_PARENT
```

Pending только читает подготовленные операции. `recoverable=true` означает проверенную целостность staging, а не отсутствие активного writer: recovery всё равно получает OS lock и может вернуть busy. Недописанный receipt, изменённый hash, лишний файл, неверный ID или escaped path дают recoverable=false/ошибку; частичный набор не публикуется. Повреждённые preparations автоматически не удаляются и не «чинятся» пустыми журналами. Служебные `.psa-staging/` и `.psa-locks/` исключены из Git/релизов и forbidden-path проверки, исходные данные не выгружаются в репозиторий.

Recovery требует точный operation UUID и повторно проверяет staging перед публикацией. Если процесс умер уже после rename, тот же UUID возвращает прежний проект без повторной инициализации. Позднейшие author edits не сбрасываются: initialization receipt — история создания, а не текущий integrity manifest всех изменяющихся файлов. Другой UUID не может перезаписать опубликованный кейс. Обычный повтор init по занятому ID по-прежнему отклоняется.

Если упавшая операция была незавершена до receipt, можно после осмотра начать новый init, пока конечного кейса нет; старый incomplete staging остаётся для отдельного разбора. Исторические v1 кейсы без initialization receipt читаются прежними командами; recovery не присваивает им чужую операцию и не запускает автоматическую миграцию.

## Что ещё остаётся R2

Для **изменения существующих** источников/claims/решений нужен единый operation journal, expected_version, согласованный commit нескольких реестров и reader/recovery протокол. Atomic directory creation этого не заменяет. Текущие gate/claim/source writers не получили новую транзакционность автоматически; новый receipt не меняет их согласия/права.

Typed IDE-authored research_plan draft с файловым HEAD commit/recovery реализован: [research-artifacts.md](research-artifacts.md). Research_plan gate CLI/MCP явно выбирает текущую structured operation/version, проверяет свежесть и сохраняет hash-bound ссылку в approval под общим lock. Без structured плана работает legacy Markdown path. Gate state/events получили [write-ahead bundle/recovery](workflow-recovery.md), ACTIVE guard, caller UUID replay и gate-only workflow_version. Публичные readers/writers CLI/MCP/core/store теперь используют [общий access lock](case-access.md), включая вложенные вызовы и snapshot чтение. Остальные legacy writes ещё не имеют write-ahead recovery; raw-доступ обходит lock. Далее — перенос нужных операций на commit/recovery. После mapping/import и проверки parity выводить SQL/контейнерные dependencies и CI; они пока не удалены. Artifact/workflow recovery доступны через CLI/MCP; workspace recovery пока имеет CLI fallback.

## Проверка

`python -m unittest discover -s tests` включает реальные дочерние процессы: kill во время записи, до/после публикации; active writer lock, два init, recovery из другого процесса и повтор без потери author edits. Проверяются tampered hashes/extra files/path escape, предсуществующая папка и отсутствие SQL/model imports. Symlink probe выполняется при разрешении ОС; лексические escape checks обязательны. In-process FastMCP проверяет тот же init и отказ от дубля. Это автоматизированный protocol test, а не живая IDE-приёмка.
