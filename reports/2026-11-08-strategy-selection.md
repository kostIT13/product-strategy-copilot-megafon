# Сохранение AI-вариантов и человеческого выбора — 8 ноября 2026, 21:54 (Asia/Novosibirsk)

Продолжен основной агентный сценарий этапа 5, ветка feature/main-solution-roadmap. Длительность отдельно не замерялась.

## Реализация

- Отдельные SelectionCommand/fingerprint, application port и StrategySelectionService; PostgreSQL adapter/model и миграция 0015_strategy_selections. CLI/MCP остаются тонкими интерфейсами; MCP inventory вынесен в общий constant (12 tools).
- selection preview связывает successful strategy_options с successful evidence_critic input_run_id/hash, восстанавливает pinned revisions, повторно валидирует цитаты и полное critic item coverage. Insufficient evidence не продвигается в canonical options. Preview возвращает reviewed draft/critic, hashes и stale source IDs без модели/записи.
- Явная SelectionCommand требует source/critic hashes, owner/rationale/review_note/review_trigger, confirmed=true и ровно одну disposition для каждого O1/O2/O3. Негативный/uncertain critic требует непустого человеческого critic_resolution. Supported critic не заменяет подтверждение. Revalidate_instances=always запрещает обход через внутренний model_copy.
- В одной транзакции создаются три proposed OptionRecord, один DecisionRecord с тремя dispositions и StrategySelectionRecord с полным audit snapshot. Ключи вариантов ai-RUNHEX-o1/o2/o3, ключ решения задаёт человек. Source/critic/decision/options привязаны project-bound FKs; options и decisions получили id/project unique constraints. Downgrade блокируется при существующих selection records.
- Под блокировками project/runs/sources/revisions проверяются fingerprints и актуальность исходной ревизии. Конфликты canonical key/FK откатывают весь набор. Идентичная нормализованная команда возвращает исходную квитанцию; другая команда к тому же source run отвергается. Исторический replay не означает повторную проверку текущей актуальности источников.
- Гипотезы/риски/эксперимент сохраняются как предложения; AI advantages не переносятся как доказанные strengths. Claim/evidence/capability и workflow approvals не создаются. Имя owner self-reported, identity_verified=false: сервер не доказывает участие человека и не реализует auth/RBAC. Клиенту явно предписано получать человеческое указание.
- CLI selection preview/record --input/show. Три новых FastMCP tools: psa_main_preview_selection, psa_main_record_selection (idempotent write), psa_main_get_selection. Изменения bootstrap/schema не меняли prompts/providers и не вызывали живую модель.
- CI PostgreSQL job дополнен smoke_strategy_selection; прежние fixture/stdio/Docker inventory checks обновлены до 12. Инструкции и планы обновлены; добавлены docs/strategy-selection.md и diagrams/main/strategy-selection.mmd.

## Проверки

- Все 160 unit-тестов — OK, включая девять новых selection tests: explicit confirmation/coverage/hash/project guards, отказ на stale sources, неизменность исходных runs, replay/conflict, resolution для negative critic, model_copy bypass и MCP parity. Ruff — OK.
- Первая попытка migration ожидала выключенный PostgreSQL и завершилась connection timeout. Контейнер поднят через docker compose up -d postgres с существующим volume; 0014→0015 применена, Alembic check не нашёл drift. .env не менялся, данные старых проектов не удалялись.
- PostgreSQL smoke: project selection-e4df07bc0a89, selection 80e9c094-add3-45b7-8a68-2c4b0c325cac; source run 073b3d54-9e2b-4115-8e11-6aa30a7bb49a, critic run 178bfb7e-ce73-4748-9673-d5d45cdfdaef, decision 41d28f46-300f-4899-b4ae-5a5a31260708. Четыре concurrent identical writes вернули одну квитанцию; в проекте ровно 3 options, 1 decision, 1 audit, 0 claims, workflow state отсутствует. Проверены stale checkpoint под backend lock, отказ без critic resolution, различающийся retry, rollback после collision decision key, run fingerprint guard, project FK rejection и CLI/real stdio MCP parity. Во время selection/read/retry число fixture model calls не менялось.
- Регрессия options/critic pipeline: project strategy-d3590e475a45, run 982c18ad-9855-418b-a727-92e33c100fff — passed. Production main MCP: project mcp-main-8d61c0bf4c0a, run 38b952f9-277e-4bbb-9f83-993880cd1ecc — passed, 12 tools, stdio и CLI parity. Только MockTransport.
- Docker Linux smoke — OK: frozen runtime, non-root/read-only/network none, offline SQL включая 0015, production inventory 12, оба demo, model_calls=0. Временный image tag удалён.
- Локальные docs/diff/YAML checks — OK; Gitleaks проверил историю/рабочий экспорт без находок, отрицательные пробы прошли. Remote GitHub Actions status не подтверждается локальными проверками.

## Следующий продуктовый срез

Подготовка продуктовой и коммуникационной стратегии/плана экспериментов на основе сохранённого решения, с coverage и контролем обещаний. Решения пока не редактируются через selection; последующий revisit, полный стратегический workflow, независимая оценка, IDE instructions и remote приёмки остаются открытыми. Живая генерация трёх вариантов по-прежнему не заявляется подтверждённой; новые модельные вызовы в этой итерации отсутствовали.
