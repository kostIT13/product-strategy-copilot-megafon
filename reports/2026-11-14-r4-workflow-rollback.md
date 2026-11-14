# R4: явный возврат незавершённого workflow назад

Завершено: 14.11.2026 20:29 (Asia/Novosibirsk). Ветка `feature/main-solution-roadmap`.

## Что изменилось

Отдельные WorkflowRollback model/planner и application service используют существующий snapshot/publication port и файловый journal. CLI `psa workflow rollback` и FastMCP `psa_rollback_workflow` принимают actor/reason, target_stage, текущие workflow review hash/version и caller UUID. Операция доступна только для активной работы и строго более раннего этапа. Same/forward/completed и несогласованные stages отклоняются; completed по-прежнему использует reopen.

Выбранный этап становится in_progress, последующие not_started; workflow_version увеличивается. State rollback_history и workflow_rolled_back event сохраняют происхождение возврата и invalidated approval IDs. Реестры, материалы, решения, прежние approvals и reopen history не меняются. CLI resume/MCP status/review показывают историю. Явная инструкция человека требуется только для действий в продуктовом кейсе; все approvals в проверках — изолированные synthetic fixtures.

Journal loader детерминированно реконструирует after-state/event по before-state/request/inputs/time; подмена after-state при пересчитанных hashes отклоняется. Используется существующий bundle v1 и root schema 1 с новым request kind; новые receipts требуют обновлённый runtime. Frozen v1–v7 history поддержана, прежний semantic hash без rollback_history не меняется.

Повторные strategy/validation gates требуют нового явного решения после возврата, свежего render и действующих обязательных semantic assessments. Rollback инвалидирует semantic content binding, сохраняет required policy и не разрешает обход stale review. Старые completed rollback/gate/review replay возвращают исторический результат и не сбрасывают поздние записи. Interrupted publication восстанавливается явным workflow pending/recover точного UUID.

## Коммиты

1. `e0dbd86`: domain/service, v1 journal reconstruction, gate/render/semantic binding и семь core tests.
2. `448d11b`: CLI/FastMCP, status/resume history и real stdio tests.
3. `8bb1e11`: отдельная проверка required policy/fresh reviews и уточнение сообщений guards/port contract.
4. Documentation/report commit: контракт, workflow/quality canon и 9 adapters, README/MCP, планы и timestamp.

## Проверки

- Core: **7 tests, 51.556 s, OK**. Сохранение материалов/approvals/history, backward-only, stale hash/version, busy, inconsistent stages, request conflict, historical gate replay, новый decision/render, semantic binding, forged rehashed after-state.
- Public required-policy integration + CLI/resume + real FastMCP: **3 tests, 20.502 s, OK**. Прежние reviews не проходят после rollback; fresh strategy/validation selection снова завершает workflow. Исторический semantic receipt recovery сохраняет поздний state.
- Реальные process interruptions на preparation/ACTIVE/state/events/receipt/completion: copy/recover/replay каждого случая и сохранение поздних writes, без повторного возврата.
- Clean base без MCP/model/SQL extras: **10 tests, 63.129 s, OK (skipped=1: MCP extra отсутствует)**.
- Full suite на окончательном коде: **426 tests, 804.799 s, OK (skipped=1: Windows symlink privilege unavailable)**. Ruff/sync9/docs190/repository history/native Gitleaks 8.30.1 history/tree/negative probes — OK. Это локальный результат, не remote Actions run.

## Границы и план

Это технический срез R4; R3 не закрывается без нового разрешённого кейса и содержательной проверки numeric coverage. Реальные IDE/host R1/M8 и независимая M6 остаются отложенными. Изменения не подтверждают качество стратегии/эффект и не дают permissions. Hashes обеспечивают integrity, не защиту от владельца, переписывающего весь каталог. Ограничения power loss/NAS и размеров общего journal сохраняются.

Реальные кейсы/.env/БД не читались/не менялись. Новые hooks/subagents/БД/контейнеры и model/API calls не добавлялись; стоимость и полная длительность IDE-сессии отдельно не измерялись. Продуктовый кейс ради разработки не создавался.
