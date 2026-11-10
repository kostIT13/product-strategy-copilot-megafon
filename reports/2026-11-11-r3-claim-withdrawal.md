# R3: явный отзыв claim и effective evidence

Дата завершения: 11 ноября 2026, 00:14 (Asia/Novosibirsk). Ветка `feature/main-solution-roadmap`. Итерация начата 10 ноября; длительность отдельно не замерялась.

## Сделано

Добавлены отдельные domain model/projection/dependency guards, port/service и CLI/MCP interfaces. `psa claim withdraw ID C-ID --by PERSON --reason REASON` / `psa_withdraw_claim` требуют explicit human instruction по политике, actor/reason по schema, caller UUID и optional expected version. Сохраняются snapshot/hash/impact/actor/time; original claims, sources, capabilities, options, decisions и approvals не переписываются. Workflow v1 state/events journal даёт общий ACTIVE/recovery/replay; новый формат bundle не вводился.

`psa claim impact` / `psa_claim_impact` показывают effective inactive claims, зависимые options/capabilities/decisions и related contradictions. Legacy supersedes учитывается, циклы/повторные withdrawal/изменённая immutable history отклоняются. Needs_review — derived view; человеческий выбор не меняется. CLI status/resume показывает необходимость review. Новые support links и chosen/rejected option refs не используют inactive evidence; historical ledger replay сохранён.

Coverage, promise/baseline proof и новые gates учитывают effective state. Verify не выдаёт inactive claims за текущие citations, но сохраняет source integrity/структурные проверки. Evidence/options gates используют текущие основания; strategy/validation не переиспользуют затронутое текущее решение автоматически. Critic-pack исключает inactive claim statements и показывает audit. Сам источник не удаляется и остаётся доступным новому исследованию.

Добавлен renderer v2: active evidence, audit inactive IDs/statuses, affected capabilities как needs_review и review notes для options/decision. Frozen v1 сохранён; старые receipts без builder marker и новые v2 операции воспроизводятся. Auto replay сравнивает business intent, внутренний builder marker не подменяет request intent. Новые generations только v2; после withdrawal validation gate требует свежую v2 generation, не adoption/old replay. Author drafts не перезаписываются.

README/MCP docs, основной план/roadmap, ledger/render contracts и quality canon обновлены; 9 generated adapters пересобраны. R3 остаётся открытым: отдельная audited correction/supersede команда, source withdrawal, review/reopen и semantic/numeric consistency ещё впереди. Future production-ready roadmap остаётся в плане; hooks/subagents не включались автоматически.

## Проверки

- Полный unittest suite: **346 tests, OK (1 skipped: Windows symlink privilege unavailable)**, 354.314 s.
- Targeted withdrawal suite: 10 tests OK; прежние 9 render/recovery tests также прошли отдельно. Первый withdrawal run имел неверное ожидание обязательного initial approvals key; тест исправлен на optional empty list, поведение сохранения истории не менялось.
- Новые tests: canonical bytes/choices unchanged, dependent review, inactive support guards + old ledger replay, verify/source integrity, baseline withdrawal, actor/reason/version/busy/duplicate/cycle/tamper, fresh current human decision, render freshness, renderer v1 missing-marker compatibility/v2 audit/replay, реальные process interruptions на 6 границах с copy/recover/later writes, CLI/real stdio parity.
- Base environment без SQL/model/parser/MCP extras прошло completed workflow/copy resume. Оба demo прошли с unchanged read-only inputs и 0 model calls. Native Gitleaks и итоговые Ruff/docs/sync/repository-history/diff results фиксируются в development log.

## Границы

Attribution не является authentication. Проекция структурных refs не распознаёт все смысловые зависимости prose. Completed status/старые approvals остаются историей; automatic reopen/reapproval нет. Старый render replay не обновляет views, после withdrawal нужен новый UUID generation. Отзыв replacement не восстанавливает прежний claim. Полное исправление/отзыв источников, новые human review/reopen operations и semantic consistency — следующие задачи; general draft/input freshness не объявлена решённой.

Реальные продуктовые кейсы, БД/Docker/.env/real LLM не использовались/не менялись. Remote Actions, live R1/M8 и независимая M6 оценка не запускались и не объявлены пройденными. Пользовательские данные не удалялись.
