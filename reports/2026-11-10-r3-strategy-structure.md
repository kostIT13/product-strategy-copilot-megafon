# R3: структурная полнота двух стратегий

Дата: 10 ноября 2026 (Asia/Novosibirsk); точное время завершения — в development log. Ветка `feature/main-solution-roadmap`. Длительность отдельно не замерялась.

## Сделано

Первый срез R3: отдельные domain/port/service/files reader и CLI/MCP adapters для обязательных восьми разделов product/communication drafts. `psa strategy check ID` и `psa_check_strategy` дают одинаковый read-only hash-bound report. Проверяются canonical RU headings или объявленные English aliases, наличие prose, placeholders/markers-only/code/comment bodies, duplicate sections и незавершённая разметка. Reader использует общий lock/ACTIVE guard, confined paths и 512000-byte limit на state/draft. Scope — structural completeness, не semantic alignment или publication approval.

Новые strategy gates требуют одновременно прежние decision/substantive/coverage/promise checks и полную структуру; validation gate проверяет её снова после generated integrity. Явный human gate сохраняет strategy_structure review_hash/status/version отдельно от promise reference. Формат journal, старые receipts и frozen render/templates не менялись; UUID replay исторического approval не переутверждает текущие drafts. Read-only validate/verify/coverage/render не объявлены проверкой полной R3 structure; старые demo replay сохраняют прежнюю механику.

Обновлены README, MCP tools list, планы/roadmap и agent/quality.md; sync --write пересобрал 9 generated adapters с новым canonical digest, sync --check прошёл. Добавлен контракт strategy-structure. Synthetic CI author fixture содержит восемь заполненных разделов; base smoke и gate fixtures используют её вместо прежних одноабзацных drafts. Это не реальный продуктовый кейс или рыночные основания.

## Проверки

Полный unittest suite: **326 тестов, OK (1 skipped: Windows symlink privilege unavailable)**, 330.897 s. Native Gitleaks history/working-tree/negative probes прошли без находок.

- Новые 8 tests прошли: complete/read-only/stable hashes/no-approval flags, missing/empty/placeholders/markers-only, fenced/commented/duplicate/unknown headings, English/H3/unclosed fence, state/bounds/pending/busy, structure block при зелёном evidence coverage, gate audit hash + historical replay, validation recheck после render, CLI/real stdio MCP parity/exit 3.
- Все 10 file-promise tests повторены и прошли после усиления gate fixtures.
- Base environment без SQL/model/parser/MCP extras прошло полный workflow до completed и copied resume. Оба CI demo прошли с 0 model calls и unchanged read-only inputs.
- Ruff/docs/repository-history/sync/diff checks прошли. Полный suite, native secret check и окончательный timestamp записаны в development log.

## Ограничения и дальше

Plain Markdown parser и минимум 24 prose letters — защита от пустых templates, не доказательство качества. Заполненные разделы не доказывают соответствие human choice, согласованность стратегий, экономику или истинность. Неподдержанные heading формы нужно привести к объявленному contract; полный natural-language inference не добавлялся. Новые gates старого незавершённого кейса потребуют заполнить разделы; старые approvals автоматически не меняются.

R3 остаётся открытым. Следующий срез — metric definitions/unit/population, baseline либо measurement plan, критерии сравнения, observation window, guardrails/stop rule, owner/data source; затем semantic consistency и corrections/withdrawal. Live R1/M8 и независимая M6 оценка остаются отложенными. PostgreSQL/Docker/.env, реальные продуктовые данные и real LLM не использовались/не менялись. Remote Actions и live IDE проверки не запускались.
