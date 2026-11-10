# Явный пересмотр завершённого workflow

```powershell
psa workflow review CASE
psa workflow reopen CASE --stage strategy --by OWNER --reason "Основание пересмотра" --review-hash HASH --expected-workflow-version N --operation UUID
```

Read-only review возвращает status/stages, историю approvals/reopen, claim impact, workflow version и hash просмотренного снимка. Hash связывает точные state/events bytes и fingerprints всех non-journal case inputs, включая authored drafts, источники и generated artifacts. Это снимок для обсуждения, не semantic approval или разрешение reopen. Изменение файлов даже без увеличения версии требует нового review.

Reopen выполняется только по явному указанию человека. Автор, причина, выбранный этап, review hash и expected version обязательны. Имя — self-reported attribution, не authentication. MCP `psa_review_workflow` / `psa_reopen_workflow` используют тот же service. Review допустим для любого текущего этапа; reopen — только для completed workflow с согласованным stages=done. Возврат незавершённого workflow на предыдущий этап пока не реализован.

## Что меняется

Допустим любой рабочий этап intake…validation. Выбранный становится in_progress, последующие — not_started, включая completed; предыдущие остаются done. State получает reopen_history; event сохраняет from/target, автора/причину/время, snapshot hash, invalidated stages и IDs исторических approvals. Decisions, claims, options, capabilities, drafts и generated artifacts не переписываются. Старые approvals сохраняются без расширения их действия: после reopen ориентируйтесь на текущий stage и проходите выбранный и последующие gates заново. CLI resume и MCP status показывают reopen history.

При возврате к strategy или более раннему этапу новый strategy/validation gate требует новое явное человеческое решение после reopen. Можно осознанно подтвердить тот же вариант новой записью; автоматического подтверждения нет. Guard проверяет reconstructed immutable decision result и completion receipt, а не только timestamp/ID root record. Frozen v4 event record_id иногда содержит option ID, поэтому он не используется как единственное доказательство нового D-ID. Подмена текущей записи относительно journal result не проходит. Legacy решение без такого proof не принимается как новое.

Возврат только к validation сохраняет существующий выбор, если его основания по-прежнему проходят текущие проверки. Он не снимает blockers inactive evidence/current decision review. Любой новый validation gate после reopen требует свежий render v2. Старый render replay/adoption не заменяет новую генерацию. Existing coverage, strategy sections, promise proof, measurement checks и явный человек для gates остаются обязательными.

## Journal и восстановление

Используется общий workflow v1 state/events bundle с новым request kind workflow_reopen; v1–v5 исторические операции поддержаны. Loader полностью реконструирует after-state/event по captured request, before-state/events, inputs и timestamp. Новые receipts требуют обновлённый runtime; hashes обеспечивают integrity, не защиту от владельца, переписывающего весь каталог.

Одинаковый завершённый UUID/request возвращает прежний event до повторного review и не сбрасывает последующие writes/gates. Другой request под тем же UUID — conflict. ACTIVE блокирует участвующие entrypoints; `psa workflow pending CASE` и `psa workflow recover CASE --operation UUID` завершают точную сохранённую операцию. Проверены реальные остановки на preparation/ACTIVE/state/events/receipt/completion, перенос case directory и сохранение позднейших записей. Общие byte/file limits и ограничения power loss/NAS — в [recovery contract](workflow-recovery.md).

Отзыв источников реализован отдельной [операцией](source-withdrawal.md). Этот срез не оценивает semantic/numeric alignment и не заменяет независимую оценку. Live R1/M8 и M6 остаются отложенными.
