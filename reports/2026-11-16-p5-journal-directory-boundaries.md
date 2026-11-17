# P5b — bounded directory/path boundaries журналов

Дата: 16.11.2026 17:30 (Asia/Novosibirsk). Ветка feature/main-solution-roadmap.

## Результат

Закрыт общий пробел task/hook/host/config stores: лимит истории раньше проверялся после materialization всего directory listing. Новый отдельный persistence helper использует os.scandir, прекращает обход на первой лишней записи, закрывает iterator и не возвращает усечённый успешный результат. Новая публикация учитывает место для записи заранее; существующие лимиты и history retention сохранены.

Confinement проверяется для каждого найденного пути до skip/ignore, включая final-looking records и ACTIVE. Реальные symlinks/junctions внутри/вне выбранного корня отклоняются. Bounded scan применён также к config audit operation entries и interrupted snapshots. CLI/FastMCP продолжают использовать прежние services; contracts, published schemas, gates и native activation не изменены.

Добавлен [runbook](../docs/journal-directory-boundaries.md); основной план, roadmap, production-план и README отражают P5b как завершённый ограниченный срез. Далее P5c — journal version compatibility/upgrade. P5 целиком и отложенный P4 не закрыты.

## Проверки

- Новые directory boundaries4,8.682 s,OK. Управляемый lazy iterator до1млн потенциальных entries реально посещает только1001 (1002 с ignored ACTIVE); точный предел и закрытие iterator проверены. Все пять pending adapters отказывают до чтения records. Реальные Windows junctions final-looking/ignored/internal/external проверены без skip, внешний sentinel сохранён.
- Task journal12,33.040 s,OK; hook runs11,55.778 s,OK; host acceptance/reviews/config/profiles43,53.303 s,OK. Regression включает process termination/copy recovery и реальный CLI/FastMCP stdio replay/parity. Три suite выполнялись независимо, это не измерение производительности production.
- Итого70 разных целевых tests. Полный suite репозитория не запускался.
- Чистая base-установка без MCP/LiteLLM: новые4,9.456 s,OK; base completed/copy/resume/reopen/reapprove smoke OK,sql_dependencies=false,model_calls=0.
- Ruff, sync9, tracked Markdown links, git diff checks и native Gitleaks history/tree/negative probes проверены перед push.

## Коммиты

4ce57e2 — streaming enumeration и adoption в task/hook/host observation/review stores.
f8a4915 — config pending/audit/snapshot bounds и corpus negative path/resource tests.
Итоговый docs commit фиксирует планы/runbook/этот отчёт.

## Ограничения

Это bounded enumeration, не wall-clock timeout файловой системы и не полный integrity audit всех final records. Будущие namespaces/schema и общий upgrade/rollback остаются P5c; остальные privacy/injection/dependency сценарии не объявлены закрытыми. Path TOCTOU вне participating locks, hardlinks, power-loss/NAS и другие ОС этим Windows-прогоном не удостоверены.

Работа выполнена на коде и временных synthetic fixtures. Реальные IDE configs, рабочие кейсы, .env и БД/volumes не менялись; native subagents/hooks не активированы, внешние модели не вызывались. Приватные данные не коммитились. Live P4, R1/M6/M8 остаются открытыми.
