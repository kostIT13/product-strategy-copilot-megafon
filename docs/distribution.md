# Сборка и проверка дистрибутива

Версия Python-пакета в pyproject.toml и src/product_strategy_agent/__init__.py должна совпадать. Теговый workflow принимает только `vX.Y.Z`, точно соответствующий стабильной версии пакета. Сейчас это `v0.1.0`; создание тега — отдельное действие владельца.

## Локальная сборка

Установите uv 0.11.30. Из корня репозитория:

```powershell
uv sync --frozen --group dev
uv run --frozen --no-sync python -m scripts.release.package
uv run --frozen --no-sync python -m scripts.release.verify dist/release/product-strategy-agent-0.1.0.zip
```

Для выпуска используйте `--require-clean --tag v0.1.0` у package. Обычная локальная сборка допускает незакоммиченные правки и явно отмечает dirty=true в манифесте; такой архив не подтверждает конкретный чистый commit. В архив входят только отслеживаемые Git файлы из allowlist: исходники, миграции, инструкции, тесты/CI scripts, документация/диаграммы, сохранённые отчёты и синтетические evals, projects/demo и projects/table-demo. Личные проекты, .env, .git, .venv, backups и volumes не включаются. Игнорируемые локальные данные не читаются. Symlinks запрещены.

Результат в dist/release/: ZIP, wheel, sdist, release-manifest.json и SHA256SUMS. В ZIP есть distributions/ с теми же wheel/sdist. Manifest содержит версию, source commit, dirty flag и SHA-256 каждого файла; SHA256SUMS покрывает внешние assets. Это проверка целостности, не криптографическая подпись автора. ZIP использует фиксированные timestamps, но wheel/sdist и сборочные инструменты не гарантируют побайтово одинаковый результат разных запусков.

Verifier проверяет список файлов и hashes до распаковки, отвергает traversal/symlinks/дубликаты/слишком большой ZIP. Во временном каталоге устанавливает зависимости из lock без проекта, затем по очереди wheel и sdist без editable install. Импорт должен идти из site-packages, doctor/help выполняются вне исходников, оба демо проходят установленным пакетом. Нужна сеть для установки зависимостей/сборочных инструментов; вызовов модели нет. `--python 3.11` позволяет повторить установку на другой поддержанной версии.

## Использование архива

Проверьте SHA256SUMS доверенным локальным инструментом, распакуйте ZIP и перейдите в верхний каталог. Для обычной установки из исходников выполните `uv sync --frozen --no-default-groups`, затем `uv run --frozen --no-sync psa doctor` и `uv run --frozen --no-sync python -m scripts.ci.demo`. Это не требует .env, PostgreSQL и ключа модели. Для основной системы установите extras agent/documents/mcp и отдельно настройте PostgreSQL по README; миграции лежат в alembic/. Git-зависимые проверки CI запускаются из clone, а не из распакованного архива без .git.

## GitHub workflow

release.yml запускается по тегу v* или вручную. Переиспользует ci.yml и demo.yml на том же commit, включая PostgreSQL, секреты и Docker. Только после их успеха собирает и проверяет дистрибутив, сохраняет artifact на 14 дней. Ручной запуск на ветке даёт проверочный artifact. Теговый запуск создаёт только draft GitHub Release; перед созданием сравнивает remote tag commit с проверенным SHA. Публикация остаётся отдельным действием владельца, существующий release не перезаписывается. LLM-секреты не используются; права contents: write выдаются только draft job, который не исполняет код из пакета.

Сборка использует [uv build](https://docs.astral.sh/uv/guides/package/), draft — [GitHub CLI release create](https://cli.github.com/manual/gh_release_create) с --verify-tag/--draft. Checkout/setup-uv/upload-artifact закреплены на проверенные commit SHA.

## Docker smoke

```powershell
uv run --frozen --no-sync python -m scripts.ci.docker_smoke
```

Нужен Docker. Dockerfile закрепляет Python/uv images по digest, устанавливает agent/documents/mcp через frozen uv.lock и запускается от app. Smoke собирает временный image, проверяет doctor, main CLI help, offline Alembic SQL, реальный main FastMCP stdio inventory (14 tools), затем оба demo с read-only fixture mounts. Runtime-контейнеры имеют --network none, --read-only и временный /tmp; БД и API не вызываются. Загрузка образов и зависимостей при build требует сети. Временный тег image удаляется; build cache остаётся для следующих запусков. Это startup/offline проверка, не замена PostgreSQL integration job.
