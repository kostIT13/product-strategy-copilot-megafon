# Проверки чистого checkout

В `.github/workflows/ci.yml` добавлен первый срез CI. Он запускается для PR, push в main/feature/** и вручную через workflow_dispatch. Результат удалённого прогона нужно проверять в Actions; локальный успех не означает зелёную матрицу на GitHub.

## Что выполняется

- Ubuntu: Python 3.11 и 3.12, Windows: Python 3.12. Проверка актуальности lock, frozen install extras agent/documents/mcp и dev-группы, Ruff, unittest, `psa doctor`, `psa-main --help`.
- Отдельная Ubuntu/Python 3.11 установка без extras/dev: doctor и help обоих CLI. Отсутствие FastMCP в этом job — ожидаемое предупреждение optional component.
- Ubuntu/Python 3.12 и PostgreSQL 17 service: все миграции с нуля, Alembic check и семь smoke-сценариев main/agent/agent_pipeline/evidence_extraction/agent_critic/strategy_options/main_mcp. Agent-ответы фиксированы через MockTransport; проверяется настоящий FastMCP stdio subprocess.

Используются uv 0.11.30 и `uv.lock` из публичного PyPI. Полные SHA checkout v7.0.1 и setup-uv v10.3.3 сверены с официальными Git tags; Actions закреплены на commit. Источники: [checkout](https://github.com/actions/checkout/releases/tag/v7.0.1), [setup-uv](https://github.com/astral-sh/setup-uv/releases/tag/v10.3.3), [интеграция uv](https://docs.astral.sh/uv/guides/integration/github/).

Права workflow — contents: read, checkout не сохраняет credentials, PR не использует pull_request_target. У jobs есть timeout; новые прогоны той же ветки отменяют устаревшие. Пользовательский `.env` не создаётся, LLM-ключ пуст, endpoint — provider.invalid, cost map LiteLLM берётся локально. `smoke_agent_live.py` не входит в CI. Установка Python/зависимостей требует сети; фикстурные agent-проходы не требуют внешней модели.

Ruff пока проверяет E9/F63/F7/F82: синтаксис, некорректный control flow и неопределённые имена. Полный набор style/import rules и type checker остаются отдельным улучшением.

## Локальный повтор

Для проверки в отдельном окружении PowerShell:

```powershell
# Установите uv 0.11.30. Команды не требуют LLM_API_KEY.
$env:UV_PROJECT_ENVIRONMENT = '.venv-ci'
uv lock --check
uv sync --frozen --extra agent --extra documents --extra mcp --group dev --python 3.12
uv run --frozen --no-sync ruff check .
uv run --frozen --no-sync python -m unittest discover -s tests
uv run --frozen --no-sync psa doctor
uv run --frozen --no-sync psa-main --help
Remove-Item Env:UV_PROJECT_ENVIRONMENT
```

`uv run --no-sync` сохраняет уже установленный набор extras. Базовую установку проверяйте в другом окружении с `uv sync --frozen --no-default-groups`. Для проверки отсутствия скрытых настроек используйте свежий clone без `.env`; локальный doctor сообщает только о наличии файла/имён переменных.

PostgreSQL smoke создают синтетические проекты и failed checkpoints. Используйте отдельную временную development/CI БД и явно передайте её DATABASE_URL, затем выполните `alembic upgrade head`, `alembic check` и перечисленные `scripts/smoke_*.py` через тот же `uv run --frozen --no-sync`. В Actions БД изолирована service-контейнером и удаляется вместе с job. Пароль CI-service является публичным тестовым значением и не предоставляет доступа к рабочей БД.

## Что остаётся

Demo workflow, release packaging, secrets/history и docs checks, instruction-sync, Docker build smoke и настройки required checks пока не реализованы. Общего replay engine нет; фикстурные smoke не подменяют независимую оценку качества стратегий и отложенные пользовательские приёмки. Бейдж CI добавляется после подтверждённого удалённого зелёного прогона. План: раздел 14.1 в `docs/solution_plans/plan-main.md`.
