# Отзыв источника и зависимых оснований

```powershell
psa source impact CASE
psa source withdraw CASE S-ID --by OWNER --reason "Почему источник больше нельзя использовать" --operation UUID --expected-workflow-version N
```

MCP: read-only `psa_source_impact` и `psa_withdraw_source`. Отзыв выполняется только по явному указанию человека. Автор и причина обязательны; имя является self-reported attribution, не authentication. Optional expected version защищает от записи поверх изменившегося workflow; caller UUID обеспечивает точный replay.

## Канон и область отзыва

Отзывается весь source ID, включая его применение как текущего основания после прежних revisions. Это не выборочная отмена одной выдержки. Исходная строка sources.jsonl, тексты, архивы revisions, claims, capabilities/options/decisions и approvals остаются без изменений. Raw source status extracted описывает извлечение; effective status withdrawn вычисляется по событию. CLI source list и renderer показывают effective status. Возврат withdrawn source в active/extracted eligibility отдельной командой пока не реализован.

Workflow v6 публикует только state/events с snapshot/hash источника, автором, причиной, timestamp и impact. Captured ledger inputs до 4 МиБ позволяют полностью реконструировать after-state/event при replay/recovery. Общие metadata targets ограничены 512000 байтами; limits не приводят к усечению. Source registry должен совпадать с immutable snapshot отзыва; последующая ручная подмена метаданных вызывает integrity error.

## Evidence и зависимые решения

Effective active claim с source ID отозванного источника получает derived status source_withdrawn. Для claim с несколькими sources отзыв любого из них блокирует текущую запись целиком: система не переоценивает достаточность остальных оснований автоматически. Явные withdrawn/superseded statuses сохраняются. Impact показывает withdrawn source IDs, прямо зависимые claims и affected options/capabilities/decisions, включая selected/rejected options. Это структурный анализ ссылок, не распознавание всех смысловых зависимостей.

Coverage, promises, reported baseline и новые gates исключают такие claims. Текущее затронутое решение требует нового явного выбора человека; доступность capability и история решений автоматически не переписываются. Source_collection считает только effective extracted sources. Новые claim/correction/support records не принимают отозванный источник/неактивное основание. После повторного анализа разрешённых независимых материалов человек может явно указать [claim correction](claim-correction.md), обновить supports/drafts и пересмотреть решение. Копирование отозванного материала под другим ID не создаёт нового доказательства.

Поиск и citation snapshot исключают отозванные источники из результатов, но проверяют canonical paths/hash/UTF-8 всех сохранённых current texts. Корпусные limits/bytes учитывают весь проверяемый корпус. Verify сохраняет source integrity и historical schema/ref checks; inactive claim citations не выдаются за текущие. Renderer v2 отмечает withdrawn sources как audit history и source_withdrawn claims как неактивные. Critic-pack исключает неактивные claim statements. После source withdrawal новый validation gate требует свежий render v2; старый replay/adoption недостаточен.

## Импорт, повтор и восстановление

Новый импорт/revision известного withdrawn source отклоняется до acquisition, включая сохранённый requested URL. Если другой URL перенаправляет к отозванному final source ID, это обнаруживается после acquisition и до публикации. Автоматической реактивации нет. Завершённый старый import UUID возвращает исторический результат до acquisition и не меняет текущую eligibility.

Завершённый withdrawal UUID/request возвращает прежний event, даже если после него были другие writes. Другой request под тем же UUID — conflict; другой UUID для уже withdrawn источника также отклоняется. Общие case lock/ACTIVE guards и `psa workflow pending CASE` / `psa workflow recover CASE --operation UUID` действуют как прежде. Recovery проверяет captured inputs, before/after targets и полную реконструкцию event/impact; простой пересчёт manifest после подмены impact недостаточен. Старые workflow v1–v5 сохранены, для новых v6 receipts нужен обновлённый runtime. Общие границы filesystem/power loss/NAS описаны в [recovery contract](workflow-recovery.md).

Completed workflow не открывается автоматически: используйте [явный review/reopen](workflow-reopen.md) после человеческого выбора. Semantic/numeric alignment, reactivation источника, rollback незавершённого workflow, live IDE R1/M8 и независимая M6 не закрываются этой функцией.
