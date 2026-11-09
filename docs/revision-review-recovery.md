# Review ревизии источника через workflow journal

R2: `psa revisit resolve` сохраняет явный review конкретной ревизии и перечисленных зависимых claims/решений через общий write-ahead state/events протокол. Сам [импорт/создание новой source revision](source-import-recovery.md) также перенесён на общий workflow v2 journal.

```bash
psa revisit list CASE
psa status CASE
psa revisit resolve CASE REVISION_EVENT_ID --by "Владелец решения" \
  --reason "Проверены изменения и затронутые выводы" \
  --reviewed-claim CLAIM_ID --reviewed-decision DECISION_ID \
  --operation 14a9b54b-1710-4a76-afb3-c91adb4d9d87 --expected-workflow-version 0
```

ID claims/решений нужно перечислить ровно по текущему revisit report; flags повторяются для каждого ID. При пустом dependency set соответствующие flags не передаются. Порядок ID канонизируется, повторы и пропущенные/лишние IDs отклоняются. Обязательны человек/роль и непустая причина; техническая аутентификация личности этим не выполняется.

Файловый MCP `psa_revisit_resolve` принимает те же поля, включая `operation_id` и `expected_workflow_version`. CLI/MCP вызывают RevisionReviewService, RevisionReviewStore port и FileWorkflowStore. Pure dependency mapping вынесен в domain, проверка файлов — в отдельный filesystem reader. Application service не читает filesystem напрямую.

## Проверки перед подготовкой

- Revision event должен существовать однозначно и иметь тип source_revised; новая операция поверх уже отмеченной reviewed ревизии отклоняется.
- В source registry должен существовать ровно один соответствующий источник с current_content_hash этой ревизии.
- Текущий extracted text и предыдущий архивный текст должны находиться внутри sources/ без symlink/junction/escape и совпадать с revision hashes. Хэши читаются потоково; отсутствующие/изменённые версии не восстанавливаются предположениями.
- Claims зависят от source ID. Decisions включаются через свои claim_ids, выбранный option и отвергнутые options, если options зависят от этих claims. Все ожидаемые IDs должны быть явно рассмотрены.

Все чтения, проверки и commit выполняются под общим case access lock. Новые значения `workflow_version` считаются совместно для gate, mode_change, revision_review и source_import. Review увеличивает только version/updated_at в state и добавляет один event в events.jsonl. Этап, режим, stages, approvals, claims/decisions не переписываются.

## Replay и recovery

Request имеет `kind=revision_review`. Caller UUID используется в общем workflow journal: совпадающий нормализованный request возвращает первоначальный event без нового review/сброса state. Изменённый request либо другой kind под занятым UUID отклоняется. Без UUID создаётся новый ID: retry без него не считается exact replay. Expected version опционален для совместимости; указанная версия проверяется до подготовки.

Используются те же [before/after bundle, ACTIVE и completion](workflow-recovery.md). `psa workflow pending/recover` и MCP `psa_pending_workflow`/`psa_recover_workflow` завершают exact operation. До завершения ACTIVE обычные команды блокируются; changed inputs/targets/integrity errors не перезаписываются. Копия case с journal переносима в другой projects-dir. Semantic validator связывает review с исходным revision event и запрещает изменение stage/mode/approval даже при согласованных payload hashes.

Исторические gate/mode bundles и legacy reviewed events не переписываются. Старый runtime, не знающий revision_review, не применять к новым bundles. Новая операция с другим UUID не дублирует review одной ревизии; exact replay старого UUID может вернуть исторический event после дальнейших изменений, но не расширяет рассмотренный список на новые зависимости или ревизии.

## Границы

Review означает запись человеческого рассмотрения точной ревизии/набора зависимостей. Он не исправляет claims автоматически, не доказывает истинность источника и не утверждает стратегию/публикацию. Обновление derived stale/re-review статусов при последующих изменениях — отдельная задача полноты R3.

Общие journal/input limits сохранены; JSONL capture ограничен 512000 байтами на файл. Raw/manual доступ обходит lock. Render и другие legacy writers ещё требуют переноса на recovery, затем import/retire старой SQL/container цепочки. БД/модель/Docker для этого review не нужны.
