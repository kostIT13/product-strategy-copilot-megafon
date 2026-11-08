# LangGraph в основном плане — 8 ноября 2026, 22:55 (Asia/Novosibirsk)

**Историческая запись: решение отменено после сверки с требованиями.** Актуальная граница — IDE-агент + CLI/MCP и проверяемый workflow, см. [корректировку](2026-11-08-ide-orchestration-plan.md).

По запросу пользователя LangGraph закреплён как целевой основной framework оркестрации полной системы и ближайший инфраструктурный подэтап 4.1. Начать на текущих срезах этапа 5, до расширения approval/export и автоматических субагентов/хуков.

В основной план добавлены стек/границы и раздел 4.1: ADR/state/граф и SDK-независимый runner port, отдельные adapter modules, PostgreSQL checkpointer/setup/backup, durable operation keys, human interrupts, постепенный CLI/MCP rollout, совместимость legacy checkpoints и критерии приёмки с controlled failure scenarios. FastMCP, LiteLLM и domain services сохраняют свои роли; graph state не подменяет business ledgers. Неизвестный исход LLM-запроса не повторяется автоматически, перенос старых checkpoints не объявлен готовым.

Обновлён roadmap и порядок ближайших работ. Knowledge runtime integration остаётся этапом 6; субагенты/хуки — отдельными последующими расширениями. Default runner меняется только после fixture/PostgreSQL/concurrency/restart/CLI/stdio/Docker приёмки, не по наличию установленной библиотеки.

Технические основания проверены по официальным LangGraph persistence/checkpointers/interrupts страницам, ссылки в разделе 4.1. Учтено, что interrupt resume повторно выполняет node, а graph checkpoint не является транзакцией exactly-once с нашим внешним API/каноническими записями.

Изменения только в планах и отчётах: зависимости, код, .env и БД не менялись, LangGraph не установлен. Unit/integration tests не запускались; проверяются docs links и git diff. Длительность отдельно не замерялась.
