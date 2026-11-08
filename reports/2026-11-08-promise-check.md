# Проверка клиентских обещаний — 8 ноября 2026, 23:29 (Asia/Novosibirsk)

## Реализовано

Первый capability-backed promise preflight: отдельные domain request/snapshot, application reader port, структурные evidence checks и PromiseCheckService, PostgreSQL reader, CLI/MCP adapters. Формулировки и явные capability/claim links подаются напрямую человеком или IDE-агентом; вызов нашего LLM-клиента и strategy_plan run не требуются. Новый CLI: psa-main promise check PROJECT --input promises.json; новый MCP: psa_main_check_promises, inventory 19. Для обнаружения UUID добавлен --json у capability list и claim list.

Проверяется каждая указанная capability (тот же проект, available), каждый выбранный claim (linked active fact), все evidence references: владение источником, текущая revision, целостность полного текста по SHA-256, точная цитата и поддержанный locator. Planned/unavailable, неподтверждённые ссылки, неактивные/нефактические claims, missing/stale/corrupt sources и непроверяемые locators блокируют preflight. Oversized source не проверяется по усечённому префиксу, а явно блокируется; request/evidence/response budgets заданы и документированы.

Reader выбирает только запрошенные IDs и их основания в одной PostgreSQL REPEATABLE READ, READ ONLY транзакции. Ответ содержит исходные формулировки, capability/claim/evidence snapshots, происхождение/ограничения источников, blockers, вопросы для review и review_hash. Семантическое соответствие и достоверность источников не объявляются проверенными. Даже результат eligible_for_human_review сохраняет publication_approved=false, customer_promises_approved=false и durable_approval=false. Нет автоматических фактов, решений, публикации или обхода workflow gates.

## Проверки

- Все 193 unit-теста прошли, из них 13 новых для unavailable/foreign capabilities, inactive/non-fact/unlinked claims, всех citations, missing/stale/corrupt/oversized sources, locator/quote, input/output budgets, строгого разделения структуры и семантического review, стабильности hash, CLI exit codes и MCP parity.
- PostgreSQL smoke_promises.py прошёл: UTF-8 CLI, --json UUID discovery, настоящий stdio, scope проекта, planned/stale blockers, отсутствие бизнес-записей от preflight. Concurrent commit после чтения capability не смешал старую capability с новой claim: observed transaction isolation=repeatable read, read_only=on.
- Standalone composition не создаёт LLM provider; stdio/CLI проверены без ключа и с неработающим provider endpoint. model_calls=0.
- Ruff и Alembic check прошли; новых миграций и зависимостей нет, текущая schema 0017_strategy_approvals.
- Docker smoke прошёл: frozen image, 19 FastMCP tools, non-root/read-only/network none, offline Alembic SQL и оба demo без модели. Docs (116 документов), git diff и forbidden-paths/full-history прошли; Gitleaks: 0 находок в истории и рабочих файлах, отрицательные пробы прошли, сканирование без сети.

## Документация и следующий шаг

Добавлены docs/promise-check.md и diagrams/main/promise-check.mmd; обновлены README, MCP inventory, основной план/roadmap и GitHub postgres job с новым smoke. Следующий срез — явное человеческое решение по точным обещаниям с транзакционной повторной проверкой и привязкой к артефактам. Затем — инструкции/skills/IDE adapters и knowledge integration этапа 6. Публикация и готовность всего этапа 5 не заявляются.

.env/зависимости/схема БД не менялись; только smoke создал и изменил собственные синтетические проекты в development-БД. Автономный агент/LangGraph не добавлялись, remote Actions result не подтверждён. Длительность отдельно не замерялась.
