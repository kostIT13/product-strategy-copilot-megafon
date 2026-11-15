# R3.1/P4a — host profiles и scoped fallback plans

Завершено 15.11.2026 18:56 (Asia/Novosibirsk). Разработка репозитория; P4 начат, native acceptance не пройден.

## Сделано

- Canonical agent/hosts/catalog.json schema1/catalog1.0.0: пять host IDs и восемь native capability областей, все not_verified. Это отсутствие evidence нашего решения, не утверждение об отсутствии vendor capability.
- Каталог включён в canon digest sync_harness; девять generated adapters пересобраны. Фактические host settings не изменялись; host catalog не autoload в product case context. Hash текущих catalog bytes: `ca82ac756b22fead88f68d5ffd836edaebe1c1d936fe4223cc012314859e6c09`.
- Strict HostCatalog/HostProfile/PlanHost, отдельные application port/service и bounded file reader. Reject verified/permissions/commands, schema drift, unknown hosts, traversal, missing instructions, incomplete scope и duplicate/oversized JSON. Read-only file presence/hashes отделены от host_loading_verified.
- Host plan фиксирует host/version/platform/feature/mode/request fingerprint/catalog hash. Native request возвращает fallback_required/sequential proposal; explicit sequential — ready proposal. Native activation, execution, config writes, external transfer и human approval всегда false.
- CLI host list/inspect/plan и read-only FastMCP psa_host_matrix/psa_host_profile/psa_plan_host; CLI1 при fallback_required, CLI0 ready. Никакого автоматического запуска кейса/модели/subagent/hook или редактирования IDE configs.
- [Runbook](../docs/host-profiles.md), README/IDE/MCP docs и три плана обновлены: P4a implemented, далее evidence-bound acceptance/config previews и проверенные native adapters/activation/migrations. Ранее отложенные live IDE проверки не выполнялись.

## Проверки

- Финальные host suite9, 14.113 s, OK: CLI/real stdio parity, all-host/all-feature native refusal, scope fingerprints, unsafe/spoofed fields, missing instructions, no writes, response mutation isolation и sync drift.
- Instruction/context regression8, 5.443 s, OK: host catalog не попадает в case context, generated sync и intended release allowlist сохраняются. P0 contracts12, 0.030 s, OK. Итого 29 разных целевых tests.
- Чистая base-установка без MCP/LiteLLM:9, 3.123 s, OK (1 ожидаемый MCP-extra skip). Existing base completed/copy/resume/reopen/reapprove smoke OK, sql_dependenciesfalse/model_calls0.
- Ruff, sync9, tracked Markdown links/git diff checks и native Gitleaks8.30.1 history/tree/negative probes проверены. Full suite репозитория не повторялся: проверены новые механизмы, instruction context и прежний base workflow.

## Коммиты и ограничения

ad9f2cf — canonical catalog/sync/generated adapters; 99dc876 — strict core profiles/plans; 1fbe8ff — CLI/FastMCP/parity. Заключительный docs commit фиксирует отчёт и планы.

P4a — только read-only planning. Нет installed-host probe, native execution, acceptance record ingestion, enable/disable/config migration или permission grant. Schema1 намеренно не позволяет руками пометить feature verified; будущая evidence/adoption схема требует отдельной реализации. Host version/OS — заявленный caller контекст, не измерение. Наличие файлов и локальный stdio не доказывают IDE loading/support. Vendor API/форматы и актуальные версии в этом срезе не утверждаются; их официальную документацию нужно сверить при конкретном adapter. R3.1/R1/M6/M8 остаются открытыми. Последовательный fallback и human gates сохраняются. Рабочие кейсы/.env/пользовательские/global IDE settings/БД/volumes не читались/не менялись; тесты использовали только временные synthetic fixtures. Native hooks/subagents/модели и внешняя передача не запускались.
