# Базовое knowledge/ — 8 ноября 2026, 22:46 (Asia/Novosibirsk)

Выполнено базовое наполнение этапа 5, ветка feature/main-solution-roadmap. Длительность отдельно не замерялась.

## Содержание

- knowledge/README.md: назначение, навигация по ID@version, правила ручного применения/обновления и явный статус not connected.
- knowledge/methods/: segmentation.md, alternatives.md, experiments.md — адаптации для segment/value hypotheses, качественного сравнения вариантов и проверки критических допущений.
- knowledge/checklists/: evidence.md, critic.md, strategy.md — собственные рабочие списки reviewer по действующим контрактам. Они не создают новые gates/approvals.
- knowledge/sources.md и catalog.json: 4 внешних первичных источника, 4 внутренних основания, 6 материалов версии 1.0.0; авторство/происхождение, дата проверки, применимость и ограничения каждого. Внешние адаптации отделены от внутренних эвристик.

Первичные страницы проверены 08.11.2026: Christensen Institute JTBD, GOV.UK Learning about users and their needs, HM Treasury/Government Finance Function Green Book 2026, Alex Osterwalder/Strategyzer Test Card. Ссылки и границы заимствования находятся в knowledge/sources.md. Для двух динамических страниц фиксированная внешняя версия неизвестна и указана null; дата проверки не означает эмпирической валидации подхода. Полные статьи/PDF/фирменные шаблоны не копировались, примеры написаны как синтетические.

Материалы подчёркивают границы: методика не является evidence кейса; exact quote не доказывает entailment; critic advisory и не гарантирует независимого оценщика; owner self-reported; schema kind=hypothesis не исключает скрытого обещания в тексте; strategy_plan internal-only, публикация не разрешена. Для main options не введены новые обязательные роли, численные рейтинги или придуманные пороги.

## Упаковка и проверки

- Knowledge включено в release ZIP allowlist/required files и MANIFEST.in для sdist; вложенный .env по-прежнему запрещён. Проверка дополнена в существующем distribution test. Docs gate требует README/catalog и проверяет локальные Markdown links.
- Одноразовая проверка catalog.json: корректный JSON, уникальные source/document IDs, известные source references, версии/даты/авторы/непустые applicability/limitations, существующие пути; metadata IDs/version/date/source IDs соответствуют текстам. Результат — OK. Постоянный runtime loader/metadata validator на этой итерации не добавлялся.
- Пять distribution tests и шесть CI-check tests — OK; Ruff и git diff --check — OK. Полный набор 170 core tests повторно не запускался: модельные prompts/сервисы/БД не менялись.
- Отдельный review bundle собран в .venv-ci/knowledge-bundle, dirty=true. ZIP и sdist содержат все 9 knowledge files; это проверка состава, не новый опубликованный release. Предыдущий чистый dist/release архив не заменялся.
- Gitleaks проверил историю/рабочий экспорт без находок, negative probes прошли. Итоговый docs gate проверяет навигацию с новым отчётом перед коммитом. Проверка внешних источников проведена вручную через чтение первичных страниц, не объявляется автоматическим CI monitoring внешних URL.

## Статус плана

Основной план и roadmap отмечают базовое knowledge/1.0.0 как готовое для ручного применения. Этап 5 целиком не закрыт: остаются human approval/export и контроль capability-backed promises. Этап 6 должен реализовать использование зафиксированной версии материалов в agent/skills/IDE и проверить загрузку/parity. Пока файловые материалы не подгружаются в работающий агент, LLM prompts, FTS или RAG; пользователь может вручную ссылаться на ID@version в review_note, но приложение не проверяет версию методики автоматически.

Проверки на реальных кейсах/независимая оценка не проведены, RAG остаётся отдельным отложенным расширением. .env, рабочая БД, canonical records, approvals и модельная конфигурация не менялись; живые LLM-запросы не выполнялись.
