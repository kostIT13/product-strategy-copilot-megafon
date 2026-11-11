# Проверка числового фрагмента baseline

```powershell
psa validation check CASE
psa validation numbers CASE
```

FastMCP: `psa_check_baseline_numbers`. Это read-only проверка одного автором выбранного числового литерала и единицы для reported baseline. CLI возвращает exit 3 при blocked; literal_match и not_applicable — exit 0. Нет записей, моделей, сети или запуска эксперимента. Используются общий case lock, bounded validation Markdown и тот же current claim/source proof, что у promises/reported baseline.

## Авторский anchor

Рядом с полным `psa-validation-v1` block в drafts/validation-plan.md добавьте ровно один `psa-baseline-number-v1`. Пример ниже иллюстративный: он предполагает baseline.value=75, baseline.claim_id=C-001, metric.unit="%" и уже прочитанную/зарегистрированную цитату `Baseline is 75 %.`:

```psa-baseline-number-v1
{
  "schema_version": 1,
  "claim_id": "C-001",
  "source_id": "S-ABC123",
  "locator": "paragraph:1",
  "quote": "Baseline is 75 %.",
  "decimal_separator": ".",
  "number_span": {"start": 12, "end": 14},
  "unit_span": {"start": 15, "end": 16}
}
```

Spans — индексы Unicode code points от нуля, end не включён; это не UTF-8 byte offsets. Число и единица должны быть непустыми, не пересекаться и находиться внутри quote (до 500 символов). Цитата/source ID/locator должны точно совпадать с одной записанной citation текущего baseline claim. Новая неподтверждённая цитата в anchor не создаёт evidence. Hidden/commented/example-fenced blocks не считаются; дубликаты JSON keys, лишние поля и некорректные spans отклоняются.

Поддержаны signed ungrouped decimals; decimal_separator по умолчанию точка, запятая задаётся явно. Сравнение через Decimal без допуска, округления, scaling, пересчёта процентов/денег или unit aliases. Выбор части токена (75 из 175, 1 из 1e3 или 1/2, префикс дроби) и неоднозначные соседние/grouped literals блокируются. Для неподдержанного формата нужен отдельный контракт, а не подбор anchor ради зелёного результата. Единица сравнивается буквально с metric.unit; запись "%" не отождествляется со словом "процентов" автоматически.

## Что подтверждает результат

Literal_match требует одновременно current active factual claim proof, точную recorded citation, правильные spans, совпадение Decimal baseline.value и выбранного токена и буквальное совпадение единицы. Изменённые source hash/revision, withdrawal claim/source, неподтверждённые bindings, чужой claim ID и mismatch числа/единицы блокируют результат. Unknown/null baseline возвращает not_applicable, числовое совпадение ему не приписывается. Malformed measurement plan возвращает blocked.

Packet содержит baseline evidence, anchor, issues, fingerprints и review_hash; он меняется при изменении draft/evidence/state. `numeric_literal_matches` / `unit_literal_matches` true только при успешной проверке всего packet. Общие `numeric_alignment_verified`, `semantic_alignment_verified`, `source_truthfulness_verified`, `experiment_approved` и `workflow_approval_granted` остаются false.

Человек отдельно оценивает, относится ли выбранное число именно к нужной метрике, аудитории, периоду, условиям, знаменателю и методике измерения. Совпадение 75 и "%" в цитате не доказывает, что это retention нужной когорты или пригодная baseline. Отдельная unit literal может относиться к другому числу той же цитаты — смысловая связь не выводится автоматически. Actual outcomes/эффект и разрешение эксперимента также не следуют из проверки.

Standalone command остаётся read-only. [Semantic validation review](semantic-review.md) после adoption требует этот preflight для reported baseline; старые validation check/receipts и legacy gates без audit сохранены. Следующие задачи R3 — более широкий numeric alignment, приёмка нового кейса и глобальная policy migration legacy. Полнота стратегий/measurement plan, coverage/verify/promises и явный выбор человека остаются самостоятельными требованиями.
