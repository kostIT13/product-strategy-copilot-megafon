# Восстановимый source import и revision

R2: `psa source add/fetch` сохраняют registry, extracted text, при необходимости архив прежнего текста, revision event и state через общий workflow journal. Модель, PostgreSQL и Docker не нужны.

```bash
psa status CASE
psa source add CASE ./notes.md --operation f8f301b6-ae82-46a2-a4a5-934eb664b765 \
  --expected-workflow-version 0
psa source fetch CASE https://example.org/page --operation ANOTHER_UUID \
  --expected-workflow-version 1
```

Файловые MCP `psa_add_source`/`psa_fetch_source` принимают `operation_id`/`expected_workflow_version`. SourceImportService зависит от store/reader ports; acquisition/extraction отделены от persistence, построение source plan — pure domain function.

## Идентичность и версии

Caller UUID связывается с нормализованным request: input kind, locator, optional title и expected version. Local locator абсолютен для внешнего файла и относителен для файла внутри case. Web locator — исходный HTTP(S) URL без fragment; final redirect URI сохраняется в source record, определяет source ID и captured result. Source ID и existing registry fields остаются совместимыми с прежним file core.

Exact completed replay возвращает исходный результат **до чтения local input/HTTP**. Он работает и после удаления исходного внешнего файла. Другое содержимое request или другой operation kind под занятым UUID отклоняется. Expected version проверяется до acquisition. Без caller UUID создаётся новый operation ID: это новый осознанный import/fetch, не replay. Redirect outcome/content при replay не переопределяются.

Если процесс остановился до полного сохранения подготовки, факт HTTP acquisition мог не попасть в journal. Приложение не делает скрытого retry: inspect pending, затем явное решение о повторе/новой операции. Неполный bundle не дописывается автоматически. После полного bundle recovery работает только с captured bytes и не читает external source заново.

Все новые source операции увеличивают shared workflow_version вместе с gate/mode/review. CLI/MCP status показывают версию. Они не утверждают этап, не добавляют approval и не подтверждают истинность материала.

## Source plan и journal v2

Перед обновлением current text должен соответствовать hash/path/URI зарегистрированного источника. Чужой unregistered target, corrupt current/archive, дубли source IDs и нестандартный legacy extracted path не перезаписываются; нужен отдельный осознанный разбор/перенос.

При новом content hash прежние bytes сохраняются в `sources/history/SOURCE_ID/HASH.txt`, добавляется один source_revised event с previous/current hashes и paths. Existing archive допускается только с точными прежними bytes. Current text и registry обновляются согласованно. Same-content import обновляет metadata и пишет source_imported, но не создаёт фиктивную revision. Первый import также пишет source_imported.

Для source операций manifest format_version=2 расширяет прежние семь metadata files:

- source.json — captured URI/title/publisher/timestamp и before absence markers;
- source-result.json — воспроизводимый результат API;
- sources.before.jsonl / sources.after.jsonl;
- text.before.bin / text.after.bin / archive.before.bin.

Targets вычисляются заново из request, source registry и captured bytes; произвольных target paths в manifest нет. Derived source ID/hash paths остаются confined. Semantic validation заново строит record/event/targets, проверяет payload hashes и неизменность stage/mode/approvals. Исторические workflow v1 gate/mode/review bundles остаются читаемыми, не переписываются. Старый runtime без v2 не использовать для новых source bundles.

## Публикация и recovery

Используется тот же [workflow протокол](workflow-recovery.md): полный durable bundle → ACTIVE → temp+replace каждого target → completion receipt → удаление ACTIVE. Новые parent directories создаются с directory sync там, где поддерживается. Обычные participating readers/writers держат общий case lock и не читают промежуточную пару/набор; после process death ACTIVE блокирует работу до явного recovery.

```bash
psa workflow pending CASE
psa workflow recover CASE --operation UUID
```

Те же MCP pending/recover возвращают source result для source операции; для прежних видов по-прежнему возвращается event. Каждый target должен совпадать с captured before или after; отсутствующий before разрешён только для создания нового файла. Unrelated input snapshot проверяется отдельно от target files. Manual edits/changed files/integrity errors не перезаписываются; marker/preparations не удаляются предположениями. Исторический committed recovery не сбрасывает последующие изменения. Copy case с journal восстанавливается в другом projects-dir без original local file или сети.

## Пределы и что остаётся

Raw input и saved UTF-8 extracted text ограничены 10 МиБ каждый; newline входит в saved-text limit. Source blobs имеют отдельный 10-МиБ лимит, поэтому текст больше metadata limit 512000 байт поддерживается. Registry/common metadata ограничены 512000 байтами на файл, input snapshot — 2000 файлами. Journal хранит копии source data: применять ту же дисциплину доступа/секретов, что и к case.

Это recoverable publication участвующих файлов, не защита от raw/manual доступа и не сертификация power loss/NAS. Canonical ledger/usage writers перенесены на workflow v4; затем mapping/import/retire прежней цепочки. Source review/corrections и semantic quality не заменяются успешным импортом или точным совпадением хэша.

Render и adoption integrity manifest теперь используют [workflow v3 recovery](render-recovery.md); Markdown builder отделён от публикации, existing drafts сохраняются.

Canonical ledger/usage append теперь поддерживает [workflow v4 replay/recovery](ledger-recovery.md); shared version учитывает эти записи, usage business ID отделён от journal UUID.
