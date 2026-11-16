# P6b: сводки выбранных операций и подсказки продолжения

Срез от 16.11.2026 поверх [P6a operation diagnostics](operation-diagnostics.md). Сводка относится к явно выбранным ID одного кейса, не ко всему проекту или всем задачам.

```text
psa diagnostics summary --request summary.json --projects-dir PATH
```

```json
{
  "schema_version": 1,
  "project_id": "case",
  "operations": [
    {"kind": "task", "operation_id": "00000000-0000-0000-0000-000000000001"},
    {"kind": "result", "operation_id": "00000000-0000-0000-0000-000000000002"}
  ]
}
```

Это пример формата, не реальные ID. FastMCP: `psa_summarize_operations(request, projects_dir="projects")`, readOnlyHint=true/destructiveHint=false. Request ≤16384 bytes, 1–32 selections; пары kind/UUID уникальны. Kind: task/result/review/hook, для task используется task_id. Неизвестные поля, включая command/approved_by, запрещены. Порядок выбора сохраняется.

## Что суммируется

Packet psa-operation-summary-v1 содержит selection_hash, scope=selected_operations_only, redacted P6a operations, counts и guidance. Batch читает все выбранные записи под одним participating case lock. Конкурирующий участвующий reader/writer получает busy; это не защита от внешнего редактора или гарантия filesystem snapshot. Исторические captured snapshots разных записей могут отличаться; freshness остаётся not_checked.

Counts группируют только выбранные записи по kind/publication. Published_outcomes считает записанные outcomes только published/completion_recorded; unpublished_outcomes отдельно показывает captured outcomes pending-записей. Это количество записей, не проверенных запусков. Not_found не является failed; отсутствие result/review в выборке не означает, что их вообще нет. Ready_for_followup и historical passed не становятся разрешением действия/gate.

Usage остаётся per-operation с прежним self_reported/unknown basis. Итоги usage_totals=null, usage_aggregation=not_computed: разные currencies, неизвестные значения, несколько results одного task и неизвестная связь с исполнением не суммируются. Явные нули сохраняются; разница timestamps не объявляется временем работы.

## Подсказки — данные, не команды к выполнению

Каждая guidance-запись содержит фиксированный code, prerequisites и inspection.cli_argv. Единственные templates — `psa status ID`, `psa subagent pending ID`, `psa hook pending ID`. Они read-only и не содержат actor/reason/material text, shell fragments, путей или подставленных команд. Scope_argument указывает добавить собственный `--projects-dir PATH` как отдельные argv; строки не предназначены для shell eval.

| Наблюдение | Подсказка и условия отдельного продолжения |
|---|---|
| ID отсутствует | Проверить kind/UUID; не создавать запись автоматически |
| Pending или execution_unknown | Посмотреть pending, подтвердить отсутствие активного writer; recovery требует отдельного явного указания |
| Task опубликован | Проверить текущий snapshot; dispatch требует отдельного указания |
| Completed result | Оценить записанный результат и freshness перед followup |
| Failed/cancelled/budget_exceeded result | Разобрать исторический outcome, а при budget_exceeded — бюджет; новая попытка требует нового явного решения |
| Review ready_for_followup | Проверить freshness; verdict не является human semantic approval |
| Hook completion | Historical passed не действует для нового действия; нужен fresh preflight и явное действие |

Prerequisites не считаются автоматически выполненными. Authorization_granted/autorun_allowed=false, guidance_only=true, actions_executed/mutation_authorized/workflow_approval_granted/native_activation_allowed=false. Сводка не публикует pending, не повторяет checks/модель, не отменяет процессы и не одобряет gates. Настоящие mutating команды требуют своих существующих явных оснований.

## Ошибки и проверка

Corrupt/partial/unsupported/conflicting выбранная запись прерывает весь ответ без частичных counts/JSON. Сохраняются прежние busy/canonical-workflow-pending отказы. Исходные материалы и role files не перечитываются; используются прежние bounded journal decoders. Case bytes не меняются, кроме служебного lock housekeeping вне кейса.

Проверены exact CLI/service/real-stdio parity, pending outcome separation, currencies/zero/unknown preservation, 32/33/empty/duplicate/extra-field/request-byte boundaries, один case lock на batch с конкурирующим потоком, fixed read-only argv и безопасные отказы. Unit tests подтверждают программные границы, не native IDE acceptance.

P6b реализован; весь P6 открыт. [P6c usage provenance](usage-provenance.md) реализован; далее P6d capability-aware retry/cancel/resume policy. Для telemetry: различение measured/estimated/unknown требует реальных оснований, а не повышения self-reported values. Host coverage и native cancel/resume остаются отдельными задачами; P4/P5/R1/M6/M8 не закрыты.
