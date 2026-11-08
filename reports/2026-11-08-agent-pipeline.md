# Агентный pipeline с checkpoints/resume — 8 ноября 2026

Время фиксации: 14:57 Asia/Novosibirsk. Длительность блока отдельно не замерялась.

Добавлен первый многошаговый execution-срез этапа 4: фиксация доказательств → проверенный модельный черновик → детерминированный пакет для проверки человеком. В пайплайне один модельный вызов, отдельный LLM critic не добавлялся. Human-approved workflow проекта, claims, варианты и решения не изменяются автоматически.

Реализация:

- Отдельные доменная модель AgentPipeline, port, AgentPipelineService, SQLAlchemy model/repository, CLI pipeline_commands и MCP pipeline_tools. В AgentAnalysisService выделено выполнение заранее зарезервированного run; общие функции контекста и проверки цитат переиспользуются.
- Миграция 0011_agent_pipelines применена к PostgreSQL 17. Versioned pipeline хранит ссылки на закреплённые ревизии, model/prompt version, хэш запроса и fingerprint конфигурации, статус, run ID и review packet. Полные промпты и raw model output не сохраняются.
- Резервирование pipeline и running agent_run выполняется одной транзакцией до внешнего вызова, с блокировкой строки и проверкой expected_version. Composite FK защищает project/run связь. Внешний вызов выполняется вне DB-транзакции.
- Resume восстанавливает исходные ревизии без нового FTS и проверяет hash источника/запроса. Изменение model/endpoint/max_tokens/extra_body/prompt/schema блокирует новый вызов; смена API-ключа и timeout разрешена fingerprint-политикой. Внутреннее обновление серверной модели под тем же alias не обнаруживается.
- Если run succeeded, но pipeline не успел обновиться, resume переходит к draft_ready без генерации. Если run running/исход неизвестен, повтор блокируется. Failed не повторяется автоматически. Повтор completed возвращает прежний пакет, в том числе со старой version.
- CLI: pipeline start/show/resume. MCP: psa_main_start_pipeline/get_pipeline/resume_pipeline; production inventory вырос до семи инструментов. Границы платного действия обозначены annotations и описаниями.

Проверки:

- Все 96 unit-тестов прошли: 12 новых pipeline/MCP тестов и две проверки привязки reserved request/config fingerprint. Покрыты отсутствие вызовов на start/review, восстановление после checkpoint, неизвестный исход, устаревшие версии, drift, project scoping, insufficient evidence и повторная проверка цитат.
- Alembic check: No new upgrade operations detected.
- Финальный scripts/smoke_agent_pipeline.py прошёл на настоящем PostgreSQL с синтетическим ModelProvider. Проверены original revision после source update, recovery после succeeded run до pipeline update, unknown running без повтора, два конкурентных workers с одним вызовом, rollback после INSERT attempt до UPDATE pipeline, отсутствие orphan rows, отказ composite FK межпроектной ссылки, CLI и настоящий stdio MCP subprocess. Всего три fixture-вызова для трёх сценариев; внешняя модель не вызывалась.
- Контрольный проект `pipeline-9ccbd2f0fe91`; completed pipeline `8d2de65e-f78e-4b36-bb53-c089f97d6c6e`; recovery `36c823be-ad39-4738-9d3b-5ea691be2981`; намеренно оставленный unknown `2ee74ead-89b2-47cc-968d-e4590a5ee6ab`.
- Регрессия standalone agent с LiteLLM/MockTransport прошла: `agent-8b1759bcc755`, run `f4df054f-d249-4ae3-865e-eb30ae2669a9`. Регрессия MCP/CLI parity: `mcp-main-f266fcdde2f3`, run `94a65f5b-60b1-4d74-93a0-6992d867d6b3`, семь инструментов, stdio true.
- Проверки выполнены в локальном Python-окружении с PostgreSQL в Docker; образ приложения не пересобирался. Синтетические записи сохранены для просмотра, включая намеренно оставленные running checkpoints. git diff --check прошёл.

Ограничения: pipeline completion не означает human approval или semantic entailment. После сбоя до сохранения ответа нет exactly-once гарантии удалённого API и автоматического способа узнать, был ли запрос выполнен/оплачен. Lease expiry, reset и retry failed/unknown не реализованы; автоматического повторного платного вызова нет. Реальный Qwen ранее проверен отдельно, в этом блоке новых живых вызовов не делалось.

Инструкция docs/agent-pipeline.md, диаграмма diagrams/main/agent-pipeline.mmd, планы и README обновлены. Следующее развитие — типизированные аналитические шаги, отдельная critic-проверка и контроль качества результатов на разрешённых кейсах. Полный стратегический workflow и отложенные M6/M8 не объявлены завершёнными.
