# Проверки чистого checkout

В `.github/workflows/ci.yml` и `demo.yml` добавлены проверки установки, тестов, документации, секретов и синтетического демо. Они запускаются для PR, push в main/feature/** и вручную через workflow_dispatch. Результат удалённого прогона нужно проверять в Actions; локальный успех не означает зелёную матрицу на GitHub.

## Что выполняется

- Ubuntu: Python 3.11 и 3.12, Windows: Python 3.12. Проверка актуальности lock, frozen install extras agent/documents/mcp и dev-группы, Ruff, unittest, `psa doctor`.
- Отдельная Ubuntu/Python 3.11 установка без extras/dev: doctor, help файлового CLI и полный синтетический workflow/resume через scripts.ci.base_smoke без SQL/model/parser/MCP dependencies. Отсутствие FastMCP в этом job — ожидаемое предупреждение optional component.
- PostgreSQL services, Alembic и Docker jobs удалены в R2; API-orchestrator transport checks снятого psa-main не являются required checks текущего продукта.

Используются uv 0.11.30 и `uv.lock` из публичного PyPI. Полные SHA checkout v7.0.1 и setup-uv v10.3.3 сверены с официальными Git tags; Actions закреплены на commit. Источники: [checkout](https://github.com/actions/checkout/releases/tag/v7.0.1), [setup-uv](https://github.com/astral-sh/setup-uv/releases/tag/v10.3.3), [интеграция uv](https://docs.astral.sh/uv/guides/integration/github/).

Права workflow — contents: read, checkout не сохраняет credentials, PR не использует pull_request_target. У jobs есть timeout; новые прогоны той же ветки отменяют устаревшие. Пользовательский `.env` не создаётся, LLM-ключ пуст, endpoint — provider.invalid, cost map LiteLLM берётся локально. Live-модельные прогоны не выполняются в CI. Установка Python/зависимостей требует сети; фикстурные agent-проходы не требуют внешней модели.

Ruff пока проверяет E9/F63/F7/F82: синтаксис, некорректный control flow и неопределённые имена. Полный набор style/import rules и type checker остаются отдельным улучшением.

Unit job timeout задаётся явно каждой matrix row: Ubuntu15 min, Windows25 min. Windows P7d run673d6a1 был отменён через15 min с GitHub annotation `The job has exceeded the maximum execution time of 15m0s`; ранее локальный Windows full suite занимал18.2 min. Увеличен только общий job budget Windows с headroom для setup/host variation; unit tests, их собственные deadlines, guard/refusal assertions и required checks не сокращены. Cancelled timeout run не считается прошедшим suite.

## Документация, секреты и демо

Docs job использует Markdown parser: проверяются локальные inline/reference/image links, anchors и обязательные файлы. Примеры кода пропускаются; HTTP/app/plugin ссылки не открываются. Проверка исправила пять существовавших битых ссылок.

Secrets job требует полный checkout (`fetch-depth: 0`): запрещает отслеживаемые .env/runtime-файлы также в истории, сканирует историю и безопасный экспорт рабочего дерева через Gitleaks CLI. Игнорируемый личный .env не читается. Используется нативный [Gitleaks 8.30.1](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1), asset SHA-256 для Linux/Windows x64 закреплены в scripts/ci/install_gitleaks.py. Docker не нужен. Installer читает только именованный binary из проверенного архива. Сканы используют --redact=100; наружу выводятся только rule/file/line/commit, без совпавшего текста и секретов. Отрицательные пробы генерируют искусственный ключ во временном Git-репозитории и проверяют обнаружение до и после удаления. Native scan не имеет прежней контейнерной network isolation. Это эвристический сканер, не доказательство отсутствия всех секретов. Baseline/глобальные исключения не добавлены.

Для локального запуска установите binary через `python -m scripts.ci.install_gitleaks --directory .venv-ci/Scripts`, затем укажите GITLEAKS_BIN или добавьте эту папку в PATH. Запустите `python -m scripts.ci.secrets`. Локальный .env не читается.


Demo workflow устанавливает базовый пакет без extras/dev, PostgreSQL и модели. `scripts.ci.demo` копирует demo/table-demo во временный каталог, строго проверяет цитаты (любое warning — отказ) и coverage, выполняет реальные validate/verify/coverage/resume CLI-команды и render с повторной валидацией. Read-only команды и весь прогон не меняют оригиналы. JSON summary содержит количество цитат/абзацев и model_calls=0; он отображается в GitHub job summary. Это воспроизведение локальных артефактов, а не общий engine записанных LLM-ответов. Предметные unit-тесты сохранены; тесты снятых PG CLI/MCP dispatch удалены с интерфейсами.

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
Remove-Item Env:UV_PROJECT_ENVIRONMENT
```

`uv run --no-sync` сохраняет уже установленный набор extras. Базовую установку проверяйте в другом окружении с `uv sync --frozen --no-default-groups`. Для проверки отсутствия скрытых настроек используйте свежий clone без `.env`; локальный doctor сообщает только о наличии файла/имён переменных.

Дополнительные проверки из корня (после установки dev-группы; секреты требуют закреплённый native Gitleaks и полный Git checkout):

```powershell
.\.venv-ci\Scripts\python.exe -m scripts.ci.docs
.\.venv-ci\Scripts\python.exe -m scripts.ci.repository --history
.\.venv-ci\Scripts\python.exe -m scripts.ci.secrets
.\.venv-ci\Scripts\python.exe -m scripts.ci.demo --report .venv-ci/demo-report.json
```

Demo runner сам использует временные копии и не изменяет projects/. Secrets scanner не сканирует весь локальный каталог с .env/.venv; в экспорт попадают Git-tracked и новые неигнорируемые файлы.

Тот же base-only demo job запускает `python -m scripts.ci.research_smoke`: [offline research contracts](offline-research-smoke.md) проверяются на собственном temporary synthetic case без DNS/socket/process dispatch. Registry/fallback, revision/hash/quote, draft replay, corrupt/invalid refusal и withdrawal проверяются отдельно от человеческих gates. Оба JSON выводятся в summary; failure runner возвращает nonzero. `ok` smoke не означает готовность кейса, полезность агента или human/native acceptance.

## Переносимость checkout и TEMP

Файлы кейсов содержат byte-level hashes sources/render/journals. `.gitattributes` задаёт `/projects/** -text`: Git сохраняет исходные байты независимо от `core.autocrlf` и ОС. Два synthetic demo содержат исторические generated Markdown с CRLF, соответствующие существующим manifest; исходные bytes сохранены в Git, manifests/gates не переписывались. Новые файлы сохраняют те окончания строк, которые записал штатный writer. Не нормализуйте сохранённый кейс и не регенерируйте hashes ради прохождения CI. Regression `test_demo_checkout.py` экспортирует реальные Git index bytes и проверяет оба autocrlf режима с точными source/render hashes.

На Windows runner системный TEMP может иметь ancestor alias/short name (`RUNNER~1`). `confined` сравнивает resolved child с resolved root, сохраняя отдельный запрет symlink/junction на самом выбранном root и внутри него. Это разрешает системный alias выше root, сохраняя confinement, запрет traversal и existing link checks. Regression `test_store_paths.py` моделирует такой alias и проверяет сохранность отказов. Workspace tests сравнивают возвращённый canonical path с resolved expected path; privacy test читает доверенный role oracle как bytes, сохраняя CRLF так же, как service.

CI/demo/release явно задают `PYTHONUTF8=1`. На Windows Python3.12 системная code page может не представлять кириллицу из `psa resume` при pipe capture; UTF-8 mode наследуется дочерними CLI и делает execution encoding одинаковой на runners. Это настройка test/build environment, а не разрешение на изменение содержимого кейса. Required checks, strict evidence policy и негативные security assertions сохранены.

## Дистрибутив

Release job переиспользует CI/demo, собирает wheel/sdist/archive и проверяет установку вне исходников. PostgreSQL, Alembic и Docker больше не входят в runtime/package/required checks. Состояние локального прогона фиксируется в reports; remote Actions и реальные IDE проверяются отдельно.
