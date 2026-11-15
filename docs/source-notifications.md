# P3c: уведомление о пересмотрах источников

Явный локальный `source_revision` hook использует существующий [revisit](../src/product_strategy_agent/revisit.py) и [bounded run/journal P3b](hook-runs.md). Он сообщает о необходимых человеческих пересмотрах после **уже committed** импорта, не выполняя импорт или review. Автоматический запуск при импорте, native host activation и внешние сообщения не включены.

## Команды

После штатного обновления источника подготовьте request с новым UUID; сохраните stdout вне каталога кейса:

```powershell
psa hook prepare-notification CASE --operation UUID --projects-dir projects
psa hook run --request PATH_OUTSIDE_CASE/notification.json --timeout 30 --projects-dir projects
psa revisit list CASE --projects-dir projects
```

Prepare read-only и связывает source_revision request с текущим project/version/hash state/events/input snapshot. Этот snapshot покрывает все текущие пересмотры кейса, не один произвольно указанный event ID. Повторное уведомление после изменения источника или human review требует нового request/UUID. Source URI/title/текст и registry statuses остаются данными; они не добавляют разрешений или команд.

Выполнение использует прежний fixed worker с timeout/watchdog, case locks и immutable journal. Отдельные port/service/reader строят только counts из существующего build_revisit_report: все revisions, ожидающие human review revisions и уникальные затронутые claims/decisions среди ожидающих. В hook output не попадают raw titles/URIs, тексты источников и произвольные diagnostics. Полные IDs/детали доступны через psa revisit list. Claims/решения не меняются, review не записывается.

## Значение результата

| Состояние | HookResult | Новый current run | Дальнейшее действие |
|---|---|---|---|
| Есть pending revisions | blocked + counts/revisit hint | notification_delivered=true, CLI0 | Человек оценивает затронутую работу; уведомление не снимает blockers |
| Revisions есть, все reviewed | passed | notification_delivered=true, CLI0 | Это отсутствие pending revisions, не согласование стратегии |
| Только initial import, revisions нет | skipped | notification_delivered=false, CLI1 | Исходный импорт не считается изменением прежнего источника |
| Check/worker недоступен или timeout | failed | notification_delivered=false, CLI1 | Импорт остаётся committed; inspect/pending/recover, без скрытого retry |
| Snapshot изменился | blocked/error | delivery=false либо ошибка до запуска, CLI1 | Подготовить новый request |
| Повтор завершённого UUID / recovery | Прежний receipt либо interrupted failure | historical=true, delivery=false | Нового уведомления не было; использовать новый UUID для запуска |

**required_check_passed всегда false для source_revision**, даже при passed и завершённых human reviews. Domain helper required_hook_allows также отвергает source notifications как required checks. Успешная доставка с blocked означает, что обнаруженная необходимость revisit показана пользователю, а не устранена. Workflow approval всегда false.

CLI run код 0 обозначает доставку нового current уведомления; code1 historical replay намеренно не объявляет доставку заново. Show/recover code0 подтверждает только успешность инспекции/восстановления. MCP caller проверяет notification_delivered и diagnostics отдельно от transport success. Historical receipt/hash/timestamp не переписывается, freshness пересчитывается.

## Failure policy и границы

Source import и notice — разные явные операции. Service уведомления не вызывает SourceImportService, resolve_source_revision, approve_stage и не имеет rollback импорта. Ошибка/timeout/partial publication не удаляет источники, не откатывает state/events и не превращает pending review в reviewed. Для фактического human review используются существующие команды с явным человеком/основанием и действующими правилами; разрешение не выводится из notice.

Intent/result journal, limits, historical replay и recovery сохраняют [P3b протокол](hook-runs.md). Captured notification из копии кейса может быть опубликован только как historical artifact без delivery/required pass; незахваченный outcome становится interrupted failure. Старые before-gate request/completion schemas и их hashes не изменены; новый delivery flag находится только в response wrapper.

FastMCP: `psa_prepare_source_notification(project_id, operation_id, projects_dir)` read-only, затем существующий `psa_run_hook(request, timeout_seconds, projects_dir)`. Инспекция — psa_hook_run/pending, восстановление — psa_recover_hook_run. CLI/настоящий stdio, initial-vs-revision, human-review isolation, failure и copy/recovery проверяются на временных синтетических fixtures, без внешних моделей и сообщений.

[P3d release checks](release-hooks.md) реализован отдельно без публикации. Локальные механизмы P3 готовы; далее P4 host adapters/fallback. Native activation/host acceptance относятся к P4; R1/M6/M8 открыты. Автоматический event dispatcher при импорте и native hooks не заявляются реализованными.
