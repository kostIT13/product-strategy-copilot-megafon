# План инструкций и структурированный evidence extraction — 8 ноября 2026

Время фиксации: 15:16 Asia/Novosibirsk. Длительность блока отдельно не замерялась.

По запросу пользователя в основной план добавлен отдельный пакет инструкций: AGENTS.md как канонические правила и тонкие адаптеры/конфигурации .cursor/, .claude/, .codex/ для Cursor, Claude, Codex. Критерии: проверка поддерживаемых форматов и фактической загрузки, синхронизация, CLI/MCP parity, отсутствие секретов и дублирования общих правил. Сами файлы инструкций пока не реализованы. Изменение плана сохранено отдельно коммитом 7d98455.

Следующий аналитический срез реализован как task evidence_extraction поверх общего агента и checkpoint-пайплайна:

- Отдельные Pydantic-схемы ExtractedStatement/EvidenceGap/EvidenceExtractionDraft, стабильные task IDs, версионированный evidence-extraction-v1 prompt и registry application/agent_tasks.py. Факты, гипотезы и gaps разделены. Гипотеза требует validation_question; каждому утверждению нужна точная цитата, а все указанные gap citations тоже проверяются.
- Existing evidence_answer остаётся default. CLI agent analyze / pipeline start получили --task; MCP prepare/analyze/start_pipeline — optional task с enum. Количество MCP-инструментов осталось семь.
- Task сохраняется с agent_run и pipeline, участвует в проверке reserved request и связывании attempt. Resume восстанавливает правильный prompt/schema и формирует типизированный human review packet; перепутать answer и extraction при резервировании/проверке нельзя.
- Миграция 0012_agent_tasks применена к PostgreSQL; старые записи backfilled как evidence_answer. Исходный answer prompt/schema не менялись. Downgrade защищён от удаления типа существующих extraction-записей. Alembic check не обнаружил новых операций.
- Извлечённые fact drafts не создают канонические claims, decisions, capabilities или approvals. Точная цитата не доказывает смысловую обоснованность всей формулировки; critic и human review остаются отдельными шагами.

Проверки:

- Все 108 unit-тестов прошли, включая 12 новых extraction/MCP проверок: типы/обязательные поля, unsupported tasks и schemas, факт без цитаты, гипотеза без проверки, цитаты statements/gaps и дубли, insufficient evidence, task-aware resume и совместимость default answer.
- scripts/smoke_evidence_extraction.py прошёл на PostgreSQL с настоящим LiteLLM SDK и MockTransport: два statements (fact/hypothesis), один gap, pinned revision, сохранение task, отказ выдуманной gap quote и неверного task binding, отсутствие canonical claims/workflow изменений, CLI и отдельный stdio subprocess. Проект extraction-20c8d90f9acd; pipeline 3d664651-8077-4c6d-a1f9-cd67a39168ba; run 821bf2df-5e7f-41fd-adc1-8b44afe0564d.
- Реальный подготовленный checkpoint до миграции успешно реконструирован с прежним request hash без вызова модели: 58738a86-4ff8-4d56-af15-8e4c2ffbccf9 (pipeline-9ccbd2f0fe91), task evidence_answer.
- Регрессия pipeline recovery/concurrency/rollback/CLI/MCP прошла: проект pipeline-a92340497c1a, completed 9cc4fbc9-d92b-4be9-8ccd-3b125904d233. Регрессия stdio MCP/CLI: mcp-main-b7fd0a0d68ea, run fa813a2e-c59e-4b62-afc7-d1661282acf5, семь tools.
- Живая попытка с тестовым лимитом 1024 вернула provider_incomplete_completion; невалидный/незавершённый результат не принят. Failed run cf913f09-900b-4847-acb5-c458f8e948b4, проект live-agent-be01f953b239.
- После явного изменения smoke-limit до 2048 (не выше настроенного лимита) выполнена одна новая контрольная попытка, без автоматических retries. Qwen3.8-27B вернула extracted: два fact drafts, два gaps и четыре точные цитаты. Проект live-agent-40d3aeded503, run 1bddae12-1027-4487-82c3-6ed9d9c3fa35. Usage: input 1194, output 1154, total 2348 токенов, duration_ms 10250, cost null. Успешный ответ превышает первоначальные 1024 output tokens. Передавались только две синтетические фразы об экспорте и неуказанной цене. Проверено в БД: canonical claims 0, workflow не создан.
- Обновлён scripts/smoke_agent_live.py --task: answer ограничен 512, extraction 2048, оба не выше настроенного значения; timeout операций до 45 секунд. В блоке две явные живые попытки, повторов в коде нет.

Документация: docs/evidence-extraction.md, существующие инструкции и README обновлены. Проверки использовали локальный Python и PostgreSQL в Docker; образ приложения не пересобирался. Синтетические артефакты оставлены для просмотра. git diff --check прошёл.

Следующий аналитический срез — отдельная critic-проверка типизированных результатов и дальнейшее развитие стратегических шагов. Один живой синтетический кейс не заменяет независимую оценку качества, semantic entailment и отложенные M6/M8. Запланированные IDE-инструкции не объявлены готовыми.
