# P6c: происхождение usage/cost без повышения доверия

Срез от 17.11.2026 дополняет [P6a](operation-diagnostics.md) и [P6b](operation-summaries.md). Это read-only отчёт существующего usage.jsonl выбранного кейса; старые ledger, append/replay receipts и usage report не меняются.

```text
psa diagnostics usage case --projects-dir PATH
```

FastMCP: `psa_diagnose_usage(project_id, projects_dir="projects")`, readOnlyHint=true/destructiveHint=false. Instructions root, provider credentials и запуск модели не требуются.

## Декларация и измерение

У canonical v1 cost уже есть certainty measured/estimated/unknown. Эти labels записаны вызывающей стороной, а receipt не подтверждает способ получения числа. Новый отчёт сохраняет basis, но обязательно показывает basis_provenance=recorded_declaration и verified=false. Source_authentication=not_performed и independent_verification_performed=false: hash не превращает утверждение пользователя/провайдера в независимо проверенное измерение.

| Данные | Что показывает отчёт |
|---|---|
| Cost с certainty=measured | Записанная декларация measured, без независимой проверки |
| Cost с certainty=estimated | Записанная декларация estimated, без независимой проверки |
| Нет cost amount | Value/unit=null, basis=unknown; валюта по умолчанию не становится известной стоимостью |
| Tokens/duration | Значение сохраняется, basis=unknown/basis_provenance=not_recorded: v1 не хранит метод измерения этих полей |
| Явный0 или cost="0"USD | Значение0 и указанная валюта сохраняются, без вывода о бесплатности всех операций |

Coverage считает присутствующие/отсутствующие значения, а не проверенные измерения. Declared_cost_basis_counts считает декларации. Totals=null/aggregation=not_computed: отчёт не смешивает currencies, unknown и неоднородную provenance. Legacy usage report сохраняет прежние суммы reported values и не является независимым подтверждением расходов.

## Привязка и приватность

Source содержит фиксированное имя usage.jsonl, поддерживаемый schema_version1 и SHA256 прочитанных bytes файла. Каждая строка получает row_sha256 исходной непустой JSONL строки без line delimiter; file hash учитывает весь файл, включая whitespace/переносы. Business_operation_sha256 связывает точную записанную operation_id, не раскрывая её свободный текст. Event_id USE-N сохраняется.

Provider/model, operation text, raw business operation_id, at/stage, pricing_as_of и note не возвращаются. Hash — идентификатор содержимого, не шифрование/анонимизация и не подпись источника. Measurement_evidence_binding=null: v1 не содержит отдельной проверенной привязки measurement evidence. Automation_operation_binding=null: business operation_id свободный, его нельзя автоматически считать task/result/hook UUID или использовать для двойного подсчёта.

Для subagent-result usage P6a/P6b продолжают показывать self_reported с basis=unknown. Новая проекция canonical ledger не объединяет эти каналы и не подменяет их provenance.

## Границы чтения

Reader открывает только usage.jsonl выбранного существующего кейса под прежним case lock. Сохраняются canonical-workflow-pending/busy отказы и confinement; symlinks/junctions не обходятся. Источники, role guidance, .env и IDE config не читаются. Лимиты:2MiB и1000 непустых записей. Превышение, unsupported schema, extra fields, duplicate event/business identity, malformed JSON/UTF-8 или несовместимые amount/certainty — ошибка целиком, без partial report и без repair.

Projection строго проверяет известные v1 fields, но не обновляет их и не меняет старые hashes/receipts. Scope model_called_by_diagnostic=false относится только к текущему чтению, а не ко всем прошлым операциям кейса. Records_changed/workflow_approval_granted=false. Никакой pricing lookup, LLM/network call, retry или human gate не выполняется. Participating lock не гарантирует транзакцию с внешним редактором/power-loss/NAS; hash описывает прочитанные bytes.

Проверены source/row/business hashes, declared basis, privacy canaries, явные нули/null, legacy report/byte preservation, missing measurement bindings, schema/bool/duplicate/cost negatives,1000/1001 и byte limits, реальный Windows junction, canonical pending refusal и точная CLI/real-stdio parity. Другие ОС и native IDE acceptance этим прогоном не удостоверены.

P6c реализован в пределах provenance inspection. Verified provider/IDE measurement evidence не получено; budget enforcement/cancel не выводятся из cost labels. [P6d CLI control policy](operation-controls.md) и сверка P6 реализованы; далее независимый P7a inventory/eval; native controls зависят от отложенной P4. P4/P5/R1/M6/M8 остаются открытыми.

Для сумм времени, расходов и повторов по категориям используйте [сводку по кейсу](case-effort.md). Диагностика отдельных строк продолжает показывать происхождение значений.
