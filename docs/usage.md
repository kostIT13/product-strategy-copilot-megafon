# Учёт времени и расходов

`usage.jsonl` — append-only журнал вызовов провайдера или вручную внесённых оценок. По умолчанию содержимое запроса не записывается.

Добавьте запись, используя только данные, которые действительно доступны:

```powershell
psa usage add demo --provider "qwen_api" --model "Qwen3.8:27B" --operation "claim_extraction" --stage evidence_review --input-tokens 12000 --output-tokens 1800 --duration-ms 42000 --cost-amount 0.42 --currency RUB --cost-certainty estimated --pricing-as-of 2026-11-05 --cost-note "Расчёт по тарифу на дату; usage API отсутствовал"
```

Неизвестные токены, время и стоимость оставляйте пропущенными; они сохраняются как `null`, а не как ноль. Стоимость требует `--cost-certainty measured|estimated`; `measured` означает цифру из usage/billing API, `estimated` — вычисленную. Для расчёта указывайте `--pricing-as-of` и метод в `--cost-note`.

```powershell
psa usage report demo
```

Сводка показывает число записей, суммы сообщённых токенов и времени, пропуски и стоимость отдельно по валюте и достоверности. Измеренные и оценочные суммы не объединяются. CLI не перехватывает автоматически трафик IDE и не извлекает usage из API; оператор вносит данные провайдера вручную.
