# R2: общий lock/read contract файловых операций

Время: 9 ноября 2026, 18:48 (Asia/Novosibirsk, UTC+7). Длительность отдельно не замерялась.

## Сделано

- Добавлен отдельный filesystem module case_access: общий nonblocking OS lock, pending check после получения lock и reentrant доступ только внутри текущего синхронного thread/process. В ключе владения PID/root/project ID; raw OS primitive не даёт разрешения на nested access.
- Публичные case functions sources/ledger/usage/revisit/render/artifacts/critic/coverage/validation/context, load_state, mode set и gates используют общий scope. Artifact status/record/show/pending/recover и workflow replay/commit/pending/recover подключены к нему; recovery допускает ACTIVE, но не обходит живого writer.
- CLI держит scope на всём dispatch существующего кейса, включая inline lists/preconditions, и освобождает его при return/error/SystemExit. Вложенные функции не берут конфликтующий второй OS lock. Init/workspace сохраняют свой безопасный primitive.
- Файловый MCP использует те же core/store entry points; inline source list дополнительно защищён. При занятом кейсе readers и writers получают busy, без скрытого ожидания/повтора.
- Обновлены планы/README/контракты; добавлен docs/case-access.md. Статистика последнего полного прогона в планах актуализирована.

## Проверено

- Семь новых тестов: nested core/store/manifest/critic/gate calls; другой thread; raw-lock и изменённая process identity не дают reentrancy; освобождение при ошибке и независимость кейсов; реальный mode writer, остановленный между state/events; CLI inline source list и ошибки; настоящий MCP stdio busy/read/write/recovery и продолжение после освобождения lock.
- Во время paused mode writer чтение/запись/новый gate/source fetch отказывают до файловых изменений и сети. После продолжения state/events согласованы.
- Изменены ожидания двух прежних crash-тестов: живой writer теперь даёт busy для readers вместо старого HEAD/pending-only ответа. После process death старые recovery гарантии сохраняются.
- Все 251 unit-тест прошли; оба deterministic demo прошли в изолированных копиях, model_calls=0. Ruff, instruction-sync (9 managed files), forbidden-path/full-history, Markdown links и diff checks прошли.

## Границы и далее

Lock сериализует participating операции и защищает чтение в пределах scope. Это не общая crash-atomic транзакция всех JSON/JSONL: mode/source/revisit/render и другие legacy writes пока без собственного write-ahead recovery. Несколько отдельных вызовов не являются одним снимком, raw/manual доступ обходит lock. Reentrant scope предназначен для синхронного стека, не для передачи между coroutine/thread/process. Read-only business command может открыть/создать служебный lock file вне кейса; полностью read-only filesystem не заявляется.

Следующий R2-срез — перенос нужных legacy writes на commit/recovery, затем mapping/import и retire старого backend/dependencies/CI. БД/Docker/реальные модели не использовались; .env, зависимости и пользовательские кейсы не менялись. Docker-based Gitleaks заново не запускался. R1 live IDE и M6/M8 отложены, R2 остаётся открытым.
