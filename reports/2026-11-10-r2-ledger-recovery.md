# R2: canonical ledger/usage append через workflow v4

Время: 10 ноября 2026, 00:47 (Asia/Novosibirsk, UTC+7). Длительность отдельно не замерялась.

## Сделано

- Claims/gaps/options/decision-log/capabilities/usage переведены с прямого JSONL append на общий write-ahead publisher: выбранный реестр, state/events и completion фиксируются в одной recoverable operation.
- Добавлены typed payload models/LedgerAppend, pure validation/builders/plan v1, application port/service и filesystem codec v4. Legacy wrappers стали тоньше; v1–v3 bundles сохранены.
- Сохранены source/claim reference checks, locator/quote cardinality/length, capability status/evidence, option roles, gap priority, decision owner. Выбор option при существующих options проверяется одним pure builder для CLI/MCP. Append не объявляет цитату истинной/проверенной и не утверждает этап или публикацию.
- Exact UUID replay возвращает один record; expected workflow version, fixed ledger target, before/after/input hash checks и semantic reconstruction блокируют конфликты/посторонние изменения. CLI/MCP list defaults None/[] канонизируются одинаково; порядок непустых source/locator/quote списков сохранён.
- Usage различает business operation_id и journal UUID. При одном business ID без journal UUID используется стабильный UUID5; retry не удваивает расходы. Другой payload под прежним UUID либо повтор business ID под новым UUID отклоняется. Unknown остаётся unknown; measured/estimated и currency агрегируются отдельно.
- CLI canonical add-команды получили --operation/expected version, usage — --journal-operation/expected version. MCP использует те же core/service и оба usage ID. Обновлены планы/README/контракты, добавлен docs/ledger-recovery.md.

## Проверено

- Полный набор: все 292 unit-теста прошли. После финальной канонизации list defaults повторены 9 ledger tests; все прошли, включая CLI → настоящий MCP replay одного UUID.
- Новые проверки: запись всех шести реестров с прежними ID/бизнес-полями; real process kill на семи границах для gap и usage; replay/collision/version; owner/type/evidence checks; unknown/measured usage и отсутствие double-count; partial/tampered preparation/changed target/input; portable copy; два процесса с одной expected version; CLI и MCP stdio recovery/replay.
- Оба deterministic demo прошли в изолированных копиях, model_calls=0. Ruff, instruction-sync (9 managed files), forbidden-path/full-history, Markdown links и diff checks прошли.

## Границы и далее

Shared workflow_version учитывает append, но не raw/manual writes. Journal limits сохранены, encoded snapshots не усекаются. Correction неизвестной usage в measured под тем же business ID требует отдельного контракта, не silent overwrite/второго учёта. Historical legacy usage без matching receipt не усыновляется автоматически. Pure builders v1 сохранять для historical format v4.

Начатая итерация завершена; R2 целиком ещё открыт: инвентаризация/перенос нужных legacy функций/данных, parity и import/retire старого SQL/container контура впереди. Derived critic pack и semantic correction/re-review не объявляются общей транзакцией всех файлов.

БД/Docker/реальные модели не использовались; .env, зависимости и пользовательские кейсы не менялись. Docker-based Gitleaks заново не запускался. R1 live IDE и M6/M8 остаются отложенными.
