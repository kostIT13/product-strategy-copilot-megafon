# R3: required policy новых кейсов и explicit legacy enablement

Начато: 11 ноября 2026. Работа возобновлена 14 ноября 2026; завершено 14.11.2026 19:22 (Asia/Novosibirsk). Ветка `feature/main-solution-roadmap`. Timestamp и результаты записаны также в development-log.md. Итерация разделена на пять смысловых коммитов.

## Коммиты и поведение

1. `e6219b6`: current initialization seed с required policy, creation receipt v2, поддержка frozen v1 и strict policy model; отдельные initialization/model tests.
2. `7a95cc5`: enforcement первого strategy/validation gate, snapshot-bound legacy enablement service/port/files adapter, workflow v1 reconstruction/recovery, anti-downgrade и integration tests.
3. `9d70167`: CLI `psa policy show/enable`, FastMCP `psa_quality_policy` / `psa_enable_quality_policy` и real stdio parity.
4. `e03d326`: ordinary workflow bundles не могут добавлять/менять/удалять policy в after-state, даже при rehashed manifest.
5. Отдельный docs/report commit: quality canon/9 generated adapters, контракты/README/MCP, основной план/roadmap и timestamp.

Публичный init создаёт state schema 1 с quality_policy={schema_version:1, semantic_review:required}; layout не меняется. Receipt format 2 фиксирует mandatory profile. Новые strategy/validation approvals не проходят без current accepted review даже при пустой audit history. В init нет legacy/disable опции. Frozen v1 seed/receipt поддержаны для historical recovery и явно выделенных legacy fixtures; первоначальные поведенческие assertions старых tests не удалены, новые tests отдельно проверяют публичный default required path.

Удаление required policy обнаруживается по receipt v2 либо enablement event. Null/unknown/extra fields/boolean version не трактуются как legacy. Validation/live gates/recovery используют policy contract. Старый semantic content hash без policy сохраняет реконструкцию v7; включение policy добавляет новое binding и делает старые semantic assessments stale. Historical gate replay использует captured before-state и не сбрасывает позднейшую миграцию.

Policy show — read-only status/mode/history/hash/version. Enable требует explicit human instruction по политике, actor/reason/reviewed snapshot hash/version и optional caller UUID. Workflow v1 публикует только state/events с deterministic after-state/event reconstruction, без нового bundle format. Статусы этапов, approvals, decisions, sources/drafts и supports сохраняются. Completed case остаётся completed; required policy применяется к будущим approvals/reopen. Нет disable/downgrade/массового авто-enable. Миграция пользовательских кейсов и demo не выполнялась.

## Проверки

- Финальный policy suite: **11 tests, 115.305 s, OK**, включая model/runtime/CLI-MCP/after-state protection. Первые 9 model/runtime tests (90.189 s) также прошли; новый rehashed gate after-state test отдельно — 1 test, 6.562 s, OK.
- Existing creation/recovery/concurrency/real-MCP tests: **11 tests, 19.217 s, OK**.
- New CLI/real-MCP policy parity: **1 test, 17.380 s, OK**.
- Negative cases: обязательный первый review, сохранение completed history/bytes, stale snapshot, removed/malformed policy, старый review после enable, rehashed policy-enable/gate after-state tamper; реальные process interruptions на preparation/ACTIVE/state/events/receipt/completion, copy/recover/replay/later writes.
- Clean base без SQL/model/MCP extras прошёл полный required-policy semantic review/gates → completed → reopen → новое решение/reviews → repeated gates → copy/resume.

Итоговый full suite 14.11.2026: 397 tests за 649.646 s, OK (1 skipped: Windows symlink privilege unavailable). Повторные Ruff, sync9, docs184, repository-history и native Gitleaks 8.30.1 history/tree/negative probes прошли без находок. Clean-base workflow и оба demo ранее прошли на окончательном коде; после возобновления код не менялся. Прерванный 11 ноября full run не оставил итоговой сводки; 14 ноября полный suite запущен заново. Кодовые коммиты e6219b6/7a95cc5/9d70167/e03d326 уже находились на origin при возобновлении; verification завершён; заключительный documentation/report commit фиксирует этот результат. Начатый full suite перезапущен после добавления after-state policy preservation, чтобы проверить окончательный код. Временный Windows file-mapping lock при formatting тестового файла устранён повторным запуском formatter; код и тесты прошли. В предыдущем semantic-review doc исправлен пример CLI gate: stage передаётся через --stage, не позиционно.

## Границы

Attribution self-reported, не authentication. Policy не является semantic assessment, новым human choice или разрешением эксперимента/публикации. Старые кейсы не изменяются самим обновлением программы. Прямое редактирование state/events/receipts не поддерживается; hashes не защищают от владельца, переписывающего весь каталог. Unknown future policy требует отдельной миграции, она не подменяется enable текущей версии.

Новый разрешённый кейс и более широкий numeric alignment остаются открытыми; live R1/M8 и independent M6 не закрыты. Более широкая production policy/архивирование/миграции будущих версий — отдельное hardening. Реальные кейсы/.env/БД не читались/не менялись; все тестовые actors/approvals — изолированные synthetic fixtures. Платные API/модели не вызывались, hooks/subagents/БД/контейнеры не добавлялись. Длительность и стоимость IDE-сессии отдельно не измерялись.
