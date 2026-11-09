# Смена режима через файловый journal

R2: `quick_scan`, `decision_grade` и `deep_research` меняют глубину исследования. Смена режима не утверждает этап, стратегию или публикацию и не создаёт запись gate approval.

```bash
psa status CASE
psa mode set CASE quick_scan --by "Владелец решения" \
  --operation 3ab31f02-12c0-43a1-9f22-1f8ef925a379 --expected-workflow-version 0
```

CLI status показывает `Workflow version`, файловый MCP `psa_status` — `workflow_version`. MCP `psa_mode_set` принимает те же `operation_id` и `expected_workflow_version`. UUID выбирается вызывающим; без UUID создаётся новый, поэтому для безопасного retry нужно передавать собственный.

Одинаковая нормализованная команда с прежним UUID возвращает исходный event, даже после следующего gate/изменения режима, не сбрасывая state. Другой request либо gate под занятым mode UUID отклоняется. `--expected-workflow-version` опционален для совместимости, но при передаче проверяется под общим access lock до подготовки.

## Общий state/events протокол

ModeChangeService зависит от ModeWorkflowStore port. Domain command/профили отделены от filesystem adapter и legacy workflow wrapper. CLI/MCP используют один service; чтение, validation, replay и commit происходят в одном case access scope.

Новый request имеет `kind=mode_change`. Он сохраняется в том же [workflow bundle](workflow-recovery.md): before/after state/events, event/request, hashes остальных входов, manifest, ACTIVE и COMMITTED. Файловая логика публикации/recovery не дублируется. Kind-specific validator требует изменения только mode/mode_history/updated_at/workflow_version; status/stages/approvals и остальные поля должны оставаться прежними. Новый event ровно один раз добавляется в events и mode_history.

`workflow_version` теперь считает journaled gate, mode и [revision review](revision-review-recovery.md) операции: gate v1 → mode v2 → gate v3. Исторические gate bundles без kind остаются читаемыми и повторяемыми; их request/manifest не переписываются. Старые незажурналированные mode changes задним числом не получают версию, а отсутствие workflow_version по-прежнему означает 0. Старый runtime, не знающий mode_change, применять к новым mode bundles нельзя: использовать обновлённую версию приложения.

Режим уже завершённого проекта и повтор текущего режима новым UUID отклоняются. Exact replay исходной завершённой операции работает раньше этих проверок. Указанное имя/роль — заявление вызывающего, не подтверждённая технической аутентификацией личность.

Если сбор источников уже утверждён, сохраняются minimum_sources и предусмотренное профилем исключение: минимум один источник плюс открытый high-priority gap. Mode не создаёт недостающие источники и не выдаёт утверждение источников заново. Повреждённые записи/невалидный state не исправляются предположениями.

## Сбой и проверки

```bash
psa workflow pending CASE
psa workflow recover CASE --operation UUID
```

Те же `psa_pending_workflow`/`psa_recover_workflow` поддерживают gate и mode. До завершения ACTIVE обычные команды блокируются. Recovery проверяет before/after, kind semantics и inputs; посторонние изменения не перезаписываются. Copy case вместе с journal позволяет продолжить по исходному UUID в другом projects-dir. Восстановление mode не продвигает этап и не добавляет approval.

Пределы общего journal сохранены: 512000 байт на payload file, 2000 входных файлов. Capture source/gap JSONL также ограничен 512000 байтами на файл. Это не глобальная версия/транзакция всех реестров: render и остальные legacy writes ещё требуют переноса. БД, Docker и модель для смены режима не нужны.

Source import/revision creation теперь используют [workflow v2 bundle/recovery](source-import-recovery.md) с captured text/archive targets; общая версия учитывает и эти операции.
