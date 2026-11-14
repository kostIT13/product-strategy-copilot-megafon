# Возврат незавершённой работы на предыдущий этап

```powershell
psa workflow review CASE
psa workflow rollback CASE --stage evidence_review --by OWNER --reason "Что нужно пересмотреть" --review-hash HASH --expected-workflow-version N --operation UUID
```

FastMCP: `psa_rollback_workflow`. Только по явному указанию человека после показа workflow review. Actor, reason, review_hash и expected_workflow_version обязательны. Review не разрешает действие; имя — self-reported attribution, не authentication. Существенный выбор человека эта команда не меняет.

## Переход и история

Rollback действует на активном workflow intake…validation и только на строго более ранний этап: например validation → strategy или strategy → source_collection. На intake более раннего этапа нет. Тот же/следующий этап отклоняется; completed требует отдельного [reopen](workflow-reopen.md). Это не восстановление прежних файлов и не обход forward gates.

Исходные stages должны быть согласованы: предыдущие done, текущий in_progress, следующие not_started. Hash review связывает точные state/events bytes и fingerprints non-journal inputs, включая drafts, источники и generated artifacts. Изменение документа без увеличения workflow_version требует нового review. Изменившаяся версия, malformed state/history и busy/pending операция блокируют новый rollback.

Выбранный этап становится in_progress; последующие, включая completed, — not_started. Предыдущие остаются done. Увеличивается workflow_version; в state добавляется rollback_history, в events — workflow_rolled_back с from/target, actor/reason/time, review_hash, invalidated_stages и историческими approval IDs. Прежние approvals/reopen history, decisions, claims/options/capabilities, sources, drafts и generated artifacts сохраняются.

CLI resume, MCP status и workflow review показывают rollback history. Следующую работу определяют текущие status/stages; прежние согласования остаются историей. Команда не выдаёт разрешений на публикацию, эксперимент или обязательства.

## Повторные gates

Gates выбранного и последующих этапов проходят заново. При возврате к strategy или раньше перед новыми strategy/validation gates нужно новое явное человеческое решение, даже при выборе того же варианта. Proof требует immutable journal result/completion receipt после возврата; правка decision-log или timestamp не заменяет решение. Проверки current evidence/withdrawal/coverage/структуры/measurement продолжают действовать.

Новый validation gate требует render v2 после rollback; старый replay/adoption не заменяет новую генерацию. Rollback меняет semantic content binding, поэтому старые accepted reviews не подтверждают новую итерацию. Required policy сохраняется; после adoption/при required policy нужны свежие strategy и validation assessments и явный выбор их UUID в gates. Не переподтверждать reviews/решение автоматически.

## Journal, replay и recovery

Используется workflow v1 state/events bundle с новым request kind workflow_rollback; root state schema остаётся 1. Loader реконструирует весь after-state/event по captured request, before-state/events, inputs и timestamp. Подмена stages/истории при пересчитанных manifest hashes обнаруживается; общий guard запрещает изменение quality_policy этой операцией.

Completed caller UUID/request возвращает исходный event до повторной проверки текущего этапа/hash/version и не меняет поздние записи. Другой request под тем же UUID — conflict. Replay прежнего gate тоже исторический и не перепрыгивает повторные этапы. Новый UUID требует актуального review.

После сбоя используйте `psa workflow pending CASE`, затем явный `psa workflow recover CASE --operation UUID`. Восстанавливается точная сохранённая операция, а не новый возврат. ACTIVE guard блокирует обычные entrypoints до recovery; конфликтующие входы сохраняются для ручного разбора. Проверены реальные остановки на preparation/ACTIVE/state/events/receipt/completion, copy/recover и сохранение поздних writes. Byte/file limits, ограничения power loss/NAS и integrity относительно владельца каталога — в [recovery contract](workflow-recovery.md).

Кейсы без rollback_history и исторические v1–v7 bundles поддержаны; прежний semantic content hash без нового поля сохраняется. Новые rollback receipts требуют runtime с поддержкой этого request kind. Этот технический срез R4 не заменяет новый разрешённый кейс R3, реальные IDE/host проверки R1/M8 или независимую M6.
