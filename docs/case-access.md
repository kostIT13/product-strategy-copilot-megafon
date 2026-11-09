# Общий доступ к файловому кейсу

R2: participating readers/writers используют один nonblocking OS lock на кейс через `case_access`. Это сериализация живых файловых операций; rollback/recovery каждого legacy writer остаётся отдельной задачей.

## Контракт

- Lock берётся до чтения входов/проверки ACTIVE и удерживается до конца операции, включая проверки и запись. Другой процесс или поток получает `workspace operation is busy`; скрытого ожидания/повтора нет.
- Вложенные синхронные вызовы в том же thread/process используют уже взятый lock. Ключ содержит PID, нормализованный root и case-folded ID. Сырой `project_lock` не даёт разрешения на reentrant вход через `case_access`.
- После получения lock обычный вход проверяет workflow ACTIVE. Незавершённая публикация блокирует чтение/запись. Workflow pending/recover получают тот же lock, но явно допускают ACTIVE; они не обходят работающего writer.
- Lock освобождается при return/error/SystemExit. После смерти процесса OS освобождает владение. Постоянный `.psa-locks/ID.lock` не означает занятую операцию; lock files не удаляются автоматически.
- Разные кейсы не блокируют друг друга. Case paths остаются confined; symlink/junction и некорректный ID не обходят границы.

Текущий простой режим эксклюзивен и для readers: одновременно два чтения одного кейса могут получить busy. Это осознанное ограничение локального последовательного сценария; reader/writer lock или очередь пока не нужны. Сетевой source fetch держит lock от входа до завершения записи, поэтому другие операции кейса во время fetch тоже получают busy. Подтверждённые команды нужно повторять явно, не запускать paid/внешние действия автоматически из-за busy.

## Покрытие

| Вход | Граница |
|---|---|
| Файловый CLI `psa` | Весь dispatch существующего кейса, включая inline source list и проверки перед записью; init/workspace используют отдельный primitive, workflow recovery — service/store |
| Core case functions | sources/ledger/usage/revisit/render/artifacts/critic/coverage/validation/instruction context, load_state, approve_stage, mode set |
| Artifact store | status/record/show/pending/recover — общий scope, включая current case snapshot и HEAD |
| Workflow store | replay/commit/pending/recover; явные recovery методы допускают ACTIVE под lock |
| Файловый MCP | Те же core/store функции; inline source list обёрнут отдельно |

`psa-main`/PG и его интерфейсы этим протоколом не меняются. Low-level helpers, ручные правки и сторонние программы, читающие JSON/JSONL напрямую, не участвуют в lock. Для составной Python-операции нужно держать `case_access(projects_dir, project_id)` вокруг всех её core вызовов. Несколько независимых вызовов не образуют один снимок.

Reentrancy предназначена для синхронного стека; не переносить scope в другой thread/process и не держать его через `await`/передачу управления другой coroutine. Публичные core методы синхронны. Техническое владение lock не является человеческим approval.

## Busy и восстановление

При живом writer readers больше не возвращают даже старую HEAD: они получают busy. После process kill неоконченный artifact draft по-прежнему скрыт до atomic HEAD/recovery, а workflow ACTIVE требует [явного recovery](workflow-recovery.md). Integrity/version/case hash/replay проверки не отменяются блокировкой.

Read-only команды не меняют бизнес-файлы кейса, но получение OS lock может создать/открыть служебный lock file вне кейса. Projects root должен допускать работу `.psa-locks`; это не обещание запуска на полностью read-only filesystem. Эти файлы исключены из Git/release.

## Что ещё открыто

Стабильное чтение защищено от участвующих writers в пределах одного scope. Gate, [mode changes](file-mode-recovery.md) и [revision review](revision-review-recovery.md) используют общий ACTIVE/bundle recovery. Общая crash-atomic транзакция всех реестров не реализована: оставшиеся ledger/usage writes ещё могут оставить частичные результаты после process kill. Прямые авторские/сторонние правки также требуют отдельной дисциплины. Следующий срез R2 — перенос необходимых операций на write-ahead commit/recovery, затем import/retire старого backend и зависимостей.

Source import/revision creation теперь используют [workflow v2 bundle/recovery](source-import-recovery.md) с captured text/archive targets; общая версия учитывает и эти операции.

Render и adoption integrity manifest теперь используют [workflow v3 recovery](render-recovery.md); Markdown builder отделён от публикации, existing drafts сохраняются.
