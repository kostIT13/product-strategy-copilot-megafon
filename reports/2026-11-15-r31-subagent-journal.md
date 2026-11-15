# R3.1/P2 — изолированный журнал субагентов

Завершено 15.11.2026 17:54 (Asia/Novosibirsk). Разработка репозитория, без изменений рабочих продуктовых кейсов.

## Сделано

- TaskRegistration, ResultRegistration, ReviewRegistration и общий файловый store/service: schema, parent hashes, exact task/result binding, reported budgets, UUID conflicts и immutable historical replay.
- Опциональная явная регистрация handoff и результатов: первичная оценка основным агентом не заменяет human semantic review, claim adoption или gate. Ready требует current completed result и валидных finding indices; stale rejection разрешён.
- Изолированные records внутри уже исключённого `.psa/workflow/subagents/v1`; существующие workflow input hashes и human review proofs не меняются. Новый глобальный snapshot exclusion не добавлялся.
- Shared case lock, bounded writes, pending/fsync/atomic publication, явное recovery захваченного record. Незавершённый UUID не перезаписывается; corrupt/foreign bytes не удаляются. Recovery не запускает исполнение и не удостоверяет текущую актуальность.
- CLI register/record-result/review-result/task/result/review/pending/recover и восемь FastMCP tools над общими services. P1 prepare остаётся stateless/read-only.
- [Runbook](../docs/subagent-journal.md), README, MCP docs и планы обновлены: P0–P2 implemented, далее P3 local hooks.

## Проверки

- P2: 12 tests, 33.001 s, OK. Включены CLI/настоящий FastMCP stdio, шесть принудительных остановок subprocess (task/result/review × prepared/committed), восстановление копии, сохранность последующих canonical writes, human semantic-review isolation, stale/conflict/binding/budget/partial negatives.
- P1 regression: 14 tests, 13.995 s, OK; P0 contracts: 12 tests, 0.018 s, OK. Итого 38 целевых tests с optional MCP установленным.
- Чистая base-установка без MCP/LiteLLM: 12 tests, 26.607 s, OK (1 ожидаемый MCP-extra skip). Base smoke completed/copy/resume/reopen/reapprove: OK, model_calls=0, sql_dependencies=false.
- Ruff, sync harness (9 managed files), tracked Markdown links, git diff checks — OK. Native Gitleaks 8.30.1: history/tree clean, negative probes прошли.
- Полный suite всех модулей не повторялся: проверены изменённые интерфейсы/механизмы и прежний сквозной путь. Первый sandbox запуск временных fixtures упёрся в WinError 5; успешные тесты выше повторены с разрешённым доступом к temp.

## Коммиты и ограничения

`c639c25` — domain/store/service; `a8cd37f` — CLI/FastMCP/parity; `077f2e4` — crash/copy/semantic isolation. Заключительный docs commit фиксирует этот отчёт и планы.

Записи атрибуции/usage не удостоверяют личность или реальное исполнение. Result assessment не агрегирует reviews; canonical adoption всегда false. Проверено прерывание процесса на локальной FS, без обещания power-loss/NAS durability. Native dispatch/cancel/enforcement и host acceptance ещё не реализованы. Субагенты/хуки/модели не запускались; тесты исполняли только локальные фикстуры и MCP server. Пользовательские БД/volumes/.env и рабочие данные не изменялись. R1/M6/M8 открыты. Следующий шаг — P3 локальные allowlisted hooks, затем P4 host adapters.
