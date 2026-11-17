# P6d: policy механизмов retry/cancel/resume

Срез от17.11.2026 использует [P6a](operation-diagnostics.md) для одного task/result/review/hook UUID. Это read-only описание механизмов CLI и условий отдельного действия, не executor, ACL или токен разрешения.

```text
psa diagnostics controls case UUID --kind task --projects-dir PATH
```

FastMCP: `psa_operation_controls(project_id, operation_id, kind, projects_dir="projects")`, readOnlyHint=true/destructiveHint=false. Scope cli_journal_controls_only: именованная IDE/версия/установленные процессы не проверяются. Native_host_controls=not_verified, native_host_assessed=false; это не заявление, что конкретный host не умеет cancel/resume.

## Механизм отдельно от полномочий

| Control | Что означает policy |
|---|---|
| inspect | Чтение исторических metadata |
| resume_case_context | Реальная команда psa resume читает сохранённый case status; валидность state/lock проверяет сама команда |
| recover_publication | Для валидного pending требуется явная инструкция и подтверждение отсутствия active writer |
| same_uuid_replay | Exact request возвращает исторический receipt без исполнения; pending требует разбор/recovery |
| new_attempt | Консервативный путь через новый request/UUID и свежие основания; pending сначала разобрать |
| resume_execution | Не поддержан CLI: нет собственного agent checkpoint executor |
| cancel_execution | Не поддержан CLI: нет generic process cancel endpoint |

Owned_hook_timeout описывает только существующий fixed worker deadline, не право отменить произвольный PID/IDE/model run. Self-reported cancelled, budget_exceeded или stored passed не подтверждают возможность управления процессом. Указание человека и host capability не принимаются из полей source/result.

Availability не равна authorization: authorization_evaluated/granted=false, actions_executed/workflow_approval_granted/native_activation_allowed=false. Policy_is_write_enforcement=false: новая проекция не заменяет прежние validations/human gates и не накладывает скрытых side effects. При наличии уже данной явной инструкции не нужно повторно запрашивать её только из-за этого отчёта; policy не умеет читать разрешения из чата.

## Recovery и новая попытка

Pending task/result/review → publish_captured_artifact. Hook request без completion → record_interrupted_without_execution, если исход всё ещё неизвестен; pending hook completion → publish_captured_completion. Это точные различия существующего forward recovery. Corrupt/unsupported/conflicting записи не дают policy целиком, а не превращаются в разрешение ремонта.

Проверь pending и отсутствие active writer до отдельного recover; policy сама этого не подтверждает. Existing service снова проверяет свои guards при действии. Diagnostic_binding содержит phase/record/completion hashes и freshness=not_checked, но не является CAS token или новым current preflight. После изменений перечитай состояние.

Опубликованный UUID не переисполняется. Safe new-attempt policy предлагает новый task UUID, для нового result attempt — новый task/result UUID, для пересмотра isolated review — новый review operation UUID, для hook check — новый current HookRequest UUID. Это advisory маршрут, не изменение существующих writer contracts. Review ready требует current snapshot, но не становится human semantic assessment. Reported budget_exceeded требует разбора заявленного превышения и бюджета, не автоматического увеличения лимита/оплаты.

При not_found recovery/replay/new-attempt выбранной истории not_applicable: проверь kind/UUID перед отдельным новым request. При busy/canonical pending действуют прежние отказы; metadata не объявляют процесс running или stopped. Никакой поиск/kill PID, публикация pending, чтение role/source файлов для freshness или запуск checks/модели не выполняется endpoint-ом.

## Сверка P6 и следующий этап

| Локальный срез | Реализовано | Осталось |
|---|---|---|
| P6a | Text-free historical operation metadata/outcomes | Не fresh approval и не текущий статус процесса |
| P6b | Bounded selection summary, shared lock, advisory guidance | Не полная сводка кейса и не action executor |
| P6c | Source/row-bound usage declarations, unknown/zero сохранены | Нет independent provider/IDE measurement evidence |
| P6d | Advisory CLI control capability policy и explicit recovery distinction | Native cancel/checkpoint resume, verified host controls и enforcement не подтверждены |

Локальные срезы P6a–P6d выполнены, весь P6/production readiness не закрыт. Native и host-зависимые части P4/P5/P6 и R1/M6/M8 остаются открытыми. Следующий независимый P7a — инвентаризация research/knowledge/retrieval инструментов и baseline/eval protocol перед расширениями. RAG/new provider не добавлять без измеримого выигрыша; основной последовательный путь сохраняется.
