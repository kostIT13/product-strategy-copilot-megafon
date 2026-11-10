# Восстановимая запись канонических реестров и usage

R2: claims, gaps, options, decision-log, capabilities и usage используют общий workflow journal v4 вместо прямого JSONL append. Typed payloads, pure validation/builders, application service/port и filesystem codec разделены по ответственности. Source registry продолжает использовать специализированный v2 protocol.

```bash
psa status CASE
psa gap add CASE --question "Какое допущение меняет выбор?" \
  --operation c0989be2-6d59-4e65-9503-b63456be0fad --expected-workflow-version 0
psa workflow pending CASE
psa workflow recover CASE --operation UUID
```

Остальные пять canonical add-команд получили те же `--operation UUID` и optional expected version. У usage имя flag другое, поскольку `--operation` уже означает название учитываемой работы: `--journal-operation UUID`. File MCP add tools принимают `operation_id`/`expected_workflow_version`; usage дополнительно различает `operation_id` учтённого вызова и `journal_operation_id` записи.

## Согласованность и replay

Одна операция сохраняет before/after выбранного JSONL, исходные реестры для проверки, record/result, state/events и completion receipt. Shared workflow_version увеличивается на один. Stage, mode, stages/approvals не изменяются; запись человеческого выбора в decision-log не заменяет отдельный workflow gate.

Exact caller UUID возвращает исходный record без второй строки или сброса более поздних данных. Другой payload, target ledger или operation kind под занятым UUID отклоняется. Без caller UUID обычные add-команды создают новую операцию; одинаковый текст с новым UUID сам по себе не является replay. Expected version проверяется до подготовки. CLI пустые списки и MCP None нормализуются одинаково; порядок непустых списков сохраняется, в том числе соответствие source/locator/quote.

Весь capture/validation/commit выполняется под общим case access lock. ACTIVE блокирует обычные команды до explicit recovery. Before/after target и unrelated input hashes проверяются отдельно: посторонние изменения не перезаписываются. Pending/preparation не дописываются предположениями. Copy case с journal переносим в другой projects-dir; исторический committed replay/recovery не восстанавливает вручную удалённые данные поверх текущего кейса.

## Валидация

Сохранены existing file-core правила: тип/confidence claim, известные source/claim references, соответствие числа locators/quotes и quote limit; capability status/основания; role/options; gap priority; обязательный владелец decision. Проверка выбранного option при существующих options перенесена из CLI в pure builder, поэтому действует одинаково в CLI и MCP. Decision owner — заявление вызывающего, не техническая аутентификация и не автоматически выданное разрешение на публикацию.

Typed payloads запрещают лишние поля и неявные преобразования типов. Для telemetry bool/float не принимаются вместо integer counters. Точная проверка цитаты/свежести/истинности материала остаётся в verify/evidence/semantic quality, не объявляется выполненной самим append.

## Usage: два разных ID

```bash
psa usage add CASE --provider PROVIDER --model MODEL --operation research --stage research_plan \
  --operation-id actual-call-001 --journal-operation UUID --expected-workflow-version N
```

`operation-id` — идентификатор учтённого вызова/действия. Он сохраняется в usage record. `journal-operation` — UUID команды записи, изолированный от бизнес-ID. Если указан только business ID, journal UUID детерминированно вычисляется из project ID/business ID, чтобы обычный retry не удваивал расходы. Если journal UUID задан явно, при replay нужно передавать его же. Если оба ID отсутствуют, создаются новые UUID и business ID.

Одинаковый request возвращает прежнюю запись. Изменение измерений под прежним journal UUID вызывает conflict; новый UUID с уже учтённым business ID также отклоняется. Legacy записи без matching journal receipt не «усыновляются»: требуется inspect/осознанный перенос. Новый реально отдельный вызов должен иметь отдельный business ID. Изменение unknown usage на известное требует отдельного correction-контракта, не silent overwrite или второй учёт того же вызова.

Unknown tokens/duration/cost остаются None/unknown. Известная сумма требует measured либо estimated; certainty/currency агрегируются раздельно. Request content не добавляется в usage schema; metadata/notes не должны содержать секреты.

## Workflow format v4 и ограничения

V1–v3 readers/история сохранены. V4 добавляет ledger-inputs.json, ledger-before.json, ledger-after.json и ledger-result.json. Codec заново строит record/target/event из typed request и captured inputs, проверяет ровно один append и fixed target allowlist. Произвольные filenames, скрытое изменение state/stage или дополнительная строка при совпадающих пересчитанных file hashes не принимаются. Алгоритмы pure builders v1 — часть historical format, сохранять их для старых bundles.

Target/common metadata и encoded before/after/result ограничены 512000 байтами; ledger-inputs snapshot — 4 МиБ. JSON escaping входит в payload limit. Превышение отклоняется без усечения и публикации. Raw/manual доступ обходит lock; power loss/NAS не сертифицированы. R2 ещё требует инвентаризации/переноса нужных legacy функций/данных и retire SQL/container цепочки; derived critic pack и полнота semantic corrections остаются отдельными задачами.


R3: новые supporting links проверяют effective active claims по [lifecycle projection](claim-withdrawal.md); inactive evidence и затронутые selected/rejected options не принимаются новым decision append. Frozen v4 reconstruction и historical UUID replay не менялись.
