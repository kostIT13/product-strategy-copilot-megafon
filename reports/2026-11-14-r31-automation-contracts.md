# R3.1/P0: production-план и automation contracts

Завершено 14.11.2026 21:21 (Asia/Novosibirsk). Ветка feature/main-solution-roadmap. Работа над репозиторием; продуктовый кейс не создавался и не изменялся.

## План и первый срез

После функционального R3 подготовлен полный рабочий production-план P0–P9: contracts → handoffs → result/provenance → local hooks → реальные host adapters → hardening/наблюдаемость → research/retrieval по измеримой пользе → независимая оценка → сдача. Для каждого milestone заданы dependencies, Definition of Done и границы. Матрица hosts явно отделяет локальные CLI/MCP проверки от неподтверждённой native automation поддержки; никаких новых заявлений о версиях/возможностях IDE не делалось.

Контракты описаны в docs/automation-contracts.md и реализованы раздельно в domain/automation/contracts.py, subagents.py и hooks.py. Новых dependencies, БД/контейнеров и LLM loop нет. P0 не включает dispatcher, invocation adapters, host sandbox, фактический timeout/token/cost enforcement или активацию agents/hooks.

## Реализованные guards

- Versioned strict packets: schema_version=1 без bool/unknown fields, UUID/snapshot identity, UTF-8 packet ≤128000 bytes без усечения.
- Subagent roles research/evidence/critic; 1–16 excerpts с exact UTF-8 SHA-256 и лимитом текста. Нет полей commands/tools/writes/authorization/credentials.
- Result binding к UUID, role, target и fingerprint полного task, включая goal/inputs/budget. Observation ссылается на переданные input IDs и не становится canonical fact. Failed/cancelled/budget_exceeded содержат reason, без partial findings.
- Nullable self-reported telemetry сохраняет unknown. Объявленное превышение token/time/cost требует budget_exceeded; completed с cost cap требует сравнимого cost/currency. Это guard отчёта, не измерение или actual executor limit.
- Hook triggers ограничены before_strategy_gate, before_validation_gate, source_revision, release_check; release/case targets различаются, ненулевой recursion_depth запрещён. Result должен совпадать с полным request; mandatory failed/blocked/skipped не дают proceed. Реальная causation/replay history и failure policy dispatcher — следующие срезы.

## Коммиты

1. 39450f0 — production milestones и protocol specification.
2. 69c31b3 — strict domain contracts, binding/budget guards и 12 tests.
3. 224a1f3 — strict JSON boundary regression assertions.
4. Отдельный docs/report commit — актуальные статусы планов, timestamp и проверки.

## Проверки

- Финальные 12 automation contract tests, 0.020 s, OK, включая strict JSON deserialization negatives. Проверены exact Unicode/CRLF/hash и JSON roundtrip, role/UUID/snapshot/goal/budget mismatch, неизвестные refs/permissions/commands, observations без evidence, partial failure, unknown usage, strict decimal/int/version, model_copy bypass revalidation, UTF-8 packet limits, failed/skip hooks, trigger/target mismatch и recursion.
- Clean base без MCP/model/SQL extras: те же финальные 12 tests, 0.025 s, OK. Существующий полный файловый workflow completed/reopen/reapprove/copy/resume прошёл, model_calls=0.
- Статические проверки и native secret scan: Ruff/sync9/docs205/repository history и native Gitleaks 8.30.1 history/tree/negative probes — OK.

Общий unit suite повторно не запускался: новые domain modules ещё не подключены к runtime entrypoints; выполнены целевые protocol tests и existing base workflow smoke. Наличие P0 не подтверждает native integration или measurable subagent/hook benefit.

## Далее и ограничения

Следующий P1: coherent bounded snapshot/handoff service, роль-specific инструкции и read-only CLI/FastMCP интерфейсы подготовки задачи с последовательным runbook. Затем P2 adoption/provenance и P3 фиксированные local hooks; native opt-in adapters — P4 после фактической проверки возможностей/версий.

Субагенты и хуки в этой сессии не запускались/не активировались. Источники/output остаются недоверенными данными; hashes/role/budget fields не предоставляют прав. Результаты требуют review, human gates/decisions/semantic acceptance не автоматизируются. R1/M6/M8 и remote Actions result остаются открытыми. Секреты/.env/БД/рабочие кейсы не читались; внешние модели/API не вызывались. Стоимость и полная длительность IDE-сессии отдельно не измерялись. Это начало R3.1, не полная production readiness.
