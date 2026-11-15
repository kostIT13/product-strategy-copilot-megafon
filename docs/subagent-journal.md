# P2: журнал заданий, результатов и review

Продолжение [read-only handoff P1](subagent-handoffs.md). `prepare` остаётся stateless. Явный `register` сохраняет пакет; результат и оценка основного агента записываются отдельными неизменяемыми артефактами. Эти команды не запускают модели или native subagents. Последовательный путь сохраняется.

## Команды

Из корня репозитория, для заранее выбранного кейса:

```powershell
psa subagent register CASE --request task.json --by "Основной агент"
psa subagent record-result CASE --request result.json
psa subagent review-result CASE --request review.json
psa subagent task CASE --task TASK_UUID
psa subagent result CASE --operation RESULT_UUID
psa subagent review CASE --operation REVIEW_UUID
psa subagent pending CASE
psa subagent recover CASE --kind result --id RESULT_UUID
```

Все команды поддерживают `--projects-dir PATH` и `--instructions-root REPO`. Task request совпадает с P1 PrepareHandoff: UUID, роль, цель, бюджет и selections. Register возвращает `receipt` и исходный `handoff`. Перед последующим использованием пакета проверяйте `task.freshness`.

Result request содержит `schema_version: 1`, новый `operation_id`, `task_id`, `expected_task_fingerprint` из handoff, `submitted_by` и `result` по [контракту P0](automation-contracts.md). Вложенный результат повторяет точные task UUID/role/target/fingerprint. Refs observations должны ссылаться на переданные input IDs. Проверяются заявленные usage и бюджет; unknown не заменяется нулём. Это проверка отчёта, не измерение или ограничение реального процесса.

Пример review request: UUID и hash заменяются значениями собственных квитанций.

```json
{
  "schema_version": 1,
  "operation_id": "33333333-3333-4333-8333-333333333333",
  "task_id": "11111111-1111-4111-8111-111111111111",
  "result_operation_id": "22222222-2222-4222-8222-222222222222",
  "expected_result_record_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "reviewed_by": "Основной агент",
  "reason": "Основания первого наблюдения проверены; нужен дальнейший разбор.",
  "verdict": "ready_for_followup",
  "finding_indices": [0]
}
```

Допустимы `ready_for_followup`, `changes_requested`, `rejected`. Индексы начинаются с нуля; при двух последних verdict список пуст. Ready требует completed result, существующих индексов и текущего snapshot. Отказ/запрос изменений может документировать устаревший результат. Оценки отдельных операций не агрегируются: `result.assessment = not_aggregated` не означает отсутствие review или действующее разрешение. Конкретная оценка читается по её UUID.

## Доверие, актуальность и replay

Производитель/reviewer — заявленная атрибуция, без проверки личности или запуска. Output остаётся недоверенными данными. Ready не добавляет claim, не исправляет источник, не выбирает вариант и не заменяет человеческий semantic review/gate. Применение предложений требует штатных сервисов и действующих согласований. Квитанции содержат `identity_verified: false`, `execution_verified: false`, `canonical_adoption: false`, `workflow_approval_granted: false`.

Новый результат требует совпадения текущего handoff с зарегистрированным: selected materials, state/events/source registry, версии/hashes инструкций и диапазонов. Инспекция возвращает `current`, `stale` либо `unavailable`, не обновляя запись. При изменении входов создаётся новая задача с новым UUID.

Точный replay завершённого UUID возвращает историческую квитанцию даже после изменения входов. Это не подтверждение сегодняшней актуальности и не повторное исполнение. Несовпадающий request/registrant при том же UUID отклоняется; timestamp не переписывается.

## Хранение и восстановление

Путь внутри кейса: `.psa/workflow/subagents/v1/{tasks,results,reviews}/UUIDHEX.json`. Пространство `.psa/workflow` уже исключено snapshot-протоколом: журнал не меняет оснований прежних human semantic reviews. Copy/backup всего кейса переносит и эти записи. Общий case lock исключает параллельную публикацию. Незавершённая основная workflow operation блокирует работу до её отдельного восстановления.

Операция пишет/fsync `.pending.json`, проверяет envelope/schema/hash/parents и атомарно публикует final. После сбоя pending показывает `prepared` либо `corrupt_or_incomplete`. Только явный recover завершает публикацию точных захваченных bytes. Он не вызывает модель и не принимает результат в канон. Входы могут измениться после подготовки: после recovery проверяйте freshness отдельно. Повторный recover final возвращает прежнюю квитанцию. Незавершённый UUID нельзя перезаписать обычным retry.

Повреждённые/неизвестные файлы сохраняются для разбора, без автоматического удаления/исправления. SHA-256 и schema проверяют целостность протокола, но не защищают от владельца, переписавшего всё хранилище. Проверено прерывание процесса на локальной файловой системе; сохранность при потере питания/NAS отдельно не заявляется.

Лимиты: task request 64 000 bytes, result/review request 128 000, envelope 256 000; до 1000 файлов на канал и 1000 строк pending. По достижении лимита новые записи отклоняются без удаления истории. Диагностика валидации не отражает input values.

## FastMCP и дальнейшая работа

Общие сервисы доступны через `psa_register_subagent`, `psa_record_subagent_result`, `psa_review_subagent_result`, `psa_subagent_task`, `psa_subagent_result`, `psa_subagent_review`, `psa_subagent_pending`, `psa_recover_subagent_record`. Только четыре инспекционных tools помечены read-only; запись/recovery явные и идемпотентные при том же UUID/request. Parity проверена настоящим stdio-клиентом.

Native запуск, фактические timeout/cancel/usage, host permissions и активация не входят в P2. Далее P3 — локальные allowlisted hooks, затем P4 — отдельно проверяемые host adapters. R1/M6/M8 открыты.
