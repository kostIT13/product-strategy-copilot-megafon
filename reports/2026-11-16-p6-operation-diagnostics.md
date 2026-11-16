# P6a — text-free operation diagnostics

Дата: 16.11.2026 18:24 (Asia/Novosibirsk). Ветка feature/main-solution-roadmap.

## Результат

- Добавлен общий service/reader/port/domain projection для одной task/result/review/hook операции. Stores предоставляют read-only inspect для valid published/prepared records и hook request/completion. Hash/schema/identity/parent binding и прежние case locks сохранены; final+pending conflict выбранной операции блокируется.
- CLI psa diagnostics operation case UUID --kind task|result|review|hook --projects-dir PATH и read-only FastMCP psa_diagnose_operation используют один service. Instructions root/source refresh не требуются; оригинальные material/role files не перечитываются.
- Ответ содержит только version/UUID/hash/target/timestamp/publication/structured outcome/review verdict и usage. Actor/goal/reason/findings/issues/material/role texts не возвращаются. Freshness not_checked: captured snapshot не считается текущим.
- Missing value остаётся null; явные0 tokens/duration и cost="0"USD сохраняются. Существующие values — self_reported, basis=unknown,verified=false; measured/estimated не выдумываются. Unknown hook execution не объявляется running/failed; not_found не является failed outcome. Prepared result не финализируется, hook completion/interrupted различаются.
- Diagnostics не делает recovery/checks/dispatch/gates/native activation. Store schemas/receipts не менялись. [Runbook](../docs/operation-diagnostics.md), README/MCP docs и планы обновлены. P6 частичный; далее P6b summaries/resume guidance, более широкая telemetry/host/native cancel отдельно.

## Проверки

Final projection6,16.117 s,OK: все четыре result outcomes, zero/unknown usage, privacy canaries, captured historical snapshot без profile refresh, prepared task/result/review/hook, selected final+pending conflicts, partial corruption, unsupported namespace/not_found и byte preservation.

CLI/real-stdio2,14.153 s,OK: service/CLI/FastMCP exact parity, read-only annotations, prepared result без implicit recovery, corrupt private input даёт безопасный ToolError. Task journal12,68.605 s,OK; hook runs11,104.286 s,OK; automation privacy5,21.216 s,OK. Итого36 разных целевых tests. Suites выполнялись независимо/параллельно; elapsed values не являются benchmark.

Чистый base без MCP/LiteLLM: diagnostics8,17.175 s,OK (1 ожидаемый stdio skip). Full repository suite и base completed workflow smoke в этой итерации не повторялись; новые read-only paths и прежние journal/recovery/CLI/MCP flows проверены targeted suites.

Ruff, sync9, tracked Markdown links, git diff checks и native Gitleaks8.30.1 history/tree/negative probes проверены перед push. Runtime dependencies/uv.lock не менялись.

## Коммиты и границы

745b0ce — metadata projection/service/reader/store inspections и unit tests.
980a9fb — CLI/FastMCP adapters и real-stdio parity.
Итоговый docs commit фиксирует runbook, планы и timestamp отчёт.

Это historical inspection одного operation, не полная сводка кейса/истории и не fresh preflight. Current canonical workflow pending/busy locks по-прежнему дают отказ. Shared locks не заявляют защиту от сторонней подмены файлов; hashes — целостность, не identity/authentication. Host observations/config не объединены этим endpoint и используют прежние show/pending/audit. Native cancel/resume, verified timing/usage/cost и semantic LLM eval не реализованы этой правкой.

Все mutations в тестах только на temp synthetic fixtures. Реальные кейсы/IDE settings/.env/БД/volumes не менялись, native subagents/hooks не активированы, внешних моделей не вызывали, private working data не коммитились. P4/P5/R1/M6/M8 остаются открытыми.
