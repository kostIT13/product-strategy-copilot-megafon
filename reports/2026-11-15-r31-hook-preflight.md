# R3.1/P3a — явный preflight перед strategy/validation gate

Завершено 15.11.2026 18:02 (Asia/Novosibirsk). Разработка репозитория; рабочие продуктовые кейсы не использовались.

## Сделано

- HookPreflightService, port и файловый adapter разделены по ответственности. CLI/FastMCP остаются тонкими интерфейсами.
- Два явных trigger: before_strategy_gate / before_validation_gate. Фиксированная последовательность structural_integrity, citations, stage_requirements, semantic_material вызывает существующие проверки, без копирования gate rules.
- HookRequest связывается с workflow version и hash state/events/input snapshot; shared case lock и сверка до/после checks. Устаревший request и сохранённое изменение во время проверки блокируются.
- Context guard запрещает вложенный запуск независимо от caller recursion_depth. Strict JSON/64k limit, allowlisted triggers, отказ от commands/permissions/неизвестных fields; диагностика не отражает input values.
- CLI `hook prepare/check`, FastMCP `psa_prepare_hook/psa_check_hook`: read-only, без модели/сети/shell и автоматической host activation. CLI code 1 при blocked/failed; MCP caller обязан проверять result.status.
- Passed означает механический preflight, не человеческий semantic review/approval. Canonical gates самостоятельно сохраняют действующие проверки. Ни реестры, ни state/events, ни human choice не меняются.
- [Runbook](../docs/hook-preflight.md), README, MCP/automation docs и три плана обновлены. **P3 не завершён**: дальше timeout/lifecycle/replay, source-revision/revisit notifications и release checks; затем P4 host adapters.

## Проверки

- Новый P3a: 12 tests, 22.831 s, OK. Реальные CLI/stdio parity, exit status, unknown fields/union tags/depth/duplicates, stale/midcheck mutation, recursion/error cleanup, shared busy/pending guards, сохранность canonical bytes и обязательного human review для обоих gates.
- P2 regression: 12 tests, 33.803 s, OK (включая crash/copy recovery и stdio); P0 contracts: 12 tests, 0.021 s, OK; P1 CLI/stdio regression: 2 tests, 8.837 s, OK. Всего 38 целевых tests с optional MCP.
- Чистая base-установка без MCP/LiteLLM: 12 tests, 13.959 s, OK (1 ожидаемый MCP-extra skip). Base smoke completed/copy/resume/reopen/reapprove OK, sql_dependencies=false, model_calls=0.
- Ruff/sync harness (9 managed files), tracked Markdown links, git diff checks — OK. Native Gitleaks 8.30.1 history/tree clean и negative probes прошли.
- Полный suite всего репозитория не повторялся: проверены новые механизмы, совместимость интерфейсов и прежний base workflow.

## Коммиты и ограничения

`3b0d405` — coherent fixed preflight/guards/tests; `04ac679` — CLI/FastMCP/parity. Итоговый docs commit фиксирует отчёт, runbook и планы.

В этом срезе нет durable hook journal, timeout executor, cancellation или event dispatcher. Повтор operation UUID — живая проверка, не replay исторической квитанции: прежний passed не принимается на изменённых входах. Source/release triggers P0 этот adapter отвергает. Поддержка native hooks/permissions и реальная польза отдельно не подтверждены. R1/M6/M8 открыты. Тесты запускали preflight только на синтетических временных fixtures; рабочие кейсы/.env/БД/volumes не читались/не менялись, субагенты и модели не запускались. Автоматическая активация хуков не включена.
