# Внутреннее утверждение и экспорт стратегии — 8 ноября 2026, 23:13 (Asia/Novosibirsk)

## Что реализовано

Отдельные StrategyApprovalCommand, application service/port, PostgreSQL model/store и transaction guards. Миграция 0017_strategy_approvals применена к локальной development-БД; alembic check не обнаружил расхождений. На project/strategy run сохраняется одна неизменяемая запись принятия для internal_review, с командой человека и полным рассмотренным snapshot. Одновременный повтор возвращает ту же запись, отличающаяся команда отклоняется.

Preview связывает успешный strategy_plan с его critic, исходным решением/выбором и pinned источниками. Запись требует confirmed=true, owner, review_note, preview hash и явного ответа на замечания/неопределённость critic. Под database locks заново проверяются runs, selection, strategy input, decision/option и их связи, актуальные source revisions/hash. Изменения после preview откатывают всю операцию. Неполные основания, другой проект/critic, устаревшие источники и недостаточные доказательства блокируют запись.

CLI получил strategy preview-approval/approve/approval/export; FastMCP — четыре соответствующих инструмента, inventory 18. Экспорт возвращает JSON envelope с UTF-8 содержимым strategy.md, communication.md, experiments.md, review.json и SHA-256 для каждого файла. Сам интерфейс не пишет произвольные host files и ничего не публикует. Повторный экспорт проверяет неизменность рассмотренных данных и актуальность источников; историческое утверждение при этом остаётся читаемым.

При PostgreSQL/CLI проверке выявлена проблема default encoding Windows при перенаправлении Unicode JSON; main CLI stdout переведён на UTF-8. Markdown держит недоверенный контент внутри отступленного структурированного JSON. Добавлены инструкция docs/strategy-approval.md, диаграмма и обновления README/MCP/roadmap/основного плана; CI strategy smoke расширен проверками утверждения.

## Проверки

- Все 180 unit-тестов прошли; 10 новых покрывают подтверждение, scope/hash/owner, critic resolution, replay, stale export, чужой проект, недостаточные доказательства, canonical changes, SHA-256 и CLI/MCP parity.
- PostgreSQL selection→strategy→critic→approval→export smoke прошёл с fixture-only MockTransport, конкурентной записью, отсутствием дублей и rollback при изменении решения/critic/input/текста источника между preview и записью.
- Настоящий stdio и CLI совпали с core для preview, повторной записи, чтения и экспорта. Проверен project-bound FK (SQLSTATE 23503), stale export, исторический replay без модели и отсутствие workflow gate side effects.
- Ruff, docs (114 документов), git diff и forbidden-paths/full-history check прошли. Gitleaks: 0 находок в истории/рабочих файлах, отрицательные пробы прошли, сканирование без сети.
- Docker smoke прошёл: frozen image, offline Alembic SQL, 18 FastMCP tools, non-root/read-only/network none и оба demo; model_calls=0.

## Границы и следующий шаг

Принимается внутренний черновик, не факт и не публичное обещание: publication_approved=false, customer_promises_approved=false, workflow_approval_granted=false, identity_verified=false. Owner заявляется человеком; RBAC/отзыв утверждения/полный revisit не реализованы. Выданные файлы не отзываются автоматически при последующем изменении источников. Capability-backed customer promises остаются следующим срезом этапа 5; затем AGENTS.md/skills/IDE-адаптеры и knowledge integration этапа 6.

Живых LLM-вызовов нет; .env и зависимости не менялись. Синтетические проекты и новая таблица остались в локальной development-БД. Автономный агент/LangGraph не добавлялись. Вход approval пока — существующий strategy_plan run опционального API-инструмента; приём черновиков непосредственно от IDE-агента без нашего LLM-клиента остаётся интеграцией этапа 6. Remote Actions result не подтверждён. Длительность отдельно не замерялась.
