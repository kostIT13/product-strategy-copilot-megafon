# Проверка авторских расчётов по текущим цитатам

```powershell
psa validation calculations CASE
```

FastMCP: `psa_check_calculations`. Команда read-only: читает validation Markdown и current factual evidence, возвращает arithmetic_match / blocked / not_applicable; exit 3 означает blocked. Ошибка чтения/целостности источников завершает команду ошибкой без частичного результата. Нет моделей, сети, записи результата в claims или выполнения произвольных выражений.

## Явные операции

| operation | Имена входов | Формула | result_unit |
|---|---|---|---|
| percentage | numerator, denominator | numerator / denominator × 100 | % |
| ratio | numerator, denominator | numerator / denominator | ratio |
| percentage_points | baseline, current | current − baseline | percentage_points |
| relative_change_percent | baseline, current | (current − baseline) / baseline × 100 | % |

Например, переход с 20% до 25% — **5 процентных пунктов** либо **25% относительного изменения**. Операцию и единицу выбирает автор; программа их не угадывает. Percentage здесь означает долю от целого: denominator > 0, 0 ≤ numerator ≤ denominator. Ratio требует denominator > 0; relative change требует baseline > 0, чтобы не выбирать неоднозначную конвенцию отрицательной базы. Percentage points требует две входные единицы "%"; остальные операции — одинаковые буквальные единицы входов. Не выполняются scaling, unit aliases или пересчёт валют/тысяч/процентов.

## Авторский block

Рядом с полноценным `psa-validation-v1` в drafts/validation-plan.md добавьте не более одного `psa-calculations-v1`. Пример ниже полностью синтетический: предполагает уже прочитанные и зарегистрированные C-001/C-002 с этими точными цитатами. Замените source/claim IDs и привязки реальными разрешёнными данными, не выдавайте пример за факт кейса.

```psa-calculations-v1
{
  "schema_version": 1,
  "calculations": [
    {
      "calculation_id": "CALC-001",
      "operation": "percentage",
      "period_relation": "same",
      "operands": {
        "numerator": {
          "anchor": {
            "schema_version": 1,
            "claim_id": "C-001",
            "source_id": "S-EXAMPLE",
            "locator": "paragraph:1",
            "quote": "Left is 3 users.",
            "number_span": {"start": 8, "end": 9},
            "unit_span": {"start": 10, "end": 15}
          },
          "context": {"metric": "Fixture count", "population": "Fixture cohort", "period": "Fixture window", "conditions": "Same counting definition"}
        },
        "denominator": {
          "anchor": {
            "schema_version": 1,
            "claim_id": "C-002",
            "source_id": "S-EXAMPLE",
            "locator": "paragraph:2",
            "quote": "Right is 4 users.",
            "number_span": {"start": 9, "end": 10},
            "unit_span": {"start": 11, "end": 16}
          },
          "context": {"metric": "Fixture count", "population": "Fixture cohort", "period": "Fixture window", "conditions": "Same counting definition"}
        }
      },
      "expected_value": "75",
      "result_unit": "%"
    }
  ]
}
```

Разрешены 1–10 calculations с уникальными CALC-ID, по два именованных операнда. Expected_value — строка plain decimal до 80 символов с точкой, не JSON float. Anchor использует тот же [контракт spans](baseline-numbers.md): индексы Unicode от нуля, end не включён, непересекающиеся число/единица, quote до 500 символов. Numeric input до 80 символов; decimal_separator по умолчанию ".", запятая задаётся явно. Частичные/grouped/exponent/fraction tokens и неподтверждённые citations блокируются. JSON null, duplicate fields/IDs, пустой массив, неизвестные операции/поля и произвольная expression не превращаются в not_applicable.

Нет block — not_applicable; это не доказательство отсутствия расчётов в prose. Комментарии и example fences не исполняются. Команда не извлекает формулы из естественного языка и не проверяет все числовые утверждения документа автоматически.

## Контекст и округление

Metric/population/conditions должны буквально совпадать между двумя входами. Period_relation задаётся явно: same требует одинаковых period labels, distinct — разных. Ratio/share допускают только same; points/change допускают оба явно объявленных отношения. Labels — авторские утверждения: их совпадение не доказывает одинаковую когорту, реальную последовательность дат, корректный знаменатель или сопоставимость методик. Человек проверяет это по материалу; контекстные поля не заменяют provenance.

Арифметика выполняется точно через Decimal literals → rational fractions, без binary float и скрытого допуска. Packet показывает exact_result и checked_result как numerator/denominator. Для 1/3 ожидаемое "0.33" не совпадает без явно указанного округления:

```json
"rounding": {"decimal_places": 2, "mode": "half_even"}
```

Допускаются 0–12 знаков, только half_even; например 0.125 → 0.12, 0.375 → 0.38, симметрично для отрицательных значений. Не выбирайте separator/rounding/операцию ради нужного ответа. Правила округления и применимость результата оценивает человек.

## Evidence и gates

Оба входа требуют current active factual claim proof и точную recorded source/locator/quote. Stale revision, withdrawn source/claim, unbound legacy record, иной locator/quote и corrupt source hash не дают arithmetic_match. Даже математически правильный расчёт не становится действующим основанием без current evidence.

Если calculation block присутствует, [semantic validation review](semantic-review.md) включает эту проверку и не принимает accepted assessment с blockers. Изменение block входит в authored content binding и требует нового review. Existing completed gate UUID replay сохраняет историю; он не проверяет новую версию плана и не продвигает её автоматически. Новый bundle/schema/state format не вводится; v1–v7 historical reconstruction сохранена.

Arithmetic_matches подтверждает лишь поддержанную формулу над выбранными текущими литералами с заявленными единицами/labels. Semantic/numeric alignment, context_truth, observed_effect, publication/experiment/workflow approval остаются false. Выбор метрики, единиц как понятий, масштаба, популяции, знаменателя и причинная интерпретация эффекта требуют отдельного human review. Packet ограничен 256000 UTF-8 байт, без усечения; остальные file/source/journal limits сохраняются. Это расширение не закрывает новый разрешённый кейс, live R1/M8 или независимую M6.
