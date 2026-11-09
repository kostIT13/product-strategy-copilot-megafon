# R2: поиск по файловым источникам

Дата фиксации: 10 ноября 2026 (Asia/Novosibirsk); точное время завершения — в development log. Ветка: `feature/main-solution-roadmap`. Длительность отдельно не замерялась.

## Сделано

Добавлены отдельные domain request/snapshot/literal matcher, application service/port, filesystem snapshot adapter и тонкие CLI/MCP модули. Команда `psa source search ID QUERY --limit N` и инструмент `psa_search_sources` возвращают одинаковый JSON без SQL, сети, модели или derived index.

Adapter читает текущий source registry и text под общим case lock; проверяет state, уникальность IDs, canonical current paths/confinement, UTF-8 и каждый content hash до выдачи результата. Pending/busy не обходятся. Поиск не включает history, binaries, title/URI или прочие файлы кейса. Snapshot возвращает workflow_version и hashes; эти references не резервируют версию для последующей записи claim.

Literal case-insensitive matching, один hit на совпавшую секцию, стабильный порядок source ID/section. Возвращаются точная quote до 500 символов, native page/cell locator или existing paragraph locator, matched_sections и explicit truncated. XLSX ищется по значениям, формулы остаются строками; PDF markers и duplicate cell coordinates проверяются. Caps: query 200 символов, limit 1–50, 500 sources, 10 MiB/source, 32 MiB/corpus, metadata 512 KiB, 50000 sections. Corrupt/over-limit corpus отклоняется без частичного результата, даже после первых совпадений.

Обновлены README, MCP tools list, основной план/roadmap, inventory и новый контракт file-source-search. Legacy FTS помечен отдельно; stemming/ranking/title weighting не объявлены перенесёнными. Следующий срез — нужный promise preflight/quality gate, затем mapping/import/parity и вывод PG/Alembic/Docker dependencies/CI.

## Проверки

Полный unittest suite: **322 теста, OK (1 skipped)**, 280.979 s.

Targeted suite: 11 tests, OK, **1 skipped** (Windows symlink privilege unavailable). Остальные включают literal/Unicode/quote windows/order/truncation, current revision only, malformed input до storage, corrupt/missing/duplicate/path/history/state/JSON, pending/busy/reentrancy, source/byte/section caps, ambiguous native scopes, отсутствие SQL/model/parser dependencies, реальные PDF/DOCX/XLSX locators с последующим verify, CLI → real MCP stdio parity и byte-for-byte read-only case. Оба CI demo прошли с 0 model calls. Полный suite и итоговые checks фиксируются в development log.

## Ограничения

Literal retrieval не равен semantic search/SQL FTS и не подтверждает истинность источника. Неподдержанный status/format или неканонический current path требуют явного разбора, не молчаливого пропуска источника. Прямые изменения файлов вне общего lock не входят в concurrency guarantee. Windows symlink integration в новых tests пропущен; confinement guard используется общий, обход guard не добавлен.

БД/внешние сайты/real LLM/Docker/.env не использовались; dependencies и пользовательские данные не менялись. Legacy import и clean install без старых dependencies ещё не завершены; R2 открыт. Remote Actions и Docker gitleaks не запускались. Live R1/M8 и независимая оценка M6 остаются отложенными, не пройденными.
