# R2: восстановление workflow state/events

Время: 9 ноября 2026, 18:38 (Asia/Novosibirsk, UTC+7). Длительность отдельно не замерялась.

## Сделано

- Добавлены отдельные GateApproval domain command, file recovery port/service, filesystem bundle/store/guard и тонкие CLI/MCP adapters. PG workflow modules сохранены отдельно.
- Gate готовит immutable request/event, before/after state/events и входные hashes, проверяет manifest/scope/append semantics. Затем публикует ACTIVE, заменяет обе root версии через temp+replace, атомарно публикует completion receipt и удаляет ACTIVE последним.
- Входной снимок включает source texts/rendered artifacts/structured artifact journal; собственный workflow journal исключён. Recovery не перезаписывает посторонние изменения root files или inputs.
- Добавлены caller operation UUID, exact replay/collision checks и опциональный expected_workflow_version. Версия относится к новым gate-переходам; это не общая версия всех legacy writers. Без caller UUID сохраняется совместимость с прежним CLI, но retry получает новый ID.
- `psa workflow pending/recover` и `psa_pending_workflow`/`psa_recover_workflow` используют один recovery service. Recovery завершает ранее явно разрешённый gate, не создаёт новое человеческое согласие.
- Pending guard подключён к CLI/MCP и публичным файловым case functions: status/context, validate/verify/coverage, source/ledger/usage/revisit/render/critic/mode, artifact store. Обычные entry points отказывают при незавершённой ACTIVE операции.
- Обновлены README, основной план/roadmap, файловые контракты; добавлен docs/workflow-recovery.md.

## Проверено

- Финальный полный прогон: 244 теста прошли. Десять новых проверяют реальные process kill после подготовки, ACTIVE, state, events, completion и завершения; exact replay/collision, expected version, неполные/tampered preparations, corrupt marker, изменённые inputs/targets, два конкурирующих процесса и перенос незавершённого кейса.
- CLI recovery и настоящий отдельный FastMCP stdio recovery/replay прошли. Предыдущие восемь structured-plan gate tests также прошли.
- Оба deterministic file demo прошли в временных копиях; model_calls=0. Ruff, instruction-sync (9 managed files), forbidden-path/full-history, Markdown links и diff checks прошли.

## Границы

Это recoverable publication пары root files с guard, а не глобальная serializable транзакция всех реестров. Прочие legacy writers пока не все участвуют в project lock; guard на входе не останавливает уже начавшуюся операцию. Прямое чтение файлов также обходит guard. Mode/source/revisit/render пока не имеют собственного write-ahead recovery. Следующий R2-срез — общий lock/read contract и перенос необходимых writers/readers, затем mapping/import и retire старой цепочки.

Journal file limit — 512000 байт, input snapshot — 2000 файлов. При неполной подготовке/конфликте не угадываются данные, marker/preparations не удаляются автоматически. Физический power loss/NAS не сертифицированы.

БД, Docker и реальные модели не использовались; .env, зависимости и пользовательские кейсы не менялись. Docker-based Gitleaks заново не запускался. R1 live IDE и M6/M8 остаются отложенными, R2 не завершён.
