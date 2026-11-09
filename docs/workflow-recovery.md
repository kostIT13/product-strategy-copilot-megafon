# Восстановление workflow gate

R2: файловый `psa` и `psa-mcp` сохраняют gate approval через write-ahead bundle. Это восстановление двух совместимых корневых файлов, а не новый автономный агент или база данных.

## Запись и повтор

```bash
psa gate approve CASE --stage intake --by "Владелец решения" \
  --operation 387668ad-b29e-45f7-8a6e-a4334a6d26bc --expected-workflow-version 0
```

UUID выбирает вызывающий. Один нормализованный request под тем же UUID возвращает прежний event, даже если кейс уже продвинулся или изменился режим. Другое содержимое запроса под занятым UUID отклоняется. Replay не переписывает state/events и не выдаёт новое согласие. Без `--operation` создаётся новый UUID, поэтому для надёжного retry следует передавать собственный. При аварии UUID можно найти в pending.

`workflow_version` — число завершённых journaled gate и [mode change](file-mode-recovery.md) операций, а не глобальная версия всех реестров. Отсутствующее поле старого кейса означает 0; старые незажурналированные mode changes не пересчитываются. Версию показывают CLI/MCP status. `--expected-workflow-version` опционален для совместимости старых команд; при передаче проверяется под project lock до подготовки. Отдельная `artifact_version` по-прежнему относится к журналу structured drafts. У structured research_plan gate остаются обязательными выбранные artifact operation/version и проверка свежести.

Согласие человека обязательно. Имя/роль в `--by` — заявление вызывающего, не проверенная аутентификацией личность. Recovery завершает только уже подготовленную команду, не выбирает план и не создаёт новое разрешение.

## Write-ahead протокол

Операции лежат в `CASE/.psa/workflow/operations/UUIDhex/`:

- request.json и event.json;
- state.before.json / state.after.json;
- events.before.jsonl / events.after.jsonl;
- inputs.json — SHA-256 остальных файлов кейса, включая source texts, rendered artifacts и structured artifact journal; собственный workflow journal исключён;
- manifest.json с project/operation scope и хэшами всех семи payload files;
- COMMITTED.json — completion receipt с manifest hash после публикации обеих новых версий.

Gate держит общий OS project lock. После проверок stages/содержимого сохраняется полный bundle с flush/fsync, проверяются исходные root files и inputs, затем через temp+replace публикуется `.psa/workflow/ACTIVE.json`. Далее state.json и events.jsonl заменяются полными новыми версиями, completion receipt публикуется через temp+replace, ACTIVE удаляется последним. Directory fsync применяется там, где поддерживается; физический power loss/NAS этим тестированием не сертифицированы.

При наличии ACTIVE файловые CLI/MCP и публичные функции case operations отказываются продолжать работу: status/context, validate/verify/coverage, source/ledger/usage/revisit/render/critic/mode и artifact store. Корневые файлы в этот момент могут быть промежуточной парой. Вручную их не редактировать. Инструменты recovery используют отдельный путь, доступный и при ACTIVE.

## Явное восстановление

```bash
psa workflow pending CASE
psa workflow recover CASE --operation UUID
```

MCP: `psa_pending_workflow` — read-only inspection; `psa_recover_workflow` — явный idempotent recovery с UUID. Оба вызывают WorkflowRecoveryService/FileWorkflowStore. Нет сетевых/модельных вызовов.

Pending показывает незавершённые подготовки и ACTIVE. Полностью подготовленная операция до ACTIVE ещё не меняла root files. Recovery сначала проверяет manifest/payload hashes, scope, before/after semantics, версию, ровно одно добавление event и входной снимок. Для ACTIVE каждый root file должен точно совпадать со своей before либо after версией. До ACTIVE допустима только исходная пара. Нужные замены доводятся до after, повтор не добавляет второй event. После COMMITTED и удаления ACTIVE исторический recovery возвращает исходный event без сброса последующих правок.

Неполная/изменённая подготовка не дописывается предположениями. При изменённых inputs или постороннем содержимом target files recovery отказывает без перезаписи. При повреждении ACTIVE/его bundle команды остаются заблокированы: сохранить копию для отдельного восстановления из доверенных данных. Не удалять marker автоматически и не угадывать исходную версию. Незавершённые bundles/temp files не очищаются автоматически. Подготовка без ACTIVE не блокирует обычные операции, но последующая смена кейса может сделать её неприменимой.

Case folder можно скопировать с journal и продолжить recovery по прежнему UUID в другом projects-dir. Имена файлов не дают права применить bundle к другому project ID. Хэши — контроль целостности, а не подпись против администратора, переписывающего весь journal.

## Ограничения и следующий перенос

Каждый journal file ограничен 512000 байтами; input snapshot — 2000 файлами. Ограничения проверяются до публикации, исходные файлы не усекаются. Payload содержит копии состояния/событий: это данные кейса, к ним применяются те же ограничения доступа и запрет на публикацию секретов.

Публичные файловые readers/writers CLI/MCP/core/store теперь используют [общий access lock](case-access.md): ACTIVE проверяется после получения lock, а весь scope защищён от участвующих writers. При живой операции pending/status и остальные команды получают busy. Прямые обращения к файлам обходят эту границу. Последовательность отдельных вызовов без внешнего access scope не является одним снимком; общая crash-atomic транзакция всех legacy реестров не гарантируется.

Mode change перенесён на тот же bundle/recovery с request kind и отдельной проверкой семантики, исторические gate bundles сохранены. Revisit/source/render и другие прежние многофайловые записи пока не получили write-ahead recovery. Следующий R2-срез — перенос нужных операций на commit/recovery; затем legacy mapping/import, dependencies/entrypoints/CI retire. PostgreSQL/Docker ещё не удалены из старой цепочки. R1 live IDE и M6/M8 остаются отложенными.
