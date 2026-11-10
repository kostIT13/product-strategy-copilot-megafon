# R3: отзыв источников и зависимых оснований

Завершено: 11.11.2026 01:21 (Asia/Novosibirsk). Ветка `feature/main-solution-roadmap`. Итоговые проверки записаны также в development-log.md; длительность итерации отдельно не измерялась.

## Сделано

Добавлены отдельные typed domain command/projection/planner, application service/port, filesystem v6 bundle codec и тонкие CLI/MCP interfaces. `psa source withdraw CASE S-ID --by PERSON --reason REASON` / `psa_withdraw_source` требуют автора/причину по schema и явного указания человека по политике. `psa source impact` / `psa_source_impact` показывают withdrawn source IDs, dependent claims/options/capabilities/decisions и текущую необходимость review. Optional expected version/caller UUID и общий lock/ACTIVE protocol сохранены.

Отзыв затрагивает весь source ID. Исходные source metadata/text/archive, claim records, supports, decisions и approvals не переписываются. Event сохраняет snapshot/hash/actor/reason/time/impact. Новый workflow v6 публикует state/events, хранит fixed canonical ledger inputs до 4 МиБ и полностью реконструирует event/impact/after-state. Старые v1–v5 read/replay/recovery сохранены. Даже rehashed подмена impact отклоняется; completed replay возвращает прежний результат без сброса позднейших writes. Проверены реальные остановки отдельного процесса на шести границах с переносом каталога/recover.

Active claim с withdrawn source получает derived source_withdrawn status. Отзыв любой ссылки блокирует весь claim; остальные источники автоматически не считаются достаточными. Existing inactive evidence guards распространяются на supports, current decisions, coverage, promises, reported baseline и gates. Новые claim/correction refs отвергают withdrawn source. Источник исключается из search/citation snapshot, но сохранённый current text по-прежнему проходит path/hash/UTF-8 и corpus limits. Verify сохраняет source integrity; renderer v2 показывает source withdrawal audit/inactive claims, critic-pack исключает inactive claim statements. CLI source list показывает effective status. Source_collection считает только effective extracted sources; новый validation требует render v2 после source withdrawal.

Новый import/revision известного withdrawn ID/requested URL отклоняется до acquisition; redirect к отозванному final ID — после acquisition, до публикации. Completed historical import UUID продолжает replay без acquisition/реактивации. Новое независимое основание можно явно связать через audited claim correction; обход отзыва копированием материала под новым ID не разрешается инструкциями. Completed case автоматически не открывается и decisions не меняются.

Обновлены quality canon и 9 generated IDE adapters, README, CLI/MCP/search/promise/recovery/lifecycle docs и оба плана. Base smoke включает v6 отзыв вспомогательного синтетического источника, затем полный corrected evidence → completed → review/reopen → новое решение → повторные gates → copied resume путь без SQL/model/MCP extras.

## Проверки

Targeted suite: 7 tests за 33.740 s, OK. Проверены canonical bytes/choices preservation, dependent impact/coverage/promises/baseline/source gates, search exclusion и integrity withdrawn text, новые support/claim/import guards и old import replay, исправление по независимому source, actor/version/busy/duplicate/request conflict/metadata tamper, rehashed bundle tamper, process interruptions/copy/recovery/later writes и CLI/real FastMCP stdio parity. В первом прогоне исправлен test fixture: pretty JSON ошибочно записывался в JSONL metadata; продуктовая логика не менялась из-за этой ошибки. Начатый full suite перезапущен после исправления fixture.

Clean-base workflow/copy/reopen и оба demo прошли, model calls=0. Полный unittest suite: 367 tests за 819.079 s, OK (1 skipped: Windows symlink privilege unavailable). Ruff, instruction sync (9 adapters), docs (178 documents), repository-history и diff checks прошли. Native Gitleaks 8.30.1 history/tree/negative probes — без находок.

## Границы

Attribution не является authentication, hashes не защищают от владельца, переписывающего весь каталог. Impact видит структурные ссылки; semantic/numeric alignment остаётся следующим R3. Source reactivation, rollback незавершённого workflow и production-ready hardening не объявляются готовыми. Live R1/M8 и независимая M6 остаются отложенными; hooks/subagents автоматически не включались.

Реальные кейсы/.env/пользовательская БД не читались/не менялись, платные API/модели не вызывались. БД/контейнеры и второй agent loop не добавлялись. Проверки — на синтетических временных данных и копиях разрешённых demo. Стоимость IDE-сессии не измерялась.
