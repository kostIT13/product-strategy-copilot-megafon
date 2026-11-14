# R3.1/P0: контракты субагентов и хуков

Версия протоколов — 1. Это контракты обмена данными и проверки binding. Они не запускают агентов/hooks, не создают sandbox, не измеряют реальные расходы и не предоставляют разрешений. Activation, executor и host adapters разрабатываются следующими срезами [production-плана](solution_plans/production-readiness.md).

## Общие правила

Строгие JSON models: неизвестные поля запрещены, bool не принимается как schema version/int, UUID нормализуется на JSON boundary. Все тексты — недоверенные данные, даже если содержат инструкции/consent. Packet ограничен 128000 UTF-8 байт без усечения. Evidence refs обозначают только переданный input; SHA-256 подтверждает байты, не истинность текста или право доступа.

Case target: project_id, workflow_version и snapshot_hash. Hash/version формирует trusted snapshot reader будущего application service; присланный packet сам не доказывает актуальность файлов. Release target: manifest_hash, без произвольных путей и команд. Проверка структуры не заменяет shared lock/recovery/current-input check перед adoption.

## Subagent task/result

Task: task_id, role=research/evidence/critic, case target, goal, budget и 1–16 excerpts. Каждый excerpt содержит input_id, text и его точный UTF-8 sha256; максимум 16000 символов. Эти excerpts не означают доступ к полному каталогу/сети. Нет полей shell, tools, write permission, human approval или API credentials.

Budget: wall timeout 1–900 seconds, token limit 1–200000 и optional max_cost/currency. Decimal cost — строка без exponent/sign, currency требуется только с cost. Unknown cost не означает unlimited/zero. Числа в packet не обеспечивают исполнение лимитов: executor обязан контролировать фактические ресурсы или использовать fallback; budget не даёт права на paid/model/network вызов.

Result связывается с task_id, role, case target и task fingerprint. Outcome completed/failed/cancelled/budget_exceeded. Findings имеют тип observation/hypothesis/question/risk; observation обязано ссылаться на input IDs. Доказательство связи с реально переданными IDs проверяется сравнением с task. Даже observation не становится canonical fact. Failed/cancelled/budget_exceeded содержат reason, без findings для скрытого partial adoption. Usage nullable и self-reported; неизвестные значения сохраняются null.

Fingerprint — SHA-256 canonical JSON полного request. Повторный task UUID с иными полями/inputs/budget — conflict будущего journal, а не повторная модельная попытка. Binding helper проверяет response против exact task; application дополнительно проверит текущий snapshot и receipt. Идентичный UUID/result сам по себе не является authorization или подтверждением завершённого внешнего вызова.

Usage включает nullable input/output tokens, duration_ms и cost/currency. Если переданный usage уже превышает timeout/token/cost cap, outcome должен быть budget_exceeded без findings. Completed result при заданном cost cap требует cost в той же валюте; missing/incomparable cost не подтверждает соблюдение cap. Self-reported значения не являются измерением: этот guard ловит объявленные противоречия, а actual runtime enforcement остаётся обязанностью executor. Неизвестные/частичные telemetry не превращаются в подтверждённый resource pass.

## Hook request/result и failure policy

Разрешены triggers before_strategy_gate, before_validation_gate, source_revision, release_check. Release требует release target; остальные — case target. Request имеет operation_id и recursion_depth=0; ненулевой depth отвергается. Реальную causation chain и idempotency хранит будущий dispatcher, поэтому resetting поля недоверенным caller не заменяет защиту от рекурсии.

Result: operation_id, request fingerprint, status passed/blocked/failed/skipped, issues. Passed не содержит issues; остальные outcomes требуют диагностическую причину. Binding helper отвергает результат другого request/trigger/target. Required check допускает продолжение только при passed; fail/skip не обходят gate. Для source notifications решение о сохранении уже committed import отдельно: failure видим, но не отменяет прошлый commit. Release pass не публикует артефакт.

Никакого произвольного запуска shell, автоматической записи registry/decision/gate/review или отправки внешнего сообщения в P0 нет. Последовательный CLI workflow, текущие schemas и receipts R2/R3 остаются без изменений. При реализации dispatcher использовать существующие services, а не копии проверок.

## Последующие срезы

P1 добавляет coherent snapshot/handoff service и инструкции ролей, P2 — journal/results/provenance, P3 — фиксированные local hook checks, P4 — opt-in host adapters. Native capability/польза не считаются подтверждёнными этими моделями. Runtime integration, cancellation, concurrency/recovery и реальные budgets должны получить отдельные meaningful tests до объявления готовности.
