# R3: метрики, baseline и план измерения

Дата: 10 ноября 2026 (Asia/Novosibirsk); точное время завершения — в development log. Ветка `feature/main-solution-roadmap`. Длительность отдельно не замерялась.

## Сделано

Добавлены отдельные domain schema/parser/report, application port/service, filesystem store и тонкие CLI/MCP adapters. `psa validation check ID` / `psa_check_validation_plan` читают один psa-validation-v1 JSON block внутри authored drafts/validation-plan.md. Обязательны hypothesis/expected_change, metric name/definition/unit/population/data_source, comparison/success criterion, observation start/duration, guardrails с definition/data source/stop rule/owner и общий owner/decision rule.

Baseline reported требует finite number и current active fact: используются существующие native locator/quote/hash/revision/v4 claim proof checks. FilePromiseReader получил read_for_claims для явной выборки baseline refs без изменения обычного promise интерфейса. Baseline unknown требует явного null, reason и measurement method/owner/timezone-aware deadline. Значения и результаты не выдумываются; semantic/numeric alignment, observed effect и permission flags false.

Новый validation gate требует complete typed plan и сохраняет отдельный review_hash/status/version в audit наряду с прежними strategy/promise checks. Схема кейса, workflow journal и frozen render/templates не менялись; structured block остаётся частью authored Markdown и попадает в generated view без второй JSON-копии. Historical approvals/replay и demo читаются в прежней механике; новый approval narrative-only плана блокируется.

Обновлены CI/base/gate synthetic fixtures, README/MCP docs, agent/quality.md, 9 generated adapters, основной план и roadmap. По запросу пользователя в основной план добавлен будущий пересмотр после R3: полный production-ready roadmap с CLI/FastMCP/host parity, opt-in subagents/hooks, research/retrieval/knowledge tools, hardening/privacy/recovery, наблюдаемостью/cost, release/rollback и измеримым demo/eval комплектом для хакатона. Это будущая работа, не заявление production readiness или гарантии победы. Текущий запрет автоматических subagents/hooks не снимался.

## Проверки

Полный unittest suite: **336 тестов, OK (1 skipped: Windows symlink privilege unavailable)**, 318.916 s. Включены все 10 новых measurement tests и повтор прежних promise/structure/recovery проверок.

Первые 9 measurement tests прошли отдельно; добавлена проверка коротких units/owner roles и запрета blank fields. Набор проверяет explicit unknown/null, missing fields/guardrails/deadline, strict numeric/version/window/timezone, duplicate/invalid JSON и fences/comments, reported baseline proof/missing/stale/corrupt evidence, pending/busy/bounds, gate block/audit hash/historical replay и CLI/реальный stdio MCP parity/exit 3. Итог полного suite записан в development log.

Base environment без SQL/model/parser/MCP extras прошло completed workflow и copied resume. Оба demo прошли, read-only inputs unchanged, model_calls=0. Native Gitleaks history/tree/negative probes прошли без находок. Ruff/docs/repository-history/sync/diff checks выполнены перед коммитом.

## Ограничения и дальше

Schema проверяет полноту/типы; достаточность threshold, observation period, sample/control, deadline и соответствие чисел/unit/population evidence оценивает человек. Narrative prose может противоречить block: автоматическая semantic alignment не заявлена. Unknown baseline measurement plan не выдаётся за состоявшийся результат; successful gate не разрешает исполнение эксперимента или публикацию автоматически. Новым narrative-only legacy drafts нужен authored block перед новым validation approval.

R3 открыт: далее semantic/numeric consistency и correction/withdrawal lifecycle. Future production roadmap будет детализирован отдельно с критериями/зависимостями/рисками и проверкой пользы инструментов. Live R1/M8 и независимая M6 оценка не пройдены. БД/Docker/.env/real product cases/real LLM не использовались/не менялись. Remote Actions и live IDE проверки не запускались.
