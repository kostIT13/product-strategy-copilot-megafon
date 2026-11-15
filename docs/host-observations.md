# P4b: evidence-bound отчёты проверки хостов

Продолжение [P4a host profiles/plans](host-profiles.md). Явные команды подготавливают scope/checklist и сохраняют выбранные локальные evidence вместе с заявленными наблюдениями. Native acceptance остаётся not_verified; activation, конфигурации IDE и продуктовые кейсы не меняются.

## Подготовка и запись

Используйте native PlanHost request по P4a с точными host/version/platform/feature. Подготовка не запускает тест, модель или host и не предоставляет разрешение на paid calls/передачу источников:

```powershell
psa host acceptance-prepare --request host-plan.json --operation UUID --instructions-root .
psa host acceptance-record --request observed-report.json --evidence-dir SANITIZED_LOGS --instructions-root .
psa host acceptance-show --operation UUID --instructions-root .
psa host acceptance-pending --instructions-root .
psa host acceptance-recover --operation UUID --instructions-root .
```

Prepare возвращает task/task_fingerprint. Task фиксирует PlanHost, catalog version/hash, instruction byte hashes и обязательные capability checks. Для mcp_stdio это instruction_loading и mcp_stdio; для subagents/hooks дополнительно требуются соответствующая feature, isolation, budget_enforcement и cancellation. При фактической проверке применяйте существующие [IDE](ide-instructions.md) и [MCP acceptance](mcp-host-acceptance.md) runbooks с действующими разрешениями. Отложенная пользователем live IDE проверка этими командами не запускается.

Observed-report.json содержит schema_version1, полный task и task_fingerprint из prepare, reported_by, observed_at (ISO timestamp с timezone), observations и evidence. Observation: capability, outcome, evidence_ids, note. Outcomes: passed/failed/not_supported требуют хотя бы одного evidence ref; not_run имеет пустые refs. Capability может быть одной из восьми P4a областей; одна запись на capability. Неполный набор допускается как неполный отчёт.

Evidence selection: evidence_id, path (одно имя .txt/.md/.json внутри явно выбранного evidence-dir), sha256 точных UTF-8 bytes. ID/path уникальны; все выбранные файлы должны быть упомянуты observations, неизвестные refs запрещены. Сначала подготовьте logs без ключей/закрытых данных; автоматической очистки секретов нет. Файлы не скачиваются и не выбираются из case/source инструкций. Nested/traversal/device names, symlinks/junctions и non-regular files запрещены.

Record проверяет текущие catalog/instructions до и после чтения evidence. Изменённый hash/неполный scope/несовпадающий task блокирует новую запись; для нового scope нужен новый UUID. До восьми файлов, ≤16 000 bytes каждый и ≤64 000 суммарно, UTF-8 с сохранением исходных CRLF/BOM. JSON request ≤64 000 bytes; полный record ≤128 000 normalized UTF-8 JSON bytes, envelope ≤256 000. Усечения и выбора дополнительных файлов нет.

## Доверие и результат

CLI code0 означает успешную запись/инспекцию, без принятия native capability. Receipt всегда содержит recorded_not_verified, identity_verified=false, host_acceptance_verified=false, review_required=true, native_activation_allowed=false и human_approval_granted=false. reported_required_checks_passed=true означает только наличие **заявленных** passed по обязательным checks с привязанными evidence bytes. Содержимое лога, reported_by и observed_at не аутентифицированы и не проверяют истинность наблюдения.

P4a matrix/planner не принимает эти records как capabilities и продолжает выдавать sequential fallback. Freshness current/stale/unavailable относится к зафиксированному catalog/instruction scope, а не к автоматическому probe установленной IDE, проверке runtime code/config identity или фактической совместимости версии. Evidence/adoption review и привязка будущего активируемого adapter/config остаются отдельным этапом.

Response CLI/MCP содержит наблюдения и evidence metadata/hashes, без raw captured text. Для локального разбора полные captured bytes находятся в record под .psa/host-acceptance/v1/UUIDHEX.json. Тексты/notes остаются недоверенными данными, не instructions/consent. Journal не становится хранилищем секретов или внешним каналом передачи.

## Неизменяемость и recovery

Файловый store использует общий OS lock и .pending.json → fsync/validation → atomic final. Точный replay завершённого UUID/report возвращает прежнюю квитанцию и historical=true; исходные evidence файлы заново не читаются, даже если удалены/изменены. Freshness пересчитывается отдельно. Другой report под тем же UUID — conflict. Новая локальная instruction/catalog правка не откатывается при replay/recovery.

Pending показывает prepared либо corrupt_or_incomplete. Только явный recover завершает публикацию точного captured record; он не повторяет native тесты и не перечитывает logs. Corrupt/partial records сохраняются для разбора. До 1000 записей, без автоматического удаления истории. SHA-256 проверяет bytes/связи, не защищает от владельца, переписавшего весь journal.

.psa/host-acceptance/ и .psa/host-evidence/ исключены Git ignore; root .psa отсутствует в release allowlist. Не коммить рабочие evidence/records. Copy всего instruction workspace переносит journal; при recovery копии новые изменения инструкций сохраняются. Проверено прерывание процесса на локальной FS, без заявления power-loss/NAS durability или OS sandbox.

## FastMCP и следующий срез

Read-only: psa_prepare_host_acceptance, psa_host_acceptance, psa_host_acceptance_pending. Пишут только локальный journal: psa_record_host_acceptance и psa_recover_host_acceptance. Вызов record/recovery явный; tool success не означает native approval. Requests одинаковы с CLI, evidence-dir/instructions-root — явная конфигурация caller.

P4 открыт. Далее — evidence review/adoption protocol и reviewable config previews; затем проверенные enable/disable/migration и native acceptance в конкретных версиях/ОС. Новые vendor config formats/API здесь не утверждаются. R3.1/R1/M6/M8 остаются открытыми; последовательный CLI путь сохраняется.
