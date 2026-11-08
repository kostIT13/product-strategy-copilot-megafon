# Релизная сборка и Docker smoke — 8 ноября 2026, 21:33 (Asia/Novosibirsk)

Завершён инфраструктурный срез раздела 14.1. Ветка feature/main-solution-roadmap; код зафиксирован в f038a1e6f2c8f8a73b6fa88f1d617e696d6e9790. Работа начата днём, продолжена вечером после остановки автоматической проверки разрешений из-за лимита использования. Невыполненные тогда команды повторены успешно после продолжения. Длительность отдельно не замерялась.

## Реализация

- scripts/release/package.py строит wheel/sdist и ZIP из Git-tracked allowlist: исходники, миграции, инструкции/CI scripts, тесты, docs/diagrams/specs/reports, synthetic evals и только projects/demo + table-demo. Исключены .git/.env/venv/backups/volumes, сторонние projects, generated cache и symlinks. MANIFEST.in включает миграции и необходимые конфигурационные файлы в sdist.
- Версии pyproject/__init__ и стабильный vX.Y.Z tag должны совпадать; --require-clean блокирует незакоммиченный checkout. ZIP имеет фиксированные timestamps и release-manifest.json с version/commit/dirty/file SHA-256. Внешний SHA256SUMS покрывает ZIP, manifest, wheel и sdist. Полная побайтовая воспроизводимость сборочных инструментов не заявляется; checksums не являются подписью автора.
- scripts/release/verify.py сверяет внешний checksum list, соответствие внешних assets ZIP, список и hashes внутренних файлов; запрещает traversal/duplicate names/symlinks/oversized ZIP. Во временном каталоге ставит frozen зависимости без проекта, по очереди устанавливает wheel и sdist без editable install, подтверждает импорт из venv/site-packages и выполняет doctor/help вне исходников и оба демо установленным пакетом.
- release.yml переиспользует ci/demo на том же commit через workflow_call. После успеха строит/проверяет архив и сохраняет artifact на 14 дней. Ручной запуск ветки только собирает artifact; теговый job проверяет remote tag commit и создаёт draft через gh release create --verify-tag --draft. Existing release не перезаписывается. Contents: write и actions: read выделены только draft job; он не исполняет код дистрибутива. Теги/релизы в этой итерации не создавались.
- Upload-artifact v7.0.2 закреплён на официально проверенный SHA cf430e030ddbb5b0abf93d22962f4752f3646cd9; checkout/setup-uv остаются pinned. Документация: docs/distribution.md и docs/continuous-integration.md.
- Dockerfile использует Python 3.12-slim digest 5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b и официальный uv 0.11.30 digest 93b61e21202b1dab861092748e46bbd6e0e41dd84f59b9174efd2353186e1b47. Runtime extras agent/documents/mcp устанавливаются через uv sync --frozen --no-default-groups --no-editable, пользователь app непривилегированный. Dockerignore теперь исключает .venv* и Ruff cache, поэтому тестовые окружения не попадают в context.
- Новый Docker job и отдельные scripts/ci/docker_smoke.py/container_probe.py: CLI doctor/help, offline Alembic SQL, реальный main FastMCP stdio inventory и два демо с read-only mounts. Контейнеры --network none/--read-only, с временным /tmp; модель/БД не вызываются. Build требует сети для образов/пакетов. Временный тег smoke image удаляется, build cache сохраняется.

## Проверки и артефакт

- Итоговый полный набор: 151 unittest на Python 3.12 — OK; пять новых distribution tests проверяют allowlist, version/tag mismatch, внутренние checksum/unexpected files, ZIP traversal/symlinks и повреждение отдельного внешнего wheel до установки.
- Ruff, git diff --check, локальные Markdown links/required files — OK; три workflow YAML разобраны, проверены workflow_call и изолированные draft permissions. Перед добавлением этого отчёта docs gate проверил 95 Markdown-файлов.
- Docker Linux/Python 3.12.16 smoke — OK: non-root, read-only FS, network none, 9 main MCP tools, offline migration SQL и оба демо (model_calls=0). При вечернем продолжении Docker Engine был выключен; Docker Desktop запущен для итогового скана.
- Финальный ZIP собран с --require-clean --tag v0.1.0 из f038a1e, dirty=false; 342 payload entries плюс manifest, 1 383 928 bytes. Все внешние/внутренние checksums, установка wheel и sdist вне src и два демо — OK. SHA-256 ZIP: 53ad43660af803aa2c7e35b915ccd1b683ccc55b0f3f83bda073fb0fcf1279b9.
- Путь локального артефакта: dist/release/product-strategy-agent-0.1.0.zip; рядом wheel, sdist, release-manifest.json, SHA256SUMS. Dist игнорируется Git. Этот отчёт фиксируется отдельным документационным коммитом после сборки, поэтому source commit ZIP намеренно остаётся f038a1e.
- Итоговый Gitleaks после восстановления Engine — OK: 0 находок в истории и рабочем экспорте, отрицательные пробы прошли, network_during_scan=false.

## Границы и следующий шаг

Личный .env и данные рабочей БД не изменялись; внешняя модель не вызывалась. PostgreSQL integration smoke повторно не запускался: прикладное ядро/миграции не менялись, Docker проверяет offline SQL. Remote GitHub Actions и фактическое создание draft release ещё не подтверждены; никаких claims о зелёном удалённом прогоне/публикации нет. Модельное качество, M6/M8 и независимая оценка остаются открытыми.

Планы/README обновлены. Следующий продуктовый срез — явное сохранение проверенных AI-вариантов и выбор человека; instruction-sync вводится вместе с каноническими IDE-инструкциями, required checks/secret scanning settings требуют отдельной настройки репозитория.
