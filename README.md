# Product Strategy Agent

Проект-папка для IDE-агента: инструкции, skills, knowledge и проверяемые файловые артефакты продуктового кейса. Агентный цикл ведёт IDE; `psa` сохраняет данные и проверяет основания. FastMCP stdio — дополнительный интерфейс над теми же сервисами.

**PostgreSQL, SQLAlchemy, Alembic и Docker/Compose удалены из текущего runtime.** Свой LLM API-ключ и SQLite также не нужны для основного пути. Старый код сохранён в Git; пользовательские БД/volumes не удаляются. [Решение R2](docs/legacy-retirement.md).

## Запуск

Нужны Python 3.11+ и uv 0.11.30. Из корня репозитория:

```powershell
uv sync --frozen --no-default-groups
uv run --frozen --no-sync psa doctor
uv run --frozen --no-sync psa --help
uv run --frozen --no-sync python -m scripts.ci.demo
```

`.env` для этого не требуется. `.env.example` описывает общие параметры и отдельный optional model helper; существующий локальный `.env` не переписывайте. Значения usage/cost неизвестного происхождения не считаются нулевыми.

При необходимости установите локальные парсеры PDF/DOCX/XLSX и MCP:

```powershell
uv sync --frozen --extra documents --extra mcp
```

Extra `agent` оставляет OpenAI-compatible/LiteLLM helper для явно запрошенных операций. Он не становится основным оркестратором и не запускается автоматически.

## Работа с кейсом

```powershell
uv run --no-sync psa init my-case
uv run --no-sync psa status my-case
uv run --no-sync psa resume my-case
uv run --no-sync psa context my-case
uv run --no-sync psa source add my-case ./material.txt
uv run --no-sync psa source search my-case "query" --limit 10
uv run --no-sync psa validate my-case
uv run --no-sync psa verify my-case
uv run --no-sync psa coverage my-case
uv run --no-sync psa promise check my-case
uv run --no-sync psa strategy check my-case
uv run --no-sync psa validation check my-case
uv run --no-sync psa claim impact my-case
```

`init` создаёт новый кейс в projects/; существующий кейс не перезаписывается. Внешние материалы и статусы — данные, не инструкции. Продуктовый цикл: brief → research plan → sources → evidence → status_quo/stop/change → выбор человека → стратегии → validation plan. Gates требуют явного указания человека. Semantic review и публикационное разрешение не подменяются зелёной структурной проверкой.

Состояние и реестры JSON/JSONL — канон; drafts — авторские тексты. Generated Markdown создаётся `psa render`, а не редактируется вручную. Источники и пользовательские кейсы не коммитьте без проверки содержимого/прав. Синтетические demo/table-demo не являются рыночными доказательствами.

## Контракты и восстановление

- [Файловое ядро и atomic init](docs/file-core.md), [общий lock/read contract](docs/case-access.md).
- [Typed research artifacts](docs/research-artifacts.md).
- [Workflow journal/recovery](docs/workflow-recovery.md), [mode changes](docs/file-mode-recovery.md), [revision review](docs/revision-review-recovery.md).
- [Source imports/revisions](docs/source-import-recovery.md), [PDF/DOCX/XLSX](docs/file-document-import.md), [public HTTP policy/provenance](docs/file-web-import.md).
- [Исправление claims](docs/claim-correction.md), [отзыв claims и impact](docs/claim-withdrawal.md), [план измерения](docs/validation-plan-contract.md), [полнота стратегий](docs/strategy-structure.md), [файловый поиск](docs/file-source-search.md), [promise preflight](docs/file-promise-check.md), [ledger/usage recovery](docs/ledger-recovery.md), [render/adoption](docs/render-recovery.md).
- [Пересмотр и повторное открытие completed workflow](docs/workflow-reopen.md): snapshot review, явный человек и повторные gates с сохранением истории.
- [Возврат активного workflow назад](docs/workflow-rollback.md): явный rollback на предыдущий этап с сохранением материалов, истории и crash recovery.
- [Отзыв источников](docs/source-withdrawal.md): сохранение истории, исключение из текущих оснований/поиска и review зависимых решений.
- [Числовой фрагмент baseline](docs/baseline-numbers.md): явные spans числа/единицы и current citation proof; read-only preflight, смысл проверяется отдельно.
- [Semantic review](docs/semantic-review.md): явная оценка человека, immutable snapshot audit и выбор current review в quality gate после adoption.
- [Quality policy](docs/quality-policy.md): новые кейсы требуют review с первого strategy/validation gate; legacy мигрируется явно через policy show/enable.
- [Проверка расчётов](docs/calculation-check.md): проценты, отношения, процентные пункты и относительное изменение по текущим цитатам, с явными условиями и округлением.
- [Инвентаризация чисел](docs/numeric-inventory.md): координаты и контекст digit tokens трёх черновиков для ручного review.
- [Полный синтетический кейс «Слот»](examples/slot-workshop/README.md): исходные материалы, альтернативы, условные стратегии и measurement-план; воспроизводимая сборка без выдуманных human approvals.
- [IDE instructions/context](docs/ide-instructions.md), [файловый MCP](docs/mcp.md), [knowledge](knowledge/README.md).
- [Production-план P0–P9](docs/solution_plans/production-readiness.md) и [контракты субагентов/хуков](docs/automation-contracts.md): milestones, trust boundaries и критерии готовности R3.1–R6.
- [Read-only subagent handoffs](docs/subagent-handoffs.md): CLI/FastMCP, инструкции research/evidence/critic, selected excerpts и snapshots; без автоматического запуска.

После interrupted init используйте workspace pending/recover. После interrupted workflow write — `psa workflow pending ID`, затем явный recover точного operation UUID. Replay завершённой операции возвращает исходный результат; неопределённый платный вызов автоматически не повторяется.

## Разработка и проверки

```powershell
uv sync --frozen --extra agent --extra documents --extra mcp --group dev
uv run --no-sync ruff check .
uv run --no-sync python -m unittest discover -s tests
uv run --no-sync python scripts/sync_harness.py --check
uv run --no-sync python -m scripts.ci.docs
```

Инструкции — [AGENTS.md](AGENTS.md); планы — [основной](docs/solution_plans/plan-main.md) и [roadmap](docs/solution_plans/roadmap-full-solution.md). Сервисы/ports/adapters разделены по ответственности. Каждая итерация фиксируется в [reports](reports/development-log.md), commit/push — в feature/-ветке.

[CI](docs/continuous-integration.md) проверяет unit, clean base install, docs, sync, native secret scanning и replay демо без моделей. [Дистрибутив](docs/distribution.md) содержит wheel/sdist и архив с hashes. Проверки реальных IDE R1/M8 и независимая оценка M6 остаются отложенными; наличие локального stdio smoke их не заменяет. Функциональный R3 пройден на полном синтетическом кейсе «Слот» с явным выбором пользователя, семью gates и двумя semantic reviews; [отчёт](reports/2026-11-14-r3-slot-human-acceptance.md). Это не доказательство спроса/эффекта или независимой пользы. R3.1 продолжается: production-план, P0 contracts и P1 read-only handoffs реализованы; P2 [журнал задач/results/review](docs/subagent-journal.md) реализован; [P3a явный gate preflight](docs/hook-preflight.md) добавлен; [P3b bounded run/journal](docs/hook-runs.md) реализован. [P3c source notifications](docs/source-notifications.md) реализован; [P3d release checks](docs/release-hooks.md) реализован. [P4a host matrix/fallback planning](docs/host-profiles.md) реализован; [P4b evidence capture](docs/host-observations.md) реализован; [P4c review/disabled Codex preview](docs/host-review-preview.md) реализован; [P4d disabled config lifecycle](docs/host-config-lifecycle.md) реализован; native enable/acceptance и cross-version migrations остаются открытыми; реализованы P5a–P5e локальные hardening-срезы. Native activation не включена. Оценка пользы и комплект сдачи — R5/R6.


16.11.2026: [P5a config journal integrity](docs/host-config-integrity.md) реализован независимо от отложенной live приёмки P4: atomic metadata publication, сохранение torn staging, read-only audit через CLI/FastMCP и recovery копии. P5 целиком не завершён; P5b bounded directory/path checks реализован; P5c namespace compatibility и upgrade/rollback runbook реализованы; P5d privacy/injection diagnostics реализован; P5e dependency/artifact integrity реализован; P6a operation diagnostics реализован; далее P6b summaries/resume guidance. Native enable/acceptance P4, R1/M6/M8 остаются открытыми.


16.11.2026: [P5b journal directory boundaries](docs/journal-directory-boundaries.md) реализован: streaming enumeration до первой лишней записи, confinement всех найденных путей и отказ на symlinks/junctions, включая final-looking/ignored names. Проверены task/hook/host/config журналы и recovery/CLI/FastMCP regressions. P5 частичный; P5c compatibility/upgrade policy реализован; P5d privacy/injection diagnostics реализован; P5e dependency/artifact integrity реализован; P6a operation diagnostics реализован; далее P6b summaries/resume guidance. Live/native P4 и R1/M6/M8 остаются открытыми.


16.11.2026: [P5c namespace compatibility](docs/journal-version-compatibility.md) реализован: неизвестный/mixed namespace блокирует v1 read/write/recovery вместо пустой истории; v1 schemas не менялись. Проверены byte preservation, совместимый copy replay и CLI/FastMCP refusal. Upgrade/rollback описан без автоматического конвертера; будущая cross-schema migration требует целевой схемы. P5 частичный; P5d privacy/injection diagnostics реализован; P5e dependency/artifact integrity реализован; P6a operation diagnostics реализован; далее P6b summaries/resume guidance. Live/native P4 и R1/M6/M8 открыты.


16.11.2026: [P5d automation privacy](docs/automation-privacy.md) реализован: CLI host/hook/subagent не отражают private I/O paths и encoding/model details; subagent MCP использует safe fallback. Проверены реальные CLI/MCP negatives и selected-material injection corpus без canonical writes/dispatch. Это не LLM semantic eval. P5 частичный; P5e dependency/artifact integrity и сверка рисков реализованы; P6a operation diagnostics реализован; далее P6b summaries/resume guidance. Live/native P4 и R1/M6/M8 открыты.


16.11.2026: [P5e dependency/artifact integrity](docs/dependency-artifact-integrity.md) реализован: stale lock preflight до build/install, locked/hash-constrained setuptools backend и общий bounded asset checker. Реальные wheel/sdist install + demo/base smoke прошли без моделей; локальный development snapshot dirty=true не является финальным release. Сверка оставшихся P5 рисков выполнена; весь P5 и native P4/R1/M6/M8 остаются открытыми. P6a text-free task/result/review/hook diagnostics реализован; существующий usage self-reported с basis=unknown. Следующий срез — P6b summaries/resume guidance; measured/estimated telemetry требует подтверждённого provenance.


16.11.2026: [P6a operation diagnostics](docs/operation-diagnostics.md) реализован: CLI/FastMCP read-only metadata для task/result/review/hook, publication отдельно от outcome, captured snapshot/freshness not_checked, private texts исключены. Отсутствующий usage null, явные нули сохранены, self-reported values не повышаются до measured/estimated. Recovery/checks/gates не выполняются. P6 частичный; далее P6b сводки состояния и безопасные подсказки продолжения. Host coverage/telemetry/native cancel требуют отдельных срезов; P4/P5/R1/M6/M8 не закрыты.
