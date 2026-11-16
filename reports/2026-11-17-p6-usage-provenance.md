# P6c — usage/cost declaration provenance

Дата: 17.11.2026 01:24 (Asia/Novosibirsk). Ветка feature/main-solution-roadmap.

## Сделано

- Новый bounded read-only reader/service/domain projection canonical usage.jsonl выбранного существующего кейса. Source file hash и hashes непустых строк связывают значения с прочитанными bytes; business operation_id возвращается только SHA256. Исходные ledger/schema/append/replay receipts и legacy usage_report не менялись.
- Cost basis measured/estimated/unknown сохраняется как recorded_declaration, verified=false. Независимая measurement verification/source authentication не объявляются выполненными. Tokens/duration method не записан в v1: basis unknown. Missing amount/unit null, явные нули/currency сохранены; totals не вычисляются.
- Provider/model, operation text/raw business ID, note/pricing_as_of/at/stage не выводятся. Автоматическая привязка к task/result/hook и measurement evidence отсутствует и обозначена null. Free text note не становится доказательством измерения.
- Reader сохраняет case lock/canonical pending guard/confinement. Лимиты2MiB/1000 rows; unsupported/partial/extra/bool/duplicate/inconsistent data дают отказ целиком, без repair/partial report. Реальный Windows junction протестирован.
- CLI diagnostics usage и read-only FastMCP psa_diagnose_usage используют общий service. [Runbook](../docs/usage-provenance.md), README/MCP docs и планы обновлены на17.11.2026. P6 частичный; далее P6d capability-aware retry/cancel/resume policy и сверка остатка P6, native controls зависят от P4.

## Проверки

Final provenance core/CLI/real-stdio7,13.601 s,OK: exact parity, file/row/business hashes, declared basis, redaction canaries, zero/null/currencies, unchanged ledger/legacy report, schema/duplicate/cost negatives,1000/1001/byte limits, junction/pending guards и safe errors без stdout prefix.

P6a regression8,18.118 s,OK. P6b regression8,14.630 s,OK. Итого23 разных целевых tests; повторы не добавлены к числу. Clean base provenance7,5.163 s,OK (1 ожидаемый stdio skip). Full repository suite, legacy writer/recovery suites и base completed smoke не повторялись: writers не менялись, valid v1 roundtrip/byte compatibility проверены новым corpus.

Ruff/sync9/tracked Markdown links/git diff checks и native Gitleaks8.30.1 history/tree/negative probes проверены перед push. Runtime dependencies/uv.lock не менялись.

## Коммиты и границы

96317de — bounded declaration provenance/service/reader и legacy compatibility/privacy tests.
dc0cdb9 — CLI/FastMCP adapters и real-stdio parity/refusal.
Итоговый docs commit фиксирует runbook, планы и timestamp отчёт.

Это provenance inspection существующего v1 ledger, не получение новых provider/IDE receipts и не проверка истинности claims о measured cost. Source hash вычислен, не подписан и не проверен по внешнему эталону. Row hash исключает line delimiter, file hash покрывает весь source. Устаревшие subagent-result metrics не объединяются с ledger и остаются self_reported/unknown в P6a/P6b. Полная native telemetry/cancel/budget enforcement не реализована этой правкой; external editor/power-loss/NAS гарантии не заявлены.

Все mutations в тестах только temp synthetic fixtures. Реальные working cases, .env/IDE settings/БД/volumes не читались/не менялись, native subagents/hooks не активировались, модели/network pricing не вызывались. Private working data не коммитились. P4/P5/R1/M6/M8 остаются открытыми.
