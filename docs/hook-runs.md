# P3b: ограниченный запуск и журнал хуков

Продолжение [P3a live preflight](hook-preflight.md). Для тех же двух before-gate triggers добавлены отдельный фиксированный worker и журнал. Автоматическая активация hooks, gate approval, модели/сеть/shell не включаются.

## Команды и результаты

Подготовьте новый HookRequest через `psa hook prepare`, сохранив JSON вне кейса. Затем:

```powershell
psa hook run --request PATH_OUTSIDE_CASE/hook.json --timeout 30 --projects-dir projects
psa hook show CASE --operation UUID --projects-dir projects
psa hook pending CASE --projects-dir projects
psa hook recover CASE --operation UUID --projects-dir projects
```

Timeout — целое число 1–120 секунд (по умолчанию 30), часть identity запуска. Run допускает только current request. Тот же UUID с другим request/timeout — conflict; незавершённый UUID требует inspect/recover, не повторного исполнения. Для новой проверки подготовьте новый UUID.

Packet содержит исходный request/timeout/run_hash, immutable receipt с результатом, временем и record_hash, отдельно `historical`, текущую `freshness` и `required_check_passed`. Workflow approval всегда false. CLI run возвращает 0 только для нового passed/current результата; blocked/failed и historical replay возвращают 1 вместе со структурированным packet. Show/pending/recover — операции инспекции/восстановления: успешное выполнение возвращает 0, что не означает passed preflight. В MCP проверяйте `required_check_passed`, а не только успешность транспорта или вложенный исторический result.status.

**Завершённый UUID не запускается повторно.** Возвращается прежний receipt; wrapper historical=true и required_check_passed=false даже при current snapshot и прежнем passed. Receipt — история, не reusable разрешение. Freshness пересчитывается и может стать stale/unavailable; старый timestamp/hash не переписывается. Human semantic review/gate остаются отдельными обязательными действиями.

## Worker и deadline

Запускается только фиксированный `python -m product_strategy_agent.interfaces.hook_worker` из текущей Python-установки, без caller commands, shell или scheduler. Временные request/output находятся вне кейса. Stdout/stderr worker направлены в DEVNULL; результат читается с лимитом 128 000 bytes и проверкой schema/exact binding. Ошибки не отражают raw output/источники. Process timeout включает запуск Python; по истечении процесс завершается и ожидается его окончание. Worker также имеет собственный watchdog, чтобы ограничить зависший checker при потере родителя после запуска worker. Это wall-time boundary, не CPU/memory sandbox и не измерение tokens/cost.

Родитель не держит case lock при ожидании: worker берёт свой общий OS lock и выполняет существующий read-only preflight. До запуска и перед публикацией проверяется snapshot; новый pass при изменившихся входах превращается в blocked. Между этими шагами возможна другая штатная операция; старый receipt не блокирует изменения кейса. В worker запрещён вложенный dispatch, дополнительно к context recursion guard P3a.

## Journal и восстановление

Путь: `.psa/workflow/hooks/v1/UUIDHEX/` внутри кейса, уже исключённый существующим input snapshot. `request.json` — fsync intent до worker; `result.pending.json` — захваченный envelope; после проверки schema/hash/parent он атомарно публикуется как `result.json`. Лимит 1000 операций, до 128 000 bytes на envelope. История не очищается автоматически. Hash проверяет целостность, не аутентифицирует владельца файлов. Completion `attempted` описывает завершённую попытку запуска, включая отказ старта/timeout, не удостоверяет выполнение всех checks; `interrupted` означает восстановление без захваченного результата.

Pending показывает `execution_unknown`, `prepared_result`, `corrupt_or_incomplete`. Recovery завершает публикацию **точного** prepared result; при валидном intent без результата сохраняет failed/interrupted. Он никогда не запускает checks заново и всегда возвращает historical packet с required_check_passed=false. Частичный request/повреждённый pending сохраняется для разбора, без автоматического исправления/перезаписи. Copy всего кейса переносит журнал; последующие canonical writes не откатываются.

Результат, оставшийся только во временном worker output при гибели родителя, не является committed evidence и не восстанавливается как pass. Потеря родителя до запуска watchdog или сбой ОС/питания не объявляются полным lifecycle guarantee. При фактически ещё занятом case lock recovery сообщает busy; это не повод автоматически повторять исполнение. Гарантии остановки потомков/host sandbox не заявляются: фиксированный worker не создаёт дочерние команды проверок.

## FastMCP и следующий срез

`psa_run_hook(request, timeout_seconds, projects_dir)` и `psa_recover_hook_run` записывают локальные артефакты. `psa_hook_run` и `psa_hook_pending` read-only. Parity проверена настоящим stdio-клиентом; intent/prepared/committed kill и portable recovery — отдельными subprocess tests.

Прежний `hook check` остаётся живой синхронной read-only проверкой без durable receipt и process timeout; не смешивайте его семантику с run/replay. P3 ещё открыт: source-revision→revisit notification без отката committed import и release checks без публикации. Native activation/host acceptance — P4, R1/M6/M8 остаются открытыми.
