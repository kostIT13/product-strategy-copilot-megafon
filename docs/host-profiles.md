# P4a: матрица хостов и план последовательного fallback

Первый срез [P4](solution_plans/production-readiness.md): read-only каталог и план запуска. Native adapters, activation/config migration и фактическая приёмка IDE ещё не реализованы. Предыдущие R1/M6/M8 остаются открытыми; пользовательское откладывание live IDE проверки сохраняется.

## Версионированный каталог

`agent/hosts/catalog.json` schema1/catalog1.0.0 содержит Codex, Cursor, Claude Code, Qwen Code и SourceCraft. Для каждого перечислены существующие instruction surfaces репозитория и восемь областей: instruction_loading, skill_discovery, mcp_stdio, subagents, hooks, isolation, budget_enforcement, cancellation.

Все native capabilities имеют **not_verified**. Это отсутствие подтверждённой приёмки нашего решения, а не заявление об отсутствии возможности у производителя. Наличие AGENTS.md/generated files и успешный stdio-клиент не доказывают загрузку правил или native работу в IDE. Новых утверждений о vendor APIs/актуальных форматах конфигураций этот срез не делает; перед конкретным adapter нужна отдельная сверка официальной документации и установленной версии.

Schema1 намеренно не принимает manually inserted verified/permissions/commands. Нельзя включить native функцию изменением строки статуса. Будущая запись фактических capabilities требует отдельного протокола evidence и версий; неизвестная schema или повреждённый catalog отклоняется без молчаливой миграции/активации.

Каталог входит в canon digest sync_harness. При изменении выполнить `python scripts/sync_harness.py --write`, затем --check; generated adapters не редактировать вручную. Host catalog не подмешивается автоматически в продуктовый case context. Release allowlist и существующий recursive agent JSON packaging включают его без изменения старого release manifest protocol.

## CLI

```powershell
psa host list --instructions-root .
psa host inspect codex --instructions-root .
psa host plan --request host-plan.json --instructions-root .
```

Пример host-plan.json (версия в примере синтетическая):

```json
{
  "schema_version": 1,
  "host_id": "codex",
  "host_version": "synthetic-host-1.2.3",
  "platform": "windows",
  "feature": "subagents",
  "mode": "native"
}
```

Допустимые platform: windows/linux/macos; feature: mcp_stdio/subagents/hooks; mode: sequential/native. Версия обязательна, является заявленным caller контекстом, не результатом probe. Plan содержит request_fingerprint, catalog version/SHA-256, hashes реально присутствующих instruction files и исходную версию/ОС. Присутствие файла помечается отдельно от host_loading_verified=false.

Native request возвращает **fallback_required**, proposed_mode=sequential, native_activation_allowed=false; CLI code1. Explicit sequential request даёт ready/code0 только для подготовленного предложения. Ни одна ветка не начинает исполнение: execution_started/configuration_written/external_transfer_authorized/human_approval_granted=false. Ready не означает, что host был запущен/проверен или функция активирована.

Fallback предлагает явно прочитать AGENTS.md/agent/README.md и для **уже выбранного** кейса использовать status/resume/context. ID — placeholder, не автоматически созданный кейс. Основной IDE-агент продолжает последовательный workflow по канону; human gates, consent и ограничения источников сохраняются. План не отправляет материалы внешнему провайдеру и не вызывает субагентов/хуки.

## FastMCP и границы

Read-only tools: `psa_host_matrix(instructions_root)`, `psa_host_profile(host_id, instructions_root)`, `psa_plan_host(request, instructions_root)`. MCP caller проверяет status=fallback_required независимо от transport success. CLI/настоящий stdio возвращают одинаковые packets; повреждённые/неизвестные fields, duplicate keys и requests больше64k отклоняются без отражения input values.

Файловый reader ограничивает catalog32k и instruction file64k, запрещает traversal/symlinks/junctions через общий confined. Корень инструкций — явная доверенная конфигурация caller, не поле источника/продуктового кейса. Сервисы не читают установленные IDE, пользовательские/global settings, .env или рабочие кейсы и не записывают native configs. Catalog hash/файловые hashes проверяют bytes, не удостоверяют автора/host behavior.

[P4b evidence-bound observations](host-observations.md) реализован: capture отчётов с unverified status и отдельным review. P4 ещё открыт: далее review/adoption и previews конкретных host configs с явным включением/отключением/миграцией. Реальную activation можно предлагать только после проверки возможностей нужной версии/ОС; при отсутствии evidence сохраняется CLI/manual fallback. Эти дальнейшие шаги не закрываются unit tests P4a.
