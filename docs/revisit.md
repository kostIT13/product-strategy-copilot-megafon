# Пересмотр после изменения источника

```mermaid
sequenceDiagram
    actor Owner as Владелец проекта
    participant CLI as psa source add/fetch
    participant Source as sources.py
    participant Files as sources/ и sources/history/
    participant Events as events.jsonl
    participant Review as psa revisit

    Owner->>CLI: Повторно импортирует тот же URI
    CLI->>Source: Извлечь и вычислить content_hash
    Source->>Source: Сравнить с текущим source_id/hash
    alt Содержимое не изменилось
        Source-->>Owner: Обновить метаданные; ревизию не создавать
    else Содержимое изменилось
        Source->>Files: Архивировать текущую извлечённую версию
        Source->>Files: Записать новое содержимое по стабильному source_id
        Source->>Events: Добавить source_revised с прежним и новым hash
        Source-->>Owner: Сообщить о необходимости пересмотра
        Owner->>Review: psa revisit list PROJECT
        Review->>Files: Найти claims по source_id и связанные options/decisions
        Review-->>Owner: Список зависимостей и pending revisions
        Owner->>Review: resolve EVENT_ID с автором, причиной и всеми ID
        Review->>Events: Добавить source_revision_reviewed
    end
```

Изменение источника не переписывает журнал утверждений и не меняет человеческое решение автоматически. Старые цитаты остаются проверяемыми только по текущей версии; при устаревшей выдержке `psa verify` сообщит об ошибке. Владелец анализирует список, обновляет или подтверждает зависимые записи, затем фиксирует, какие claim/decision ID рассмотрены.

```powershell
# Сначала обновите содержимое по тому же URI/пути, затем повторно импортируйте его.
psa source add table-demo C:\path\to\same-updated-file.csv
psa revisit list table-demo
psa revisit resolve table-demo SRC-REV-0001 --by "Владелец решения" --reason "Проверены затронутые выводы; решение оставлено без изменений" --reviewed-claim C-001 --reviewed-decision D-001
psa verify table-demo
```

При `resolve` список `--reviewed-claim` и `--reviewed-decision` должен точно покрыть все зависимости, показанные для конкретной ревизии; если зависимостей нет, флаги не нужны. Ревизия и её рассмотрение остаются в `events.jsonl`. Предыдущий текст сохраняется в `sources/history/<source_id>/<sha256>.txt`.

## Контекст для предложений

`psa revisit context PROJECT SRC-REV-0001` и FastMCP `psa_revisit_context` возвращают хеши и выдержки обеих ревизий вокруг первого различия, текущую версию кейса, а также до 50 затронутых утверждений и 50 решений. При `partial: true` откройте требуемые части сохранённых материалов. Сверяйте даты, единицы, знаменатели и старые цитаты. Для исторической ревизии проверьте также последнее изменение, прежде чем предложить обновление текущей стратегии.

Покажите человеку, какие выводы сохраняются, требуют проверки или подлежат исправлению, и что меняется в рекомендации. Для принятых изменений используйте существующие команды исправления утверждений, изменения решения и рассмотрения ревизии. Контекст читается локально, запись ревью выполняется отдельной командой.

## Черновик пересмотра

Сохраните авторский JSON в удобном файле кейса. Возьмите `context_sha256` из последнего `revisit context`. Прочитайте затронутые записи и текущие черновики перед заполнением. Пример структуры:

```json
{
  "context_sha256": "<хеш из revisit context>",
  "change_summary": "Источник пересчитал показатель для того же периода.",
  "claims": {
    "C-001": {
      "action": "revise",
      "rationale": "Новый расчёт изменил численное утверждение.",
      "next_step": "Заменить утверждение после сверки знаменателя и новой цитаты."
    }
  },
  "decisions": {},
  "product_strategy": {"action": "keep", "rationale": "Сегмент и механизм остаются прежними."},
  "communication_strategy": {"action": "keep", "rationale": "В сообщениях показатель не используется."},
  "validation_plan": {
    "action": "recheck",
    "rationale": "Изменилась база сравнения.",
    "next_step": "Сверить формулу baseline и окно наблюдения."
  }
}
```

Проверьте файл командой `psa revisit check-draft ID SRC-REV-0001 --input proposal.json` или передайте его объектом `draft` в FastMCP `psa_revisit_check_draft`. Допустимые действия: `keep`, `recheck`, `revise`. Для последних двух нужен конкретный `next_step`. Проверка сверяет хеш контекста и допустимые ID. Если источники, реестры или связанные стратегии изменились, получите свежий контекст. Параметр `unaddressed_counts` показывает необработанные зависимости, в том числе записи за пределами выдачи первых 50. Результат остаётся черновиком для человека; для исправлений или закрытия ревизии используйте отдельные команды.
