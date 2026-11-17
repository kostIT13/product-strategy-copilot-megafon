# P7c — versioned research-tool registry

17.11.2026 20:46 (Asia/Novosibirsk, UTC+7).

## Сделано

Добавлены typed schema и registry1.0.0 восьми существующих research capabilities: local import, public fetch, current literal search, instruction context, research draft record, validate, verify, coverage. Каждая декларация содержит descriptor/implementation contract, CLI/MCP entrypoints, permissions, provenance, limits/scope/enforcement, offline fallback, сценарий выбора/исключения и честный evaluation status.

RegistryService не получает case/path/URL и не выполняет probes/dispatch. Новые `psa tools list`, `psa tools describe TOOL-ID` и `psa_research_tools` читают общий in-package каталог. Availability/provenance freshness=not_checked; authorization/execution/approval/native activation=false; provider_cost=null. Registry не является runtime ACL/enforcement и не предоставляет разрешение на описанные writes/network. Legacy checks не получили выдуманного aggregate cap; fetch deadline не выдан за watchdog. P7b token candidate исключён из registry и production search сохранён.

Модули разделены: domain schema/shipped descriptions, application read-only service, CLI adapter и MCP adapter. Нет файлового provider loader, нового runtime dependency, SQL/Docker/model loop или собственного dispatcher. [Runbook](../docs/research-tool-registry.md).

Канон README/workflow/research skill актуализирован; bundle1.1.2,9 adapters пересобраны. Role profiles/knowledge1.0.0 и saved receipts/кейсы не переписывались. Skill-creator применён для узкого обновления существующей research skill, без субагентов/native activation.

Коммиты: `468ef88` domain/service; `c0325ae` CLI/MCP/tests; `a07a8f2` canon/adapters. Итоговый documentation commit включает планы и этот отчёт.

## Проверка

- Registry7 tests OK,10.569s: отказ forged IDs/authorization, no case/catalog I/O/network/process dispatch, returned JSON isolation, limits к existing constants, CLI route/provenance paths, CLI из unrelated cwd с optional-import guard, реальные CLI/FastMCP stdio parity/annotations/existing MCP names. Stdio cwd выбран вне временного sentinel folder, чтобы lifecycle дочернего процесса не удерживал Windows temporary directory при cleanup.
- Context10 tests OK,5.062s: stage selection, hashes/navigation, legacy manifests, copy и adapter drift.
- Итого17 различных targeted tests OK. Clean base повтор registry7,1.736s:6 passed/1 expected MCP skip, optional model/parser/MCP extras не требуются CLI.
- Skill validator2 UTF-8 OK для canonical/generated research skill; harness write/check9 без drift, Ruff/docs256/diff и native Gitleaks history/tree/negative probes OK для итогового tracked export.

Full suite, release build и native IDE acceptance не повторялись. Последний ранее завершённый зелёный remote CI относится к179640d; push этой итерации запускает новую matrix, его нельзя заранее объявлять зелёным. Модели, внешние research fetch и роли не исполнялись; product case/gate/decision не создавались. Версии деклараций и evidence_refs — maintained metadata, не independently verified runtime provenance.

## Что дальше

P7c завершён в заявленном scope. P7d — offline сценарии research-пути и сверка оставшихся criteria P7 перед P8/R5. Польза всех инструментов не измерена, synthetic search baseline не заменяет независимую оценку IDE-агента. Весь P7, P4/P5/P6/R1/M6/M8 остаются открытыми.
