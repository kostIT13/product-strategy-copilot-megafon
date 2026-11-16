# P4d: управляемый lifecycle отключённого Codex config

Продолжение [P4c preview](host-review-preview.md): явные plan/apply/show/pending/recover для project-local `.codex/config.toml`. Поддержаны install_disabled, refresh_disabled, disable и guarded restore. Enable отсутствует в протоколе; native acceptance остаётся not_verified.

## Два явных шага

```powershell
psa host config-plan --request change.json --instructions-root .
psa host config-apply --request prepared-command.json --instructions-root .
psa host config-show --operation UUID --instructions-root .
psa host config-pending --instructions-root .
psa host config-recover --operation UUID --instructions-root .
```

Plan читает только фиксированный project config выбранного instruction root и выдаёт prepared command с hashes. В prepared-command.json сохраняется объект `command` из stdout plan. Apply получает именно его, повторно проверяет состояние и только затем пишет файл. Сам plan ничего в config не меняет. Команды не ищут global settings и не подключают/не перезапускают сервер или IDE.

Change request schema1: operation_id (новый UUID), plan (P4a native Codex/mcp_stdio/local-platform scope), action, interpreter, optional review_operation_id, changed_by, reason. Для restore вместо interpreter/review задаётся source_operation_id завершённой исходной операции с тем же scope. Interpreter — существующий абсолютный local file, проверка его Python/MCP runtime не выполняется.

Prepared command дополнительно содержит expected_before_hash, expected_after_hash и scope_hash. Последний связывает request, catalog/instruction snapshots, выбранный review и точный preview renderer. Для restore связывается текущий profile scope и сохранённый preimage исходной операции. `changed_by` — заявленная атрибуция, не подтверждение личности или native consent.

| Action | Поведение |
|---|---|
| install_disabled | Добавляет новый PSA-блок, если секция psa отсутствует |
| refresh_disabled | Обновляет существующий валидный managed v1 блок текущим disabled template |
| disable | Меняет только enabled на false внутри валидного managed блока |
| restore | Возвращает точные before bytes исходной операции либо отсутствие созданного файла |

Управление ограничено одним блоком с BEGIN/END PSA MANAGED CODEX MCP v1 и hash его bytes. Повреждённые/дублированные markers, ручные изменения блока, неизвестная версия или чужая unmanaged секция psa блокируют overwrite. Refresh — обновление текущего v1 template, не общая cross-version migration. Расширение формата требует отдельной реализации.

Вне owned блока сохраняются исходные bytes, комментарии и переносы строк; TOML до/после проверяется, unrelated settings сравниваются структурно. Install/refresh используют disabled P4c template. Restore допускается только при точном совпадении текущего config с after исходной операции и никогда не возвращает active/implicit-enabled PSA. Restore другой restore-операции не поддержан. Поздние ручные правки требуют нового явного разбора и не откатываются автоматически.

## Privacy и журнал

Plan/receipt не возвращают чужой config content: только hashes, action, scope и новый безопасный managed fragment. Для disable/restore fragment отсутствует: существующие значения не выводятся. После apply receipt не раскрывает full before/after. `current_matches_after` описывает текущее совпадение; null означает недоступный/невалидный текущий config и не запускает repair.

Полные before/after хранятся в **приватном локальном backup/intent**, который может содержать существующие чувствительные значения config. `.psa/host-config/`, project `.codex/config.toml` и staging `.codex/.psa-config-*.tmp` добавлены в Git ignore; release allowlist эти root paths не включает. Это не encrypted vault и не средство очистки секретов. Не коммить backups и native settings.

## Устойчивость и replay

Общий OS lock сериализует участвующие config операции. До записи target сохраняется fsync intent; ACTIVE guard, atomic replace (либо удаление только ранее созданного файла при restore), COMMITTED receipt и очистка guard завершают публикацию. Любая незавершённая/повреждённая операция блокирует новые plan/apply до explicit recovery/разбора.

Повтор завершённого UUID/точного command возвращает прежний receipt без изменения target; другой command под тем же UUID — conflict. Replay допускает последующие ручные изменения и даже невалидный новый TOML: история сохраняется, config не исправляется. Recover завершает точный captured intent, только если current hash равен before или after. Для уже committed receipt он убирает только свой guard, сохраняя later edits. Новый тест/модель/сервер не запускается.

Partial/corrupt intent, guard или receipt сохраняются для ручного разбора; наличие полного другого snapshot не считается разрешением перезаписать повреждённые metadata. До1000 операций; config ≤64k UTF-8, request ≤64k, private envelope ≤512k. Проверены process-kill границы partial intent / complete intent / ACTIVE / config replace / receipt и recovery копии. Copy восстанавливает точные captured paths; при переносе workspace после recovery нужен новый refresh plan для актуального cwd/interpreter.

Это локальный write-ahead protocol, не power-loss/NAS/OS sandbox guarantee. Внешний редактор не участвует в OS lock; не редактируйте config одновременно с apply/recover. Сохраняющиеся manual edits обнаруживаются hashes, но атомарная транзакция с посторонним редактором не заявляется. Восстановление использует trusted local journal: SHA проверяет bytes, не аутентифицирует владельца, способного переписать всю историю.

## MCP и оставшаяся часть P4

Read-only: psa_plan_host_config, psa_host_config_operation, psa_host_config_pending. Mutating/destructive hints: psa_apply_host_config, psa_recover_host_config — это явная запись project config с backup, не native approval. CLI code0 означает успешную операцию/инспекцию, не readiness IDE. `native_activation_allowed=false`, `host_acceptance_verified=false` сохраняются.

P4d завершает disabled-only local lifecycle. Native enable/приёмка, другие host adapters и cross-version migrations остаются открытыми. Ранее отложенные live IDE тесты не выполнялись; R3.1/R1/M6/M8 не закрыты. Текущий реальный workspace config этим срезом не менялся: мутации проверены только на временных synthetic fixtures.
