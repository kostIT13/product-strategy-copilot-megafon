# Документация, секреты и демо в CI — 8 ноября 2026, 16:51 (Asia/Novosibirsk)

Продолжен раздел 14.1 основного плана, ветка feature/main-solution-roadmap. Длительность отдельно не замерялась.

## Что добавлено

- В ci.yml введены docs и secrets jobs с теми же pinned checkout/setup-uv и read-only permissions. Secrets job получает полный checkout fetch-depth: 0.
- scripts/ci/docs.py: CommonMark parser для tracked Markdown, локальных inline/reference/image links, heading/explicit anchors, duplicate headings и обязательных файлов. Внешние URL не запрашиваются. Markdown-it-py явно добавлен в dev-группу; uv.lock обновлён, остаётся 119 packages.
- Исправлены пять старых битых ссылок: инструкция пересмотра источников в diagrams/mvp/README.md; ссылки между архивными plan-1/3/4 и specs/case.md. Ссылки внутри fenced code не проверяются как действующие.
- scripts/ci/repository.py: запрет tracked .env/runtime-файлов в текущем индексе и истории, включая удалённые; .env.example разрешён. Полнота checkout проверяется явно, shallow history не принимается.
- scripts/ci/secrets.py: Gitleaks CLI 8.30.1 в официальном ghcr.io/gitleaks/gitleaks образе, закреплённом на sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f. Подтверждены registry digest и версия CLI. Первоначальная загрузка binary release дважды вернула HTTP 504, поэтому использован официальный контейнер, без стороннего Actions wrapper.
- Gitleaks сканирует всю доступную историю и экспорт tracked/неигнорируемых новых файлов. Игнорируемые личные .env/.venv/backups не читаются. Контейнеры сканирования работают --network none, с read-only source mount и --redact=100. Вывод ограничен RuleID/File/StartLine/Commit; сырой scanner output и matched secrets не публикуются. Нет blanket allowlist/baseline. Загрузка Docker image требует сети, сам scan не требует.
- Контрольные пробы Gitleaks генерируют искусственный access-key-shaped token во временном Git repo: чистый каталог проходит, текущий token обнаруживается, удалённый token остаётся обнаружимым в истории. Фикстура не содержит реальной авторизации и не коммитится в основной репозиторий.
- demo.yml устанавливает только базовый пакет, запускает scripts/ci/demo.py и показывает JSON в job summary. Demo/table-demo проверяются в временных копиях: строгий verify (warnings запрещены), coverage и реальные validate/verify/coverage/resume CLI; read-only hashes неизменны, render повторно валидируется. Оригиналы projects/ не изменяются; БД и внешняя модель не нужны. Это local artifact replay, не общий engine записанных модельных ответов.
- Добавлены шесть содержательных unit-тестов CI: reference links/fences/Unicode duplicate anchors; broken targets/anchors/path escape/required files; runtime path policy; удалённый .env в Git-истории; сохранность оригинального demo corpus; неверная цитата и неподдерживаемый locator. Последние проверки утверждают конкретные причины отказа, включая случай warning при успешном обычном verify.

## Результаты

- Полный набор: 146 unit-тестов на Windows/Python 3.12 — OK. Ruff и git diff --check — OK; YAML обоих workflows разобран.
- Docs: итоговый check охватил 94 tracked Markdown документа, включая этот отчёт, ошибок нет.
- Repository/history policy — OK. Gitleaks: 0 находок в истории, 0 в рабочем экспорте; положительные/отрицательные контрольные пробы прошли.
- Demo на Python 3.12 и отдельно в минимальном Python 3.11.15 окружении без extras/dev — OK. Demo: 1 проверенная цитата, 9 covered paragraphs; table-demo: 1 цитата, 5 paragraphs. Read-only файлы и оригиналы неизменны, render revalidated, model_calls=0.
- Исправлена локальная проблема кодировки Windows в захвате CLI-вывода: runner захватывает байты, не декодируя неизвестную console encoding. Итоговый прогон без UnicodeDecodeError.
- Личный .env и рабочая БД не изменялись; живые LLM-запросы не выполнялись. Полный PostgreSQL smoke повторно не запускался, прикладное ядро/миграции не менялись.

## Ограничения и следующий срез

Удалённый результат Actions ещё не подтверждён: ранее API без авторизации возвращал 404; это не считается зелёным прогоном. Secret scanning эвристический и не гарантирует отсутствие любого секрета. Docs check не проверяет внешние сайты или полное соответствие всех GitHub rendering edge cases. Демо подтверждает техническую воспроизводимость синтетического материала, не рыночное качество стратегий и не отложенные M6/M8 приёмки.

Следующая инфраструктурная работа: release archive/wheel/sdist, установка из архива и Docker build smoke. Instruction-sync вводится вместе с AGENTS.md/IDE-адаптерами. Продуктовый следующий срез — проверенные варианты и человеческий выбор — сохранён в roadmap. Планы, README и docs/continuous-integration.md обновлены.
