# P6d — advisory retry/cancel/resume policy

Дата: 17.11.2026 01:59 (Asia/Novosibirsk). Ветка feature/main-solution-roadmap.

## Реализовано

- Новый pure domain policy поверх P6a diagnostic: существующие CLI mechanisms отделены от применимости выбранного operation и от authorization. Inspect/case status resume read-only; generic cancel и agent checkpoint resume not_supported_by_cli. Native host controls not_verified/not_assessed, не выводятся из stored outcomes или имени IDE.
- Pending task/result/review recovery публикует captured artifact; hook execution_unknown recovery фиксирует interrupted без исполнения; valid prepared hook completion публикуется без rerun. Already published recovery not_applicable; exact UUID replay возвращает history. Консервативный новый attempt использует новый request/UUID, fresh binding/permissions и явную инструкцию; reported budget_exceeded требует разбора заявленного превышения.
- Policy read-only/advisory, не write enforcement/ACL/CAS token: authorization_evaluated/granted=false, actions_executed/gate/native flags false. Existing validators и human gates не менялись. Наличие старой явной инструкции не требует повторного согласия из-за policy.
- CLI diagnostics controls и FastMCP psa_operation_controls имеют общее ядро; родительские исходники/role guidance для freshness не перечитываются. Corrupt/unknown namespace/busy/pending canonical guard дают прежний отказ, не phantom capability.
- Канон/resume skill обновлены вместе с CLI/MCP, bundle1.1.1 и9 generated adapters пересобраны; profiles/journal schemas остались прежними. [Контракт и сверка P6](../docs/operation-controls.md) описывает локальные результаты и открытые native/telemetry части. Локальные P6a–P6d выполнены, весь P6 не закрыт; далее независимый P7a inventory/eval до расширений.

## Проверки

Final controls core/CLI/real-stdio8,17.062 s,OK: distinct task/result/review/hook mechanisms, same-ID replay/new attempt, pending-policy recheck после explicit recovery, hook interruption/prepared completion без rerun, reported cancelled/budget не повышают native controls, реальные psa resume byte preservation и CLI/MCP parity, corrupt private input без partial output/echo.

P6a8,19.408 s,OK; P6b8,14.908 s,OK; instruction context10,5.388 s,OK. Итого34 разных целевых tests. Clean base controls8,10.245 s,OK (1 ожидаемый stdio skip). Full repository suite/base completed smoke/hook worker execution suites не повторялись: writers/worker/enforcement не менялись, связь с actual forward recovery проверена в новом corpus на temp fixtures.

Resume canonical/generated skills прошли quick_validate в UTF-8 режиме. Sync9/Ruff/tracked Markdown links/git diff checks и native Gitleaks8.30.1 history/tree/negative probes проверены перед push. Runtime dependencies/uv.lock не менялись.

## Коммиты и границы

dbedee4 — pure CLI capability policy/service и semantic tests.
bbdee60 — CLI/FastMCP endpoint и read-only parity/privacy tests.
7c45fa6 — canonical bundle1.1.1/resume skill/adapters и runbook.
Итоговый docs commit фиксирует планы и timestamp отчёт.

Policy относится к CLI journal controls, не проверяет установленную IDE/версию/активные PIDs и не отменяет/не возобновляет их. Fixed hook timeout — только existing owned worker deadline. Binding hashes описывают прочитанный historical record, freshness not_checked; перед реальным действием остаются current guards/permissions. Новая policy не принимается writer-ами как authorization token и не обходит human choice. Native control/cancel/checkpoint integration и independently verified telemetry остаются открытыми.

Все mutations/explicit recovery в тестах только temp synthetic fixtures. Реальные cases/IDE configs/.env/БД/volumes не менялись, модели/native subagents/hooks не активировались, private working data не коммитились. P4/P5/P6 native acceptance и R1/M6/M8 остаются открытыми; RAG/provider в P7 условны до измеримой пользы.
