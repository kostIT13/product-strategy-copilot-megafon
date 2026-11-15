# R3.1/P4b — scoped host observations и evidence capture

Завершено 15.11.2026 19:13 (Asia/Novosibirsk). Разработка репозитория; native acceptance не выполнялась.

## Сделано

- AcceptanceTask связывает native PlanHost/host/version/OS/feature, catalog version/hash, instruction hashes и обязательные capability checks. Prepare только формирует task, без запуска тестов/host/model и без предоставления разрешений.
- Strict RecordHostAcceptance/Observation/EvidenceSelection/CapturedEvidence/AcceptanceRecord: unique refs, typed outcomes, точный task fingerprint и UTF-8 byte hashes. Missing/partial/not_run/failed/not_supported сохраняются как заявленные наблюдения; исходные notes/logs остаются данными.
- Отдельные application port/service, selected-only bounded evidence reader и immutable local store. До8 flat UTF-8 files,16k каждый/64k всего; hash/regular-file/device/path guards, scope freshness до/после capture. Unknown inputs/permissions и stale task отклоняются.
- .psa/host-acceptance/v1 journal с shared OS lock, pending/fsync/schema/hash validation/atomic publication, exact historical replay, conflict и explicit forward recovery. Git ignore для private records/evidence; release root allowlist .psa не включает. Public instructions/кейсы/native configs не меняются.
- Receipt всегда recorded_not_verified, identity_verified=false, host_acceptance_verified=false, review_required=true, native_activation_allowed=false, human_approval_granted=false. reported_required_checks_passed — только наличие заявленных passes с evidence refs, без подтверждения истинности/host behavior.
- CLI acceptance-prepare/record/show/pending/recover и пять FastMCP tools. Capture/recovery пишут только local journal, raw captured text в response отсутствует. Matrix P4a не принимает records как capabilities и сохраняет fallback.
- [Runbook](../docs/host-observations.md), README/планы обновлены: P4b capture implemented, далее review/adoption/config previews. R3.1/R1/M6/M8 открыты.

## Проверки

- Final host acceptance suite10,22.643 s,OK: CLI/real stdio prepare/record/replay/show/recover; all reported passes не активируют native; failed/unsupported/not_run; wrong refs/hash/scope, UTF-8/size/device/directory/extra fields; unselected evidence не читается; shared busy guard; три real-process kill boundaries partial/prepared/committed и recovery копии без original logs с сохранением later instruction writes.
- P4a regression9,14.598 s,OK; P0 contracts12,0.037 s,OK. Итого31 разных целевых tests.
- Чистая base-установка без MCP/LiteLLM:10,11.081 s,OK (1 ожидаемый MCP-extra skip). Existing base completed/copy/resume/reopen/reapprove smoke OK, model_calls0/sql_dependenciesfalse.
- Ruff/sync9/tracked Markdown links/git diff checks и native Gitleaks8.30.1 history/tree/negative probes проверены. Full suite всего репозитория не повторялся: новые capture/recovery механизмы, прежний planner и base workflow проверены отдельно.

## Коммиты и границы

184aa31 — strict capture/core/store/private ignore; 920b230 — CLI/FastMCP parity; 1287745 — process interruption/copy recovery. Итоговый docs commit сохраняет отчёт и планы.

Заявленные observer/time/outcomes не аутентифицированы. Hash связывает bytes, не доказывает корректность/реальность native теста. Freshness относится к catalog/instruction scope, не установленному host/runtime/config identity. Review/adoption и config previews/activation/migrations ещё впереди. Действующее откладывание live IDE тестов сохранено; native APIs/formats не утверждались и actual native capability не повышалась. Journal локальный, без автоматической секретной очистки/удаления/повторных тестов; лог должен быть заранее подготовлен без закрытых данных. Power-loss/NAS/OS sandbox гарантии не заявлены. Рабочие кейсы/.env/пользовательские/global IDE settings/БД/volumes не читались/не менялись; все reports/logs/обозначенные observer роли в тестах синтетические. Внешняя передача/native hooks/subagents/модели не запускались.
