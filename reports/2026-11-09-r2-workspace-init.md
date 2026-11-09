# R2: файловый workspace init/recovery — 9 ноября 2026, 17:55 (Asia/Novosibirsk)

## Решение и границы

По указанию пользователя реальная IDE-проверка R1 отложена, не пройдена; разработка продолжена в R2. В docs/file-core.md зафиксированы инвентаризация файлового/PG-контуров, v1 контракт и очередность переноса. Полная замена PG/SQL/контейнерных dependencies не выполнена. Первый вертикальный срез — безопасное создание нового файлового кейса, где прежний init мог оставить частичные файлы прямо в конечной папке.

## Что реализовано

Отдельные domain WorkspaceSeed, WorkspaceService/WorkspaceStore port и filesystem modules для paths, OS lock, receipt/integrity и repository. Существующие CLI psa init и файловый FastMCP psa_init используют этот общий путь; init_project остался compatibility wrapper, схема state.json v1 и начальный набор журналов сохранены. Путь результата теперь нормализован до абсолютного. Error path MCP для ожидаемых конфликтов возвращает безопасный ToolError; init annotations явно обозначают запись без внешнего вызова.

Подготовка идёт в projects/.psa-staging/ID/UUID, не в конечном кейсе. Записываются 11 начальных файлов, sources/ и .psa/initialization.json с project/operation ID, временем и SHA-256. После flush/fsync и проверки точного набора/хэшей/state выполняется same-filesystem directory rename под OS-owned project lock. Конкурирующий участвующий writer получает busy/conflict; завершение процесса освобождает lock. Существующий каталог, включая notes без state, не дополняется/не перезаписывается — это осознанное усиление безопасности.

Добавлены psa workspace pending и workspace recover --operation UUID. Pending только читает; готовая staging version может быть опубликована recovery после повторной проверки. Неполная/изменённая/неожиданная preparation не публикуется и не удаляется автоматически. Если публикация уже состоялась, recovery того же UUID возвращает прежний проект без сброса последующих author edits. Initialization receipt — история создания, не текущий integrity manifest меняющегося кейса.

Внутренние пути защищены от escape/symlink/junction. Runtime staging/locks внесены в .gitignore, forbidden-path/full-history policy и тем самым исключены из release allowlist. Старые кейсы без creation receipt читаются как раньше; их автоматическая миграция или удаление данных не выполнялись.

## Проверки

- Полный прогон 211 unit-тестов прошёл. После финальной обработки MCP ошибок и изменения path policy отдельно повторены все 11 file workspace/MCP tests и 6 CI checks — успешно.
- Реальные subprocess: kill во время записи, после готовой preparation и после публикации; recovery в другом процессе, committed replay с сохранением author edits, active writer блокирует init/recover, два init публикуют один кейс. Проверены hashes/extra files/escaped receipt, занятый каталог, invalid IDs и conditional symlink probe при разрешении ОС.
- Отдельный subprocess блокирует imports sqlalchemy/psycopg/litellm/openai: файловый init проходит без них. In-process FastMCP проверяет общий init и отказ от дубля. Это автоматизированные protocol checks, не реальная IDE-приёмка.
- Demo/table-demo прошли replay validate/verify/coverage/resume/render во временных копиях; исходные файлы не изменены, model_calls=0. Ruff, instruction-sync и forbidden-path/full-history прошли; docs (139 документов), diff и финальный instruction-sync прошли. Docker-based Gitleaks не запускался; native scanner остаётся будущей работой R2.

## Дальше

Нужны typed IDE-authored artifact input, expected_version и commit/recovery для многофайловых обновлений уже существующего кейса; atomic создание каталога это не заменяет. Остальные claim/source/gate writers не стали транзакционными автоматически. Далее — расширить проверенный файловый путь, затем явный legacy mapping/import и вывод старых dependencies/CI. Recovery пока доступен через CLI fallback, отдельные MCP recovery tools не добавлялись.

Гарантия ограничена crash процесса на локальной FS с поддержанными lock/rename; power-loss/NAS поведение не объявляется сертифицированным. Участие writers в протоколе обязательно. M6/M8 и live R1 остаются открытыми/отложенными. Реальные model API, PostgreSQL/Docker, .env и данные БД не затрагивались. Новые dependencies не добавлялись; рабочие кейсы не попадали в Git. Длительность отдельно не замерялась.
