# Поиск по файловым источникам

```powershell
psa source search CASE "удержание" --limit 10
```

Команда выводит JSON; файловый MCP `psa_search_sources` принимает те же project_id, query, limit и projects_dir. Нужен импортированный локальный extracted text, а не PostgreSQL, индекс, сеть или модель. CLI/MCP используют один FileSourceSearchService, port snapshot и filesystem adapter; literal matching и построение выдержек находятся в domain.

## Контракт результата

Поиск выполняет буквальное совпадение без учёта регистра (`literal_ignore_case_v1`), а не SQL FTS, regex, stemming или semantic retrieval. Запрос обрезается по краям, содержит слово/число, не содержит control characters и имеет максимум 200 символов. Пробелы внутри запроса значимы; regex-символы ищутся буквально. Title/URI и координаты ячейки не являются поисковым текстом.

Поиск проверяет все зарегистрированные текущие источники под общим case lock, включая источники без совпадений. Проверяются state, уникальность IDs, канонический путь `sources/S-ID.txt`, confinement без symlinks/junctions, UTF-8 и SHA-256. Статус источника должен быть `extracted`. Архивные revisions, исходные binaries и произвольные файлы кейса не обходятся. При ACTIVE workflow или занятом lock действует общий pending/busy contract.

Возвращается согласованный snapshot: project_id, workflow_version, sources_scanned, corpus_bytes, query/method, matched_sections, limit, truncated и hits. Каждый hit содержит source_id, title, uri_or_path, content_hash, locator и точную quote длиной до 500 символов с искомым фрагментом. Порядок стабилен: source_id, затем порядок секций; это не рейтинг достоверности. На секцию возвращается максимум один hit независимо от числа вхождений. `matched_sections` считает все совпавшие секции, `truncated` явно показывает ограничение выдачи. Пустая выдача означает отсутствие буквального совпадения в этом snapshot, а не доказанное отсутствие явления.

| Материал | Область поиска и locator |
| --- | --- |
| TXT/HTML/CSV/JSON/DOCX | Непустая строка извлечённого текста, `paragraph:N` — тот же смысл, что в verify |
| PDF | Текст внутри страницы, `page:N`; последовательность page markers проверяется целиком |
| XLSX | Значение конкретной видимой ячейки, `cell:'Sheet'!A1`; формула остаётся строкой, координата/type label не выдаются за содержание |

Quote/locator можно передать штатной записи claim, затем выполнить `psa verify CASE`. Сам поиск не создаёт claim, не подтверждает истинность, не снимает pending review и не даёт разрешения на gate. Текст источника и найденные инструкции остаются недоверенными данными. Перед использованием результата после изменения кейса сравните актуальный content_hash; поиск не резервирует версию для последующей записи.

## Ограничения и ошибки

- limit: 1–50, default 10; boolean не принимается сервисом за число.
- Максимум 500 источников, 10 MiB на текст, 32 MiB суммарного текста; state и registry ограничены 512 KiB каждый.
- Максимум 50000 секций; неоднозначные PDF markers и дубли XLSX coordinates отклоняются.
- Missing/corrupt/unsupported metadata или текст, несовпадение hash и превышение лимита дают ошибку **без частичного результата**, даже если первые limit совпадений уже найдены.
- Не создаются derived indexes, events, usage или другие файлы внутри кейса. Общий lock использует существующий служебный каталог вне кейса.

Это ограниченный файловый retrieval, не полная parity старого [PG FTS](source-search.md): нет title weighting, word-form search, relevance score, revision UUID или индекса первых 100000 символов. Corpus не обрезается молча. Старые receipts/источники не переписываются. Масштабирование и RAG допустимы только после измеренной необходимости; текущий [retire план](legacy-retirement.md) не требует переносить SQL индекс.


[Source withdrawal](source-withdrawal.md) исключает источник из текущих hits/citation snapshots; physical current text по-прежнему проверяется на целостность и учитывается в corpus limits.

[P7a inventory и retrieval eval](retrieval-evaluation.md) фиксирует synthetic literal baseline, известные FP/FN и протокол сравнения до добавления индекса/provider.
