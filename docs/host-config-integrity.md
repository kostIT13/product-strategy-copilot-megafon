# P5a: целостность config journal и восстановление копии

Первый независимый срез P5, 16.11.2026. Продолжает [disabled lifecycle P4d](host-config-lifecycle.md); live IDE приёмка P4 остаётся отложенной. Все проверки изменений выполнялись на временных синтетических проектах.

## Read-only audit

```text
psa host config-audit --instructions-root PATH
```

FastMCP: `psa_audit_host_config(instructions_root=PATH)`, readOnlyHint=true. Общий service/store и OS lock дают тот же ответ, что CLI. Проверка не выполняет recovery и не возвращает config bytes, пути к backups или тексты исключений. Служебный lock может создаваться как при других read-only командах.

Ответ содержит counts.operations/completed/pending, integrity_ok и issues с фиксированным code и operation_id (либо null). CLI code0 означает, что audit выполнен; для автоматизации отдельно проверять integrity_ok. Чистый pending intent может быть целым: integrity_ok не означает отсутствие pending или готовность IDE. Числа completed/pending учитывают записи, для которых удалось прочитать intent и receipt; повреждённые записи входят только в operations.

Проверяются schema/hash/identity intent, restore binding, receipt, ACTIVE binding, staging и SHA сохранённых interrupted snapshots. Счётчики не раскрывают before/after. Коды: invalid_active_guard, orphan_active_guard, active_binding_mismatch, unrecognized_journal_entry, unrecognized_operation_entry, corrupt_or_unsupported_operation, interrupted_staging, unpublished_metadata, unpublished_config. Неизвестная структура не считается пустым журналом. Максимум 1000 операций; исходные ограничения размера файлов сохранены.

## Публикация и recovery

ACTIVE и COMMITTED теперь записываются через отдельные `*.pending.json` внутри private operation directory, flush/fsync и os.replace. Authoritative файл появляется целиком. Формат опубликованных v1 intent/receipt не изменён; ранее завершённые v1 операции читаются и replay не запускает новую запись config.

При явном recover синтаксически оборванная metadata staging либо несовпадающий config temp сначала сохраняются в private `interrupted/<name>-<sha256>.bin`. Сохранённые bytes перечитываются и сравниваются; только затем удаляется известный staging path и создаётся новая staging запись из проверенного intent. Максимум 16 snapshots на операцию, автоматической очистки нет. Переполнение, несовпадение сохранённого файла, полный JSON с неправильным binding/schema, повреждённые authoritative metadata или несовместимый intent требуют ручного разбора. Структурно неправильный JSON не превращается в разрешение на применение.

Полный валидный staged COMMITTED фиксирует уже выполненную замену и readback config. Recover публикует именно этот receipt с исходным applied_at, сохраняя более поздние ручные изменения target. При отсутствии такого completion fact current config должен точно совпадать с before/after; посторонние правки не перезаписываются. Recovery не включает MCP и не вызывает IDE, модель или hooks.

## Backup/restore rehearsal

1. Завершить работу участвующих процессов и сохранить копию instruction workspace вместе с `.psa/host-config/` и `.codex/`, включая игнорируемые staging files. Обычный Git checkout не является таким backup. Живая несогласованная копия не проверена.
2. На копии выполнить config-audit и config-pending; сверить ID. Audit сам ничего не исправляет.
3. Для валидного pending intent явно вызвать `psa host config-recover --operation UUID --instructions-root COPY`. Повреждённый основной intent/guard/receipt оставить для разбора. Не удалять журнал, чтобы обойти отказ.
4. Повторить audit и show. Current_matches_after=false после исторического replay допустим при последующих ручных правках. Для переноса cwd/interpreter нужен новый refresh plan; recovery сохраняет прежние captured paths.

Приватный backup содержит исходные настройки и потенциальные секреты; это локальные ignored данные, не release artifact и не encrypted vault. Тесты останавливают реальные дочерние процессы во время записи staging, восстанавливают отдельную копию и сравнивают сохранённые bytes. Это не гарантия power-loss/NAS, независимого backup storage или транзакции с внешним редактором. SHA проверяет целостность, не аутентифицирует владельца журнала. Повреждённые authoritative metadata прежнего прямого writer автоматически не ремонтируются.

P5 остаётся открытым: hardening остальных журналов/paths/resources, общий upgrade/migration/rollback, dependency integrity и более широкий корпус отказов — следующие срезы. Native acceptance/enable P4, R1/M6/M8 не закрыты.
