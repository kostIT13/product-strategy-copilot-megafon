# P6b — selected-operation summaries и advisory continuation guidance

Дата: 16.11.2026 18:43 (Asia/Novosibirsk). Ветка feature/main-solution-roadmap.

## Реализовано

- Strict request с 1–32 unique kind/UUID selections одного project, предел16384 bytes. Scope selected_operations_only: никакого поиска всех кейсов или вывода глобальной readiness из неполной выборки. Request order/selection hash сохраняются.
- Общий read_many читает выбранные journal records под одним existing case lock. Сохраняются schema/hash/identity/parent и namespace guards. Один corrupt/unsupported/conflicting record прерывает весь ответ без частичных counts/JSON.
- Summary содержит прежние text-free P6a packets, counts по kind/publication, published outcomes отдельно от captured unpublished outcomes. Usage не суммируется: usage_totals=null,usage_aggregation=not_computed; currencies/zero/null и unknown basis остаются per-operation.
- Fixed guidance policy возвращает только status/subagent-pending/hook-pending argv и статические prerequisites. Prerequisites не считаются выполненными. Authorization/autorun/mutation/gate/native flags false; recovery/checks/dispatch/retry не запускаются.
- CLI diagnostics summary --request и FastMCP psa_summarize_operations используют общий service. P6a single-operation output сохранён. [Runbook](../docs/operation-summaries.md), README/MCP docs и планы обновлены. P6 частичный; далее P6c provenance telemetry/usage/cost, host/native cancel отдельно.

## Проверки

Summary core5,6.352 s,OK: selected/pending counts, no usage totals, zero/mixed currencies, один batch lock с competing thread, bounds32/33/empty/duplicates/mixed project/extra commands, fixed read-only guidance argv и no mutation authorization, whole-response corruption refusal/byte preservation.

CLI/real-stdio3,17.165 s,OK: exact parity/read-only hints, pending guidance, private canaries, oversized/invalid/corrupt requests без partial stdout. P6a regression8,29.725 s,OK. Privacy regression5,21.001 s,OK. Итого21 разный целевой test.

Clean base без MCP/LiteLLM: summary8,9.972 s,OK (1 ожидаемый stdio skip). Full repository suite, task/hook execution suites и base completed smoke не повторялись: новые batch/projection/interface paths и P6a/P5d compatibility проверены targeted suites. Journal writers, stores и runtime dependencies не менялись.

Ruff, sync9, tracked Markdown links, git diff checks и native Gitleaks8.30.1 history/tree/negative probes проверены перед push. После transient tool runtime reset файловое состояние сверено, final tests завершены с полученными результатами.

## Коммиты и границы

ee179ff — bounded selected summaries, case-lock reader и advisory guidance policy/tests.
a21be85 — CLI/FastMCP summaries и real-stdio parity/refusal.
Итоговый docs commit фиксирует runbook, планы и timestamp отчёт.

Это сводка выбранных journal records, не всех tasks/проверенных исполнений и не свежий preflight. Captured snapshots могут различаться, freshness not_checked. Case lock охватывает cooperating callers, не external editor/power-loss/NAS. Guidance — данные с autorun=false, не instruction/permission выполнять следующую mutating команду. Templates требуют собственного scope --projects-dir; никакого shell eval.

Все mutations в тестах только temp synthetic fixtures; реальные кейсы/IDE settings/.env/БД/volumes не менялись. Native subagents/hooks не активированы, модели не вызывались, private working data не коммитились. P4/P5/R1/M6/M8 остаются открытыми.
