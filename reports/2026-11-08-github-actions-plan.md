# План GitHub Actions — 8 ноября 2026, 16:27 (Asia/Novosibirsk)

По запросу пользователя адаптирован предложенный GitHub-процесс под текущее решение и добавлен в основной план, раздел 14.1. Изменения только в документации; workflows и настройки GitHub не создавались.

- Три workflow: ci.yml (unit/quality/PostgreSQL/FastMCP/secrets/docs/instruction-sync), demo.yml (синтетические источники и MockTransport), release.yml (тег, проверки, архив/wheel/sdist и draft release).
- Вместо отсутствующего sf: psa/psa-main, unittest и текущие scripts/smoke_*.py. Для демо предусмотрены validate/verify/coverage/resume; общий replay engine не объявлен существующим.
- Перед frozen install запланированы dev-группа, Ruff-конфигурация и uv.lock; sync check вводится вместе с каноническими IDE-инструкциями. PostgreSQL 17/Alembic и CLI/MCP parity проверяются отдельно от файлового MVP.
- Нет LLM-запросов/ключей/личного .env в CI. Указаны минимальные permissions, безопасные PR triggers, полная доступная история для secret scanning, SHA pinning, ограниченные artifacts и проверка архива из чистого каталога.
- Версии действий не скопированы из исходного примера: приведены официальные releases checkout/setup-uv, проверенные при обновлении плана; конкретные SHA фиксируются при реализации.
- Обновлены целевая структура .github/ и краткий roadmap; ближайшая инфраструктурная задача — CI, следующий продуктовый срез остаётся фиксацией проверенных вариантов и человеческого выбора.

Проверка: git diff --check и сверка команд/зависимостей/сценариев с pyproject.toml, README и scripts/. Тесты не запускались, исполняемый код не менялся. GitHub Actions не запускались. Длительность отдельно не замерялась.
