# R3.1/P3c — уведомления о пересмотрах источников

Завершено 15.11.2026 18:27 (Asia/Novosibirsk). Разработка репозитория без использования рабочих продуктовых кейсов.

## Сделано

- RevisionSummary и отдельные source-notification port/service/file reader. Существующий build_revisit_report переиспользуется; в output только bounded counts и фиксированный revisit hint, без raw source/title/URI/instructions.
- Явный source_revision request привязан к current case snapshot/version. Он охватывает состояние revisions всего кейса; initial import без revisions даёт skipped. Pending revisions дают blocked + counts, reviewed revisions — passed, но оба notice outcomes не утверждают gate.
- Fixed worker P3b принимает source notice; timeout/watchdog, immutable journal, stale/conflict/replay/recovery сохранены. Существующие HookRun/Completion fields/нормализованные hashes не менялись, расширен только trigger validator и response wrapper.
- notification_delivered отделён от required_check_passed. Доставка current pending-revisit сообщения может быть успешной, сохраняя blocker для человека. Domain required_hook_allows никогда не допускает source_revision как required gate check, даже при passed после завершённого human review.
- CLI hook prepare-notification + существующий hook run; FastMCP psa_prepare_source_notification + psa_run_hook. New delivered notice CLI0, historical replay CLI1; inspection/recovery не объявляет delivery.
- Ошибка уведомления не вызывает импорт/rollback/resolve/gate, committed source/state/events остаются прежними. Review остаётся pending до явного человеческого действия. Captured notice из копии восстанавливается как historical artifact без новой delivery/required pass.
- [Runbook](../docs/source-notifications.md), README, MCP/automation docs и три плана обновлены: P3c реализован, далее release checks. Автоматический event dispatcher/host activation при импорте не включён.

## Проверки

- Final source notification suite11, 52.429 s, OK: bounded real worker, initial-vs-revision, pending/affected counts, явный fixture-human review, невозможность required pass, failures/recursion/unsafe fields/source instructions, captured-copy recovery, CLI exit policy и real FastMCP parity/fresh execution/replay.
- Before-gate runtime regression11, 118.830 s, OK: process timeout/watchdog, historical receipts, intent/prepared/committed process death и portable recovery, CLI/real stdio. P0 contracts12, 0.033 s, OK после изменения helper policy. Итого 34 разных целевых tests.
- Чистая base-установка без MCP/LiteLLM:11, 34.956 s, OK (1 ожидаемый MCP-extra skip), включая source worker и copy/recovery. Existing base completed/copy/resume/reopen/reapprove smoke OK, model_calls0, sql_dependenciesfalse.
- Ruff/sync9/tracked Markdown links, git diff checks OK. Native Gitleaks8.30.1 history/tree/negative probes проверены. Full suite репозитория не повторялся: затронутые механизмы, предыдущий worker/recovery и прежний base workflow проверены отдельно.

## Коммиты и границы

`eb9971c` — summary/service/worker/delivery policy/tests; `89be4a7` — CLI/FastMCP/parity. Итоговый docs commit сохраняет отчёт/планы/runbook.

P3 ещё открыт: далее release checks без публикации; native host acceptance/activation — P4. R1/M6/M8 не закрыты. Уведомление запускается явно после committed import и не считается review/разрешением обязательств. Изменения источников автоматически хук не запускают. Worker wall-time — не общий OS/CPU/memory sandbox и не subagent token/cost enforcement. Рабочие кейсы/.env/БД/volumes не читались/не менялись; внешние сообщения, модели, native subagents/host hooks не запускались. Все тестовые источники и человеческие роли — синтетические fixtures.
