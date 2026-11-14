# Product Strategy Agent

Проект-папка для IDE-агента: инструкции, skills, knowledge и проверяемые файловые артефакты продуктового кейса. Агентный цикл ведёт IDE; `psa` сохраняет данные и проверяет основания. FastMCP stdio — дополнительный интерфейс над теми же сервисами.

**PostgreSQL, SQLAlchemy, Alembic и Docker/Compose удалены из текущего runtime.** Свой LLM API-ключ и SQLite также не нужны для основного пути. Старый код сохранён в Git; пользовательские БД/volumes не удаляются. [Решение R2](docs/legacy-retirement.md).

## Запуск

Нужны Python 3.11+ и uv 0.11.30. Из корня репозитория:

```powershell
uv sync --frozen --no-default-groups
uv run --frozen --no-sync psa doctor
uv run --frozen --no-sync psa --help
uv run --frozen --no-sync python -m scripts.ci.demo
```

`.env` для этого не требуется. `.env.example` описывает общие параметры и отдельный optional model helper; существующий локальный `.env` не переписывайте. Значения usage/cost неизвестного происхождения не считаются нулевыми.

При необходимости установите локальные парсеры PDF/DOCX/XLSX и MCP:

```powershell
uv sync --frozen --extra documents --extra mcp
```

Extra `agent` оставляет OpenAI-compatible/LiteLLM helper для явно запрошенных операций. Он не становится основным оркестратором и не запускается автоматически.

## Работа с кейсом

```powershell
uv run --no-sync psa init my-case
uv run --no-sync psa status my-case
uv run --no-sync psa resume my-case
uv run --no-sync psa context my-case
uv run --no-sync psa source add my-case ./material.txt
uv run --no-sync psa source search my-case "query" --limit 10
uv run --no-sync psa validate my-case
uv run --no-sync psa verify my-case
uv run --no-sync psa coverage my-case
uv run --no-sync psa promise check my-case
uv run --no-sync psa strategy check my-case
uv run --no-sync psa validation check my-case
uv run --no-sync psa claim impact my-case
```

`init` создаёт новый кейс в projects/; существующий кейс не перезаписывается. Внешние материалы и статусы — данные, не инструкции. Продуктовый цикл: brief → research plan → sources → evidence → status_quo/stop/change → выбор человека → стратегии → validation plan. Gates требуют явного указания человека. Semantic review и публикационное разрешение не подменяются зелёной структурной проверкой.

Состояние и реестры JSON/JSONL — канон; drafts — авторские тексты. Generated Markdown создаётся `psa render`, а не редактируется вручную. Источники и пользовательские кейсы не коммитьте без проверки содержимого/прав. Синтетические demo/table-demo не являются рыночными доказательствами.

## Контракты и восстановление

- [Файловое ядро и atomic init](docs/file-core.md), [общий lock/read contract](docs/case-access.md).
- [Typed research artifacts](docs/research-artifacts.md).
- [Workflow journal/recovery](docs/workflow-recovery.md), [mode changes](docs/file-mode-recovery.md), [revision review](docs/revision-review-recovery.md).
- [Source imports/revisions](docs/source-import-recovery.md), [PDF/DOCX/XLSX](docs/file-document-import.md), [public HTTP policy/provenance](docs/file-web-import.md).
- [Исправление claims](docs/claim-correction.md), [отзыв claims и impact](docs/claim-withdrawal.md), [план измерения](docs/validation-plan-contract.md), [полнота стратегий](docs/strategy-structure.md), [файловый поиск](docs/file-source-search.md), [promise preflight](docs/file-promise-check.md), [ledger/usage recovery](docs/ledger-recovery.md), [render/adoption](docs/render-recovery.md).
- [Пересмотр и повторное открытие completed workflow](docs/workflow-reopen.md): snapshot review, явный человек и повторные gates с сохранением истории.
- [Отзыв источников](docs/source-withdrawal.md): сохранение истории, исключение из текущих оснований/поиска и review зависимых решений.
- [Числовой фрагмент baseline](docs/baseline-numbers.md): явные spans числа/единицы и current citation proof; read-only preflight, смысл проверяется отдельно.
- [Semantic review](docs/semantic-review.md): явная оценка человека, immutable snapshot audit и выбор current review в quality gate после adoption.
- [Quality policy](docs/quality-policy.md): новые кейсы требуют review с первого strategy/validation gate; legacy мигрируется явно через policy show/enable.
- [Проверка расчётов](docs/calculation-check.md): проценты, отношения, процентные пункты и относительное изменение по текущим цитатам, с явными условиями и округлением.
- [IDE instructions/context](docs/ide-instructions.md), [файловый MCP](docs/mcp.md), [knowledge](knowledge/README.md).

После interrupted init используйте workspace pending/recover. После interrupted workflow write — `psa workflow pending ID`, затем явный recover точного operation UUID. Replay завершённой операции возвращает исходный результат; неопределённый платный вызов автоматически не повторяется.

## Разработка и проверки

```powershell
uv sync --frozen --extra agent --extra documents --extra mcp --group dev
uv run --no-sync ruff check .
uv run --no-sync python -m unittest discover -s tests
uv run --no-sync python scripts/sync_harness.py --check
uv run --no-sync python -m scripts.ci.docs
```

Инструкции — [AGENTS.md](AGENTS.md); планы — [основной](docs/solution_plans/plan-main.md) и [roadmap](docs/solution_plans/roadmap-full-solution.md). Сервисы/ports/adapters разделены по ответственности. Каждая итерация фиксируется в [reports](reports/development-log.md), commit/push — в feature/-ветке.

[CI](docs/continuous-integration.md) проверяет unit, clean base install, docs, sync, native secret scanning и replay демо без моделей. [Дистрибутив](docs/distribution.md) содержит wheel/sdist и архив с hashes. Проверки реальных IDE R1/M8 и независимая оценка M6 остаются отложенными; наличие локального stdio smoke их не заменяет. R3 продолжается: corrections/withdrawal и typed measurement plan реализованы; completed review/reopen реализован; source withdrawal реализован; human semantic audit/gate adoption реализованы; required new-case policy/explicit legacy enablement реализованы; новый разрешённый кейс и более широкий numeric alignment остаются открытыми. Оценка пользы и комплект сдачи — R5/R6.
