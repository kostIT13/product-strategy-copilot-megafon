# Реестр доказательств

Режим исследования: `quick_scan`

## Источники

### S-05AE8CA0C1EC — Synthetic reminder cohort table
- Тип и статус: local_text / extracted
- URI/путь: `C:\Users\Yaroslav\Desktop\mgimo\evals\table-demo\synthetic-reminder-cohorts.csv`
- Владелец: table-demo; надёжность: unassessed
- Дата обращения: 2026-11-05T16:25:57Z

## Утверждения

### C-001 [fact] — уверенность: medium
За четыре недели суммарно учтено по 1000 eligible в каждой группе; renewed составили 750 в control и 770 в reminder, что соответствует 75% и 77%.

Основание: **S-05AE8CA0C1EC** (Synthetic reminder cohort table), locator `lines:1-9`.
> week,arm,eligible,renewed,opted_out,complaints
W1,control,250,188,3,1
W1,reminder,250,193,7,2
W2,control,250,187,4,1
W2,reminder,250,192,8,2
W3,control,250,188,4,1
W3,reminder,250,193,8,2
W4,control,250,187,4,1
W4,reminder,250,192,9,3

Пояснение: Суммы по четырём строкам arm; renewed / eligible. Все значения синтетические.

## Открытые пробелы

- **G-001 [high]** Неизвестны ли правила назначения arm, определения renewed/opted_out и наличие пересекающихся пользователей?
  - Почему важно: Без этого нельзя интерпретировать разницу как эффект напоминания.
  - Как закрыть: Получить схему эксперимента, словарь метрик и данные на уровне назначенных групп.
