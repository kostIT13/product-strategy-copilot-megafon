# Linked critic для сохранённых черновиков — 8 ноября 2026

Время фиксации: 15:39 Asia/Novosibirsk. Длительность блока отдельно не замерялась.

Добавлен отдельный critic-проход по успешному evidence_answer/evidence_extraction run. Он использует закреплённые источники и канонический снимок исходного черновика без нового FTS. Исходный run/packet остаётся неизменным. Используется текущий настроенный провайдер в новом контексте; это не независимый человек или гарантированная верификация.

Реализация:

- Отдельные CriticDraft/CriticAssessment, evidence-critic-v1 prompt, AgentCriticService, critic_context и модули CLI/MCP. Каждая answer/statement/gap формулировка получает ровно одну assessment: supported, needs_revision или insufficient_evidence; reason обязателен, отрицательная/неопределённая оценка требует revision_request.
- Supported non-gap требует точной source citation. Все указанные цитаты сверяются с исходными source/revision/locator/text. Unknown/duplicate/missing item IDs отклоняются. Общий critic_verdict вычисляется сервером, а не принимается от модели как отдельный несогласованный балл.
- Миграция 0013_critic_inputs добавила input_run_id/input_hash в agent_runs и agent_pipelines, expanded task constraint и project-bound composite FK. Только critic допускает и требует input binding. Старые записи получают null refs; запросы answer/extraction не менялись. Downgrade отказывается удалять binding при наличии critic-записей.
- Critic pipeline фиксирует SHA-256 канонического target и всего запроса. Изменение исходного черновика или source snapshot блокирует продолжение до модели. Слишком большой сериализованный target (>48000 символов) отклоняется; оценки ограничены 40 items. Полный target/промпт в pipeline не копируется.
- Резервирование running attempt использует общий atomic row lock/expected_version механизм. Уже сохранённый succeeded critic run восстанавливается без повторного вызова. Unknown outcome не повторяется автоматически. Completed возвращает сохранённый packet.
- CLI critic prepare/start и MCP psa_main_prepare_critic/start_critic работают без LLM до resume. Main inventory вырос до девяти tools. Новая внутренняя задача evidence_critic не предлагается в обычном --task без input run.
- Packet всегда requires_human_review=true; semantic_entailment=model_assessed_not_verified. Исходный черновик не исправляется автоматически, canonical claims/решения/capabilities/workflow approvals не создаются. Ошибки повреждённого saved target скрывают Pydantic input details.

Проверки:

- Все 125 unit-тестов прошли: прежние 108 плюс 17 critic/MCP проверок. Покрыты coverage, invalid citations/schema/revision request, pinned input/hash, foreign/failed/running/critic targets, bounded target size, отсутствие утечки модельного содержимого, source corruption, extraction items/gaps, terminal no-op, checkpoint recovery и невозможность прямого FTS critic без target.
- Миграция применена к PostgreSQL 17; финальный Alembic check: No new upgrade operations detected. Pre-critic answer checkpoint из pipeline-9ccbd2f0fe91 восстановлен с прежним request hash и input_run_id=null без вызова модели.
- scripts/smoke_agent_critic.py прошёл с настоящим LiteLLM SDK/MockTransport, PostgreSQL и отдельным stdio subprocess: input FK для runs/pipelines, неверный binding без orphan attempt, hash drift до модели, source revision 1 после source update, recovery без повторного вызова, отказ unknown item, CLI/MCP parity, отсутствие rewrite/approvals. Финальный fixture-проект critic-419c285e57b3; input 54565d22-23b3-432f-a681-730f98b425c1; critic pipeline c0b69025-698a-4304-a6bc-069dfe044a07; run e22db64d-8ae2-4b34-a078-c4daaa85d2f7.
- Регрессии PostgreSQL pipeline/recovery/concurrency/rollback прошли: pipeline-b6ec890c5eef, completed 076bdcea-17a1-4219-99ff-ae84f63fa9c5. Extraction: extraction-b445832ce5e6, run cdcad16d-720b-4088-9eae-cef710168501. StdIO MCP/CLI: mcp-main-3a8284f0dd6c, run 7aee6692-8720-43bd-a5ea-a7645e08c2ad, девять tools.

Живая проверка:

- Первый технический вызов Qwen3.8-27B вернул needs_revision: critic-d4b0145e23cf, pipeline 8609fb4c-3a32-4192-b3c6-23a84f21289a, run dbb413ae-2c34-47ec-81fc-a9db7dee5279; input 1493, output 665, total 2158, duration_ms 6155, cost null. В исходной фикстуре caveat прямо называл черновик overclaim; это подсказка ожидаемого ответа. Этот результат учитывается только как API/serialization check, не как проверка качества critic.
- Подсказка удалена из генератора фикстур. Создан новый кейс с нейтральным caveat; старые записи не переписывались. Одна новая явная попытка также вернула needs_revision для «Export is unlimited and free.» при источнике «Export is available.». Проект critic-419c285e57b3, input 54565d22-23b3-432f-a681-730f98b425c1, pipeline 423a4c3e-e436-4cbd-ab32-74030c0014fe, run c8676c65-a83b-4712-a01a-88021c48b3af. Usage: input 1495, output 545, total 2040, duration_ms 5000, cost null.
- В блоке две явные живые попытки на синтетических материалах; автоматических retries нет. Каждая ограничена максимум 2048 выходных токенов, не выше конфигурации, и timeout операций до 45 секунд. Стоимость не выдумывалась. Один нейтрально оформленный toy case не заменяет baseline/слепую независимую оценку и реальные кейсы.

Документация docs/agent-critic.md, диаграмма diagrams/main/agent-critic.mmd, README и планы обновлены. Тестирование выполнено в локальном Python с PostgreSQL в Docker; образ приложения не пересобирался. Синтетические записи оставлены для просмотра; git diff --check прошёл.

Следующий срез — типизированные стратегические варианты и сравнение по доказательствам, с отдельной модельной критикой и обязательным человеческим выбором. Полный стратегический workflow, unknown/failed reset, M6/M8 и пакет IDE-инструкций ещё не завершены.
