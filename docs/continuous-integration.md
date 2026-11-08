# Проверки чистого checkout

В `.github/workflows/ci.yml` и `demo.yml` добавлены проверки установки, тестов, документации, секретов и синтетического демо. Они запускаются для PR, push в main/feature/** и вручную через workflow_dispatch. Результат удалённого прогона нужно проверять в Actions; локальный успех не означает зелёную матрицу на GitHub.

## Что выполняется

- Ubuntu: Python 3.11 и 3.12, Windows: Python 3.12. Проверка актуальности lock, frozen install extras agent/documents/mcp и dev-группы, Ruff, unittest, `psa doctor`, `psa-main --help`.
- Отдельная Ubuntu/Python 3.11 установка без extras/dev: doctor и help обоих CLI. Отсутствие FastMCP в этом job — ожидаемое предупреждение optional component.
- Ubuntu/Python 3.12 и PostgreSQL 17 service: все миграции с нуля, Alembic check и семь smoke-сценариев main/agent/agent_pipeline/evidence_extraction/agent_critic/strategy_options/main_mcp. Agent-ответы фиксированы через MockTransport; проверяется настоящий FastMCP stdio subprocess.

Используются uv 0.11.30 и `uv.lock` из публичного PyPI. Полные SHA checkout v7.0.1 и setup-uv v10.3.3 сверены с официальными Git tags; Actions закреплены на commit. Источники: [checkout](https://github.com/actions/checkout/releases/tag/v7.0.1), [setup-uv](https://github.com/astral-sh/setup-uv/releases/tag/v10.3.3), [интеграция uv](https://docs.astral.sh/uv/guides/integration/github/).

Права workflow — contents: read, checkout не сохраняет credentials, PR не использует pull_request_target. У jobs есть timeout; новые прогоны той же ветки отменяют устаревшие. Пользовательский `.env` не создаётся, LLM-ключ пуст, endpoint — provider.invalid, cost map LiteLLM берётся локально. `smoke_agent_live.py` не входит в CI. Установка Python/зависимостей требует сети; фикстурные agent-проходы не требуют внешней модели.

Ruff пока проверяет E9/F63/F7/F82: синтаксис, некорректный control flow и неопределённые имена. Полный набор style/import rules и type checker остаются отдельным улучшением.

## Документация, секреты и демо

Docs job использует Markdown parser: проверяются локальные inline/reference/image links, anchors и обязательные файлы. Примеры кода пропускаются; HTTP/app/plugin ссылки не открываются. Проверка исправила пять существовавших битых ссылок.

Secrets job требует полный checkout (`fetch-depth: 0`): запрещает отслеживаемые .env/runtime-файлы также в истории, сканирует историю и безопасный экспорт рабочего дерева через Gitleaks CLI. Игнорируемый личный .env не читается. Используется [официальный образ Gitleaks 8.30.1](https://github.com/gitleaks/gitleaks/tree/v8.30.1), закреплённый на digest `sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f`; сканы выполняются с `--network none` и `--redact=100`. Наружу выводятся только rule/file/line/commit, без совпавшего текста и секретов. Отрицательные пробы генерируют искусственный ключ во временном Git-репозитории и проверяют обнаружение до и после удаления. Это эвристический сканер; он не доказывает отсутствие всех возможных секретов. Baseline/глобальные исключения не добавлены. Для локального запуска нужен Docker с доступом к каталогу репозитория и временным каталогам; загрузите образ по указанному digest заранее.

Demo workflow устанавливает базовый пакет без extras/dev, PostgreSQL и модели. `scripts.ci.demo` копирует demo/table-demo во временный каталог, строго проверяет цитаты (любое warning — отказ) и coverage, выполняет реальные validate/verify/coverage/resume CLI-команды и render с повторной валидацией. Read-only команды и весь прогон не меняют оригиналы. JSON summary содержит количество цитат/абзацев и model_calls=0; он отображается в GitHub job summary. Это воспроизведение локальных артефактов, а не общий engine записанных LLM-ответов. Сценарии PostgreSQL agent/critic/options с MockTransport остаются в ci.yml, чтобы не дублировать платные или фикстурные проходы.

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

Дополнительные проверки из корня (после установки dev-группы; секреты требуют Docker и полный Git checkout):

```powershell
.\.venv-ci\Scripts\python.exe -m scripts.ci.docs
.\.venv-ci\Scripts\python.exe -m scripts.ci.repository --history
.\.venv-ci\Scripts\python.exe -m scripts.ci.secrets
.\.venv-ci\Scripts\python.exe -m scripts.ci.demo --report .venv-ci/demo-report.json
```

Demo runner сам использует временные копии и не изменяет projects/. Secrets scanner не сканирует весь локальный каталог с .env/.venv; в экспорт попадают Git-tracked и новые неигнорируемые файлы.

## Что остаётся

Release packaging, instruction-sync, Docker build smoke и настройки required checks пока не реализованы. Общего replay engine нет; фикстурные smoke не подменяют независимую оценку качества стратегий и отложенные пользовательские приёмки. Бейдж CI добавляется после подтверждённого удалённого зелёного прогона. План: раздел 14.1 в `docs/solution_plans/plan-main.md`.
