# Проверенные варианты и человеческий выбор

`selection` связывает успешный strategy_options run с отдельным связанным critic run, затем по явной команде человека атомарно создаёт три канонических варианта, одно решение и неизменяемую квитанцию проверки. Примените миграцию `0015_strategy_selections`.

## Preview и запись

```powershell
psa-main selection preview demo OPTIONS_RUN_UUID CRITIC_RUN_UUID
psa-main selection record demo --input selection.json
psa-main selection show demo OPTIONS_RUN_UUID
```

Preview ничего не записывает и не вызывает модель: показывает options/comparison/gaps/caveats, critic, закреплённые source revisions, source_hash/critic_hash и устаревшие источники. Это материалы для решения, а не готовое разрешение. Скопируйте hashes из проверенного preview; UUID ниже замените реальными. Файл команды заполняет человек по итогам просмотра:

```json
{
  "source_run_id": "OPTIONS_RUN_UUID",
  "critic_run_id": "CRITIC_RUN_UUID",
  "source_hash": "64_HEX_FROM_PREVIEW",
  "critic_hash": "64_HEX_FROM_PREVIEW",
  "decision_key": "export-pilot",
  "selected": "O1",
  "rejected": ["O2"],
  "deferred": ["O3"],
  "owner": "Ответственный за решение",
  "rationale": "Выбираем ограниченный эксперимент для проверки спроса.",
  "review_trigger": "Пересмотреть после обратной связи пилота.",
  "review_note": "Проверены источники, сравнение, допущения и замечания critic.",
  "critic_resolution": "Принимаем только эксперимент; спрос и эффект ещё не подтверждены.",
  "confirmed": true
}
```

Для O1/O2/O3 требуется ровно одна disposition на каждый вариант: selected/rejected/deferred. Owner, rationale, review_trigger и review_note обязательны; confirmed должен быть настоящим JSON boolean true. Отрицательный или uncertain verdict critic требует отдельного непустого critic_resolution. Supported verdict не заменяет человеческое подтверждение. `can_record` в preview означает только актуальность источников: он не утверждает разрешения или полноту заполнения человеческой команды.

## Гарантии и ограничения

- Проверяется schema, полнота critic item coverage, его input_run_id/hash и точные цитаты исходных ревизий. Повреждённые/чужие/неуспешные runs и insufficient_evidence не принимаются.
- Hashes фиксируют просмотренные материалы. При изменившемся critic/вариантах нужно получить новый preview. Если после анализа появилась новая ревизия источника, новая запись блокируется до нового анализа и critic; это также проверяется под транзакционными блокировками.
- Одна транзакция сохраняет три OptionRecord, DecisionRecord с тремя dispositions и StrategySelectionRecord с source/critic hashes, исходными draft/critic/contexts и человеческой командой. Project-bound FKs защищают ссылки. Конфликт canonical key/исходных данных откатывает весь набор, включая уже вставленные варианты.
- Один source run канонизируется один раз. Идентичная нормализованная команда, включая owner/notes/hashes, возвращает прежнюю квитанцию даже после последующих изменений источников. Другая команда к тому же source run отклоняется; это не API редактирования решения. Rejected/deferred lists нормализуются по порядку. Четыре конкурентных одинаковых вызова дают одну квитанцию.
- O1/O2/O3 остаются локальными ID draft; receipt.option_ids связывает их с UUID канонических вариантов. Ключи канонических вариантов — ai-RUNHEX-o1/o2/o3; ключ решения задаётся человеком. Варианты сохраняют status proposed, выбранный UUID фиксируется в решении. Гипотезы не становятся фактами: claim/evidence/capability records автоматически не создаются, AI strengths/сравнительные оценки не переносятся как подтверждённые преимущества. Полный исходный материал остаётся в review_snapshot.
- Эта операция не выдаёт workflow approval и не меняет этапы. Owner — заявленное имя, не аутентифицированная identity; receipt явно возвращает identity_verified=false. MCP-клиент отвечает за получение явного человеческого указания, сервер не может доказать, что поля ввёл человек. Не вызывать запись автоматически по model verdict.
- Заметки и источники являются данными, не исполняются. Эта техническая проверка не доказывает экономическую обоснованность выбора; downstream стратегия и review/revisit остаются отдельными этапами.

## MCP и проверки

Main FastMCP теперь содержит 12 tools: добавлены psa_main_preview_selection, psa_main_record_selection (idempotent write) и psa_main_get_selection. Record принимает `selection` объект той же SelectionCommand, что CLI input JSON. Доступ к файлам клиента для этой операции не нужен; ключи модели не требуются.

```powershell
python -m unittest discover -s tests
python scripts/smoke_strategy_selection.py
```

Smoke на PostgreSQL и MockTransport проверяет stale checkpoint при записи, critic resolution, concurrent replay, rollback после конфликта decision key, project FKs, CLI/настоящий stdio MCP parity, отсутствие новых claims/workflow approvals и отсутствие модельных вызовов при выборе. Synthetic analysis/critic тоже используют только фиксированные ответы. Сценарий включён в CI postgres job.

Диаграмма: [strategy-selection.mmd](../diagrams/main/strategy-selection.mmd).
