# План измерения: typed contract R3

`psa validation check CASE` и MCP `psa_check_validation_plan` читают authored `drafts/validation-plan.md`. Внутри Markdown нужен ровно один fenced JSON block с language `psa-validation-v1`. Остальная prose поясняет план; schema block — единый structured author input, не дополнительный редактируемый generated ledger. Frozen renderer сохраняет Markdown целиком в `06_validation-plan.md`; отдельная JSON-копия не создаётся.

Пример **неизмеренной гипотезы**, не результат исследования:

````markdown
# План проверки

[HYPOTHESIS] Проверим направление изменения; эффект пока не измерен.

```psa-validation-v1
{
  "schema_version": 1,
  "hypothesis": "Изменение может снизить время выполнения задачи.",
  "expected_change": "Предполагаем снижение времени; величина ещё неизвестна.",
  "metric": {
    "name": "Время выполнения",
    "definition": "Медиана длительности от начала до успешного окончания задачи.",
    "unit": "s",
    "population": "Разрешённый пилотный сегмент; критерии включения заданы командой.",
    "data_source": "Разрешённый журнал пилотных событий."
  },
  "baseline": {
    "status": "unknown",
    "value": null,
    "reason": "Базовый период ещё не измерен.",
    "measurement": {
      "method": "Измерить ту же метрику в неизменённом процессе до пилота.",
      "owner": "Аналитик пилота",
      "due_at": "2027-01-15T12:00:00Z"
    }
  },
  "comparison": "Сравнение с неизменённым процессом при одинаковых критериях сегмента.",
  "success_criterion": "Меньшее время без нарушения защитных метрик; точный порог согласовать до начала.",
  "observation": {
    "start_condition": "После получения baseline, согласования порога и разрешения пилота.",
    "duration_days": 14
  },
  "guardrails": [{
    "name": "Ошибки выполнения",
    "definition": "Доля неуспешных задач среди всех начатых.",
    "data_source": "Тот же разрешённый журнал событий.",
    "stop_rule": "Остановить пилот при превышении заранее согласованного порога ошибок.",
    "owner": "Ответственный за пилот"
  }],
  "owner": "Ответственный за анализ",
  "decision_rule": "При нарушении guardrail остановиться; иначе представить результат и неопределённость человеку."
}
```
````

Даты и параметры в примере иллюстративны. Schema проверяет явность полей, а не достаточность порога, длительности, выборки или контроля. Человеку нужно определить измеримые пороги и проверить сроки до запуска.

## Baseline

- `unknown`: обязательно `value: null`, reason и measurement method/owner/timezone-aware due_at. Ноль не подставляется. Check не гарантирует, что deadline ещё не истёк или измерение уже выполнено.
- `reported`: обязательно конечное JSON number `value` и `claim_id`, например `{"status":"reported","value":75,"claim_id":"C-001"}`. Проверяются active factual claim, отсутствие superseding record, точные цитаты/locators, current source hashes/revision events и immutable v4 claim binding. Missing/legacy/stale proof блокирует reported baseline; corrupt files дают ошибку без частичного complete.

Proof означает актуальность ссылки/выдержки. Он не доказывает, что число, единицы, период и population в schema действительно следуют из claim: `numeric_alignment_verified` и `semantic_alignment_verified` остаются false. Packet показывает evidence для человеческой сверки. Reported не переименовывается автоматически в измеренный самим агентом результат.

## Проверки и ограничения

Все поля схемы обязательны, лишние запрещены. Текст непустой, до 2000 символов; unit/owner могут быть короткими (`%`, `PM`). Version — integer 1, bool не принимается. Duration — integer 1–3650 дней, bool/строки/ноль отклоняются. Guardrails: 1–5 с различными именами и явными definition/data source/stop rule/owner. Наивные даты, non-finite numbers, duplicate JSON fields, несколько blocks, comments/code examples вместо настоящего block и незавершённая разметка отклоняются.

Store читает state/draft под общим lock/ACTIVE guard, confined paths, максимум 512000 bytes на файл. Reported proof использует существующие bounded evidence limits; packet ограничен 128000 bytes. Нет model/network calls, исполнения эксперимента, записи источников или approvals. CLI: exit 0 complete, exit 3 incomplete; ошибки доступа/коррупции завершают команду ошибкой.

Report содержит schema plan, baseline proof, input hashes и review_hash. Numeric/semantic alignment, observed_effect_verified, publication_approved и workflow_approval_granted false; требуется human review. Дополнительная narrative prose может противоречить block: автоматическое разрешение такого противоречия не заявляется.

## Gates и совместимость

Новые validation approvals требуют complete plan вместе с прежними coverage/promise/strategy structure/generated integrity checks. Явный human gate сохраняет validation_plan review_hash/status/version в audit. Это не разрешение исполнения эксперимента или публикации. Historical completed UUID replay возвращает прежний event без нового согласия.

Схема кейса, workflow journal и frozen render v1/templates не менялись. Старые narrative-only планы читаются/рендерятся, но для **нового** validation gate требуют authored block. Legacy demo replay не переутверждает gates и остаётся работоспособным. Исправлять generated Markdown/state вручную не нужно; меняется authored draft и запускается render.

R3 остаётся открытым: semantic consistency, согласование численных критериев и baseline с evidence, human decisions и correction/withdrawal lifecycle ещё требуют следующих срезов. Наличие complete schema не означает готовность к production или победу в хакатоне.
