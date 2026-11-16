# R3.1/P4d — disabled-only config lifecycle завершён

Завершено 16.11.2026 16:53 (Asia/Novosibirsk). Доделан начатый 15.11 срез; workspace/global IDE config не применялся. Предыдущие regression команды были остановлены лимитом automatic approval review, 16.11 повторены с успешно пройденной проверкой разрешений.

## Сделано

- Domain PlanConfigChange/ApplyConfigChange/ConfigRecord и pure TOML controlled merge: install_disabled, refresh_disabled, disable, guarded restore. Общие before/after hashes, current scope binding, actor/reason, strict request/schema/ownership guards.
- Managed PSA v1 block c hash marker; чужая psa секция, edited/unknown markers и unrelated semantic changes не перезаписываются. Байты/комментарии/CRLF вне owned block сохраняются. Disable меняет только enabled=false; refresh использует текущий v1 renderer. Restore возвращает точный preimage либо отсутствие созданного файла и запрещает active/implicit-enabled PSA.
- Отдельные port/service/file store и CLI/MCP interfaces. Read-only plan возвращает command/hashes/new safe fragment без foreign config contents. Apply явный: fixed project-local .codex/config.toml, private before/after intent, OS lock, ACTIVE guard, atomic replace, completion receipt, historical replay и explicit forward recovery.
- Unfinished/corrupt journal блокирует новые изменения. Recovery проверяет current before/after hashes и сохраняет later edits; completed replay не чинит даже последующий invalid TOML. Copy recovery публикует captured bytes, без запуска сервера/модели/новых tests.
- Private .psa/host-config, project config и staging files добавлены в ignore; release root allowlist их не включает. Full backups могут содержать private settings и не возвращаются tool response. Mutating config tools имеют readOnly=false/destructive=true.
- [Runbook](../docs/host-config-lifecycle.md), README/планы обновлены. Native acceptance/enable, остальные host adapters и cross-version migration остаются открытыми; R3.1/R1/M6/M8 не закрыты.

## Проверки

- Final config suite10,18.309 s,OK: CLI/real FastMCP plan/apply/replay, foreign/private values preservation, restore-to-bytes/absence, refusal to restore active PSA, managed ownership/stale hashes/UUID/enable-spoof negatives. Пять real-process interruption boundaries partial intent/intent/ACTIVE/config/receipt и copy recovery; pending conflict preserves manual bytes.
- Review/preview regression9,12.714 s,OK. P0 contracts12,0.051 s,OK. Итого31 разных целевых tests.
- Чистая base-установка без MCP/LiteLLM:10,8.564 s,OK (1 ожидаемый MCP skip). Existing base completed/copy/resume/reopen/reapprove smoke OK,model_calls0/sql_dependenciesfalse.
- Ruff/sync9/tracked Markdown links/git diff checks и native Gitleaks8.30.1 history/tree/negative probes проверены. Full suite всего репозитория не повторялся: изменённый lifecycle, предыдущий preview/review и baseline workflow проверены отдельно.

## Коммиты и ограничения

7a616b4 — core merge/apply/restore/private journal; e8052c8 — CLI/MCP/parity; d4ca057 — process fault/copy tests. Итоговый docs commit фиксирует отчёт и планы.

Enable отсутствует в schema/API. Локальная запись enabled=false не удостоверяет поведение установленной IDE или остановку уже работающего процесса; host reload/connection не запускались. Refresh — только текущий managed v1, неизвестный формат требует явного разбора. Shared lock защищает participating operations; внешний редактор не является участником транзакции. Hash — целостность, не аутентификация владельца; corrupt private metadata сохраняются для разбора, без обещания power-loss/NAS/OS sandbox. Copy содержит исходные cwd/interpreter paths и требует свежего refresh plan для нового workspace. Все изменения конфигов в проверках выполнены только во временных synthetic fixtures. Реальный project/global config, рабочие кейсы/.env/БД/volumes не читались/не менялись; native hooks/subagents/модели и внешняя передача не запускались. Live IDE отсрочка сохранена.
