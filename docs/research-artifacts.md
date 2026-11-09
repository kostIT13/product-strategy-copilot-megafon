# R2: структурированный план исследования и файловый журнал

IDE-агент или человек может сохранить `research_plan` как типизированный черновик без собственного API run, БД или модели. JSON артефакта, читаемый Markdown, событие, квитанция и снимок хэшей входов фиксируются одной видимой версией. Это следующий срез R2 после atomic workspace init, не завершённая миграция всех файловых writers.

## Использование

```powershell
psa artifact status CASE
psa artifact record CASE --input research-plan.json
psa artifact show CASE
psa artifact show CASE --operation OPERATION_UUID
psa artifact pending CASE
psa artifact recover CASE --operation OPERATION_UUID
```

Везде доступен `--projects-dir CASES_PARENT`. Status и show только читают; status не создаёт пустой журнал. Возьми текущие `version` и `case_hash` из status, а новый UUID создай для одной осознанной операции. Пример JSON с placeholders (заменить UUID/hash, версия — из status):

```json
{
  "operation_id": "OPERATION_UUID",
  "expected_version": 0,
  "expected_case_hash": "CASE_HASH_FROM_STATUS",
  "kind": "research_plan",
  "author": "IDE agent",
  "content": {
    "decision_question": "Какое исследование может изменить выбор пилота?",
    "objectives": ["Проверить наиболее важное неизвестное"],
    "constraints": ["Только открытые и собственные материалы команды"],
    "questions": [{
      "question": "Кто регулярно решает эту задачу?",
      "decision_impact": "Выбор целевого сегмента",
      "method": "Изучить разрешённые материалы и сопоставить ограничения",
      "permitted_source": "Перечислить доступные материалы команды",
      "sufficiency": "Показать опору и явно оставшиеся неизвестные"
    }],
    "open_questions": ["Каких данных пока нет?"]
  }
}
```

Author — заявленная метка, не проверенная личность. Запись не выдаёт согласие человека. Content — план будущего исследования, не регистрация проверенного факта или выполнения эксперимента. Дополнительные поля вроде publication_approved/confirmed не принимаются. Enum kind пока поддерживает только research_plan; размер строк/списков ограничен схемой, CLI input — 128000 байт.

## Канон и commit point

```text
CASE/.psa/artifacts/
├── HEAD.json
└── operations/OPERATION_UUID_HEX/
    ├── request.json
    ├── artifact.json
    ├── artifact.md
    ├── event.json
    ├── receipt.json
    ├── base-snapshot.json
    └── manifest.json
```

Canonical draft — artifact.json выбранной committed операции. Markdown — безопасное отступленное JSON-представление тех же данных, а не второй редактируемый канон. Request фиксирует нормализованный typed input; receipt — request hash, версию, время и scope; event — событие записи черновика; base-snapshot — хэши рассмотренных входных файлов. Manifest связывает все шесть файлов и предыдущий HEAD.

Под общей OS project lock запись сверяет expected_version и case_hash, подготавливает полный bundle, выполняет flush/fsync и проверку содержимого. Затем единственная atomic замена HEAD.json делает всю операцию видимой. Читатель захватывает один HEAD и проверяет immutable chain; незавершённая папка не становится артефактом только из-за наличия request.json. Genesis version=0 также публикуется целым каталогом; отсутствие HEAD внутри существующего журнала — ошибка, не сигнал «начать заново с нуля».

`expected_version` относится **к artifact journal**, не ко всем старым writers проекта. В status явно указаны version_scope=artifact_journal и legacy_writers_transactional=false. Два новых writer с одной версией не могут оба записаться: второй получает busy/version conflict. Повтор идентичной нормализованной команды с тем же operation UUID возвращает исходную квитанцию, даже если появились позднейшие версии. Другие данные под занятым UUID отклоняются. Порядок ключей JSON не имеет значения; порядок исследовательских вопросов является частью content.

## Входной снимок и совместимость

Case hash связывает state.json, восемь текущих JSONL-реестров, 01_brief.md, 02_research-plan.md и три известных strategy/validation author drafts (отсутствующий draft отражён как null). Это хэши входных файлов, не копии полного исследовательского корпуса и не проверка истинности/цитат. Обычная проверка verify/evidence остаётся отдельной задачей.

Перед записью/recovery хэш входов проверяется повторно; изменённый вход требует нового осознанного запроса. Show возвращает исходный base_snapshot, base_inputs_changed и changed_input_files. При этом исторический exact replay не переиздаёт approval и не обновляет старый snapshot.

Source/claim/gate/render и остальные публичные файловые операции теперь используют [общий access lock](case-access.md). В пределах participating core/store scope case snapshot не пересекается с другим writer; при живом writer status/show/pending получают busy. После освобождения lock входы могут измениться, и show пометит исторический draft как основанный на изменённых входах. Ручные/сторонние правки не участвуют в lock, а большинство legacy writers ещё без journal/recovery: глобальная crash-atomic транзакция всех реестров не заявляется.

Запись draft не переписывает 02_research-plan.md или state.json и не переводит этап. Если committed structured план существует, research_plan gate использует его как единственный план для этого утверждения; содержимое legacy Markdown не может заменить его или обойти проверку. Для кейсов без committed structured плана сохраняется прежняя проверка 02_research-plan.md. Автоматической двусторонней синхронизации нет.

## Явное утверждение structured плана

После просмотра `psa artifact show ID` человек явно разрешает переход по конкретному draft. Передайте UUID и version из receipt:

```bash
psa gate approve ID --stage research_plan --by "Владелец решения" \
  --artifact-operation UUID --artifact-version 1 --reason "План рассмотрен"
```

Файловый MCP `psa_approve_stage` принимает те же `artifact_operation` и `artifact_version`. Сам draft, его author, critic и наличие содержательного legacy Markdown не считаются согласием человека. `approved_by` — указанное вызывающим имя/роль, а не подтверждённая технической аутентификацией личность.

Gate требует оба селектора, текущую committed HEAD-версию и неизменённые base inputs. Старый UUID, новая версия под другим UUID, повреждённый journal, изменённый brief/state/реестр/draft блокируют переход. Требуется записать и рассмотреть свежий draft; автоматической подстановки последней версии нет. Селекторы для других этапов отклоняются. Кейсы с существующим, но повреждённым journal не переключаются на Markdown fallback.

В approval state/history и events записывается `research_plan_artifact`: kind, operation_id, version, manifest_hash и base_case_hash. Markdown не проецируется обратно в авторский файл. Утверждение меняет state/events, поэтому исторический draft затем показывает изменённые base inputs; это сравнение с исходным снимком, а не автоматический отзыв уже записанного approval. Более поздняя draft-версия сама не заменяет ссылку в историческом approval.

Gate держит общий OS project lock от проверки версии до конца записи; participating artifact/legacy writers не могут вклиниться в этот интервал. State/events публикуются через [write-ahead bundle и явный recovery](workflow-recovery.md), с before/after hashes, ACTIVE guard и completion receipt. Для exact replay gate можно передать собственный operation UUID; это другой ID, чем выбранный artifact UUID. Ручные/сторонние правки обходят lock. Не считать эту интеграцию глобальной crash-atomic транзакцией всех реестров.

## Сбой и recovery

Pending показывает операции вне reachable committed chain и целостность подготовки. preparation_valid=true не означает разрешение применить её поверх изменённого HEAD/кейса. Recovery требует точный UUID, повторную проверку всей подготовки, того же predecessor и case hash, затем выполняет atomic commit. Record той же команды также может завершить полностью подготовленную операцию. Неполную/изменённую операцию не дописывать пустыми данными и не удалять автоматически.

Если сбой произошёл после commit, record/recover возвращают прежний receipt без новой версии. Частичный HEAD temporary file игнорируется: читатели используют только HEAD.json. Если committed HEAD или его chain повреждены/удалены, команды завершаются ошибкой и не угадывают старую версию; требуется отдельное восстановление из доверенной копии. Hash — контроль целостности, не подпись/защита от администратора, который переписывает весь журнал. В v1 поддерживается до 1000 committed операций на кейс: новые версии сверх лимита отклоняются до записи, история/replay остаются читаемыми. Автоматическое обрезание/compaction не реализованы. Journal files читаются с лимитом 512000 байт; превышение не обходится чтением усечённого JSON.

Служебная genesis preparation под projects/.psa-staging/ не содержит пользовательского draft; при сбое до её публикации исходный input остаётся у вызывающего, явный retry безопасен. Orphan preparations не очищаются автоматически. Гарантии относятся к локальной FS и участвующим writers; как и у init, физический power loss/NAS не объявляются сертифицированными. Копия каталога кейса сохраняет историю и исходные IDs/hashes.

## MCP и проверка

Файловый `psa-mcp` получил пять tools: psa_artifact_status, psa_record_research_artifact, psa_show_research_artifact, psa_pending_research_artifacts, psa_recover_research_artifact. CLI и MCP вызывают один ResearchArtifactService/FileResearchArtifactStore. Только record/recover имеют write hint, оба идемпотентны при том же input; внешний вызов/публикация отсутствуют. Старый PG `psa-main-mcp` этим срезом не расширяется.

Автотесты проверяют subprocess kill во время подготовки, до/после HEAD и после записи HEAD temp; конкурентные версии, replay/collision, corruption, stale case/preparation, перенос каталога и CLI/настоящий stdio MCP. Это автоматизированный транспортный тест, не отложенная live IDE-приёмка R1/M8. Модель/БД/Docker не используются.
