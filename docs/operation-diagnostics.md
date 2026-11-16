# P6a: read-only диагностика исторических операций

Срез от 16.11.2026: task/result/review субагентного журнала и hook-run файлового кейса. Host observations/reviews/config сохраняют прежние команды show/pending/audit; общий диагностический endpoint их пока не объединяет. Собственный agent loop, модель, dispatch и новый формат хранения не добавлены.

```text
psa diagnostics operation case UUID --kind result --projects-dir PATH
```

Kind: task, result, review, hook. Для task UUID означает task_id, для остальных — operation_id. FastMCP: `psa_diagnose_operation(project_id, operation_id, kind, projects_dir="projects")`; readOnlyHint=true, destructiveHint=false. Instructions root не требуется.

Оба интерфейса используют общий service/reader. Существующие store decoders проверяют schema/hash/identity и parent binding; чтение выполняется под прежним case lock. Исходные material/role files не перечитываются: проверяются сохранённые journal records, которые сами могут содержать captured text. В ответ текст не попадает. Lock housekeeping допускается как у прежних read-only команд.

## Что означает ответ

Версионированный packet psa-operation-diagnostic-v1 содержит package_version, project/kind/UUID, storage_schema_version, record/parent/completion hashes, captured snapshot и записанные timestamps. Поля actor/goal/request/reason/findings/issues/role instructions и пути к материалам не возвращаются.

| Publication | Значение |
|---|---|
| not_found | В выбранном доступном журнале нет этого UUID; это не результат failed |
| published | Опубликован task/result/review |
| prepared | Валидный pending task/result/review; запись ещё не опубликована |
| execution_unknown | Hook request есть, completion отсутствует; состояние процесса неизвестно |
| result_prepared | Валидный pending hook completion ещё не опубликован |
| completion_recorded | Hook completion опубликован |

Publication отдельно от recorded_outcome: prepared result может содержать captured completed/failed/cancelled/budget_exceeded, но не считается committed результатом. Subagent outcome имеет provenance=self_reported. Hook сохраняет исходные passed/blocked/failed/skipped, provenance=recorded_hook_result и completion_kind attempted/interrupted; сообщения issues не анализируются для выдумывания timeout/cancel статуса. Review показывает только verdict, ready_for_followup не становится human acceptance.

Captured snapshot исторический. Freshness всегда not_checked; проверка не оценивает актуальный evidence/profile, текущую стадию/версию кейса и разрешение нового действия. Recorded_at — timestamp сохранённой записи/completion, а не время исполнения. У hook без completion timestamp отсутствует, mtime файла не используется.

## Usage и стоимость

Каждая метрика содержит value, unit, basis, provenance, verified. Существующий SubagentResult хранит input/output tokens, duration_ms и cost/currency без доказанного метода измерения. Поэтому ненулевые и нулевые значения показываются с provenance=self_reported, basis=unknown, verified=false. Из этих записей нельзя честно вывести measured или estimated. Например явный cost="0" с unit=USD сохраняется; отсутствующая стоимость остаётся null с unit=null. Hooks/tasks/reviews без usage получают null, не нулевые расходы/длительность.

Срок timeout и разница timestamps не превращаются в elapsed execution time. Записанный budget_exceeded не означает, что IDE действительно обеспечила лимит. Новых budget/cost разрешений и платных действий diagnostics не предоставляет.

## Отказы и продолжение

Corrupt/partial journal, неизвестный namespace, conflicting final+pending выбранного operation и invalid parent binding дают ошибку без частичного результата. Неизвестная версия не считается not_found. При busy lock или pending canonical workflow применяется прежний отказ; diagnostics не обходит его и не объявляет процесс running.

Чтение не финализирует pending bytes, не делает recovery, не пересоздаёт handoff и не повторяет checks. Для явного продолжения сохраняются существующие subagent/hook pending/recover команды с их ограничениями. Метаданные execution_started_by_diagnostic/recovery_performed/workflow_approval_granted/native_activation_allowed всегда false. Это не автоматическая рекомендация разрешить recovery/gate.

Тесты сравнивают bytes кейса, сохраняют явные нули/unknown, проверяют prepared/conflict/interrupted состояния, отсутствие private canaries, историческое чтение после изменения материала/недоступности role guidance и реальную CLI/FastMCP parity. Это локальная механическая проверка, не native IDE или независимая оценка пользы.

P6a завершает первый ограниченный срез P6. Далее P6b — сводки состояния и безопасные подсказки продолжения; более широкая provenance/usage telemetry, native cancel/resume и host coverage остаются отдельными задачами. P4/R1/M6/M8 и host-зависимые границы P5 остаются открытыми.
