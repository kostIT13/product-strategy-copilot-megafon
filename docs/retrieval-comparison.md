# P7b: сравнение lexical candidate с literal baseline

Статус 17.11.2026: эксперимент завершён, candidate отклонён из-за потери precision. Production CLI/FastMCP продолжают использовать `literal_ignore_case_v1`. Никакого provider/index/RAG или автоматической активации не добавлено.

До реализации отдельно зафиксированы [набор и критерии](../evals/retrieval/p7b-protocol.md), commit `88960f1`. Набор синтетический и размечен тем же разработчиком, поэтому это не независимый или слепой benchmark. Код эксперимента зафиксирован в `adae42f`, provenance-формат уточнён в `fa36406`. [Машинный результат](../reports/2026-11-17-p7b-retrieval-run.json) получен на `fa36406` с dirty=true (подготовленные docs/reports); hashes связывают фактические исходники, это development snapshot. JSON содержит source/input/protocol hashes, Python/OS/dependency versions, per-query/per-category ошибки и timing.

```powershell
python -m scripts.evaluation.retrieval_compare
python -m unittest discover -s tests -p "test_retrieval*.py" -v
```

## Результаты

Одинаковые 10 sources, 16 queries и k=3; golden relevance — пара source_id/locator. Baseline не изменён. Candidate `literal_then_token_window_v1` сохраняет существующие literal hits, а при их отсутствии ищет все различные word tokens в одном окне до 500 исходных символов одной секции. Нет stemming/синонимов или модели. Код находится только в `scripts/evaluation/`, не зарегистрирован как product tool.

| Показатель | Literal baseline | Token fallback candidate |
| --- | --- | --- |
| TP / FP / FN | 5 / 0 / 6 | 9 / 2 / 2 |
| Micro precision | 100% | 81.8% |
| Micro recall | 45.5% | 81.8% |
| Проверенные exact quotes | 5 | 11 |
| Среднее loop time, 5 повторов | 0.00162276 s | 0.00337044 s |

Дополнительно найдены reordered/separated tokens и numeric/XLSX fragments. Оба метода пропускают два смысловых перефразирования. Candidate добавляет два FP: слова из предложения, где запись отменяет оператор, не подтверждают запрос о действии пользователя; запрос `SLA.*` ошибочно ослабляется до слова SLA. Gold и пороги после запуска не менялись.

Recall вырос более чем на 10 процентных пунктов, existing baseline references сохранены, все quotes/hash/locators точны, локальный loop budget 0.10 s соблюдён. **Критерий «precision не ниже baseline» не выполнен**. Token fallback в таком виде исключён из adoption. Exact quote не делает фрагмент релевантным и не подтверждает интерпретацию роли или отрицания.

## Границы проверки

Kernel eval использует заранее подготовленные current snapshots с PDF/XLSX text markers; binary extraction/file lock не входят в timing. Null denominators/cost и неизвестные memory/file-load/human time сохранены. Внешних запросов и моделей нет. Набор мал, известен автору candidate, повторный запуск на нём не становится новым holdout. Время — локальное измерение без SLA и вывода о масштабировании.

Отдельный integration test применяет lifecycle из frozen JSON на temporary synthetic file case через штатные import/withdraw writers, затем читает настоящий source-search store. Obsolete/withdrawn tokens отсутствуют для обоих kernels; current hash найден; case bytes до/после чтения совпадают, socket calls запрещены в read phase. Existing `test_file_search.py` проверяет негативные границы и реальный CLI/FastMCP parity. Runner честно оставляет `lifecycle_and_negative_checks=separate_test_runs_required`; результат отдельных tests указан в [отчёте](../reports/2026-11-17-p7b-retrieval-comparison.md), не подменён kernel pass.

Source-instruction fixture возвращается только как недоверенная quote. Это не проверка LLM injection resistance, human gate, native IDE или independent review. Новые case approvals/решения и private IDE config не менялись.

P7c выполнен: [versioned registry существующих research tools](research-tool-registry.md) с permissions/provenance/limits/offline fallback и критериями выбора. Далее P7d — offline research scenarios и сверка оставшихся criteria P7. Candidate отклонён, поэтому его включение и дальнейшая настройка не являются следующим обязательным шагом. P7 целиком и независимый [agent-level eval P8/R5/M6](evaluation/README.md) остаются открытыми.
