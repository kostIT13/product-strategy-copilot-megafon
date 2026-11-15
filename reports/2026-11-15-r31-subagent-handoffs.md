# R3.1/P1: завершение read-only subagent handoffs

Начато 14.11.2026, завершено 15.11.2026 17:24 (Asia/Novosibirsk). Ветка feature/main-solution-roadmap. Эта итерация — разработка репозитория, без изменения продуктовых кейсов.

## Результат

Реализованы отдельные HandoffService/port, filesystem readers и domain handoff envelope поверх P0. CLI `psa subagent prepare CASE --request PATH --instructions-root REPO` и FastMCP `psa_prepare_subagent` возвращают один детерминированный read-only пакет с role instructions, selected excerpts, origins, snapshot/task/handoff fingerprints. Canonical profiles research/evidence/critic имеют версии и SHA-256; включены в sync digest девяти generated adapters, без автоматического stage/native запуска.

Под общим case lock читаются только metadata и явно выбранные allowlisted материалы/ranges. Source path/hash/lifecycle проверяются; неизвестный/inactive/withdrawn source отвергается до чтения payload. Полные hashes выбранных файлов связывают snapshot даже при изменении вне excerpt. Selection coordinates и role profile hashes входят в task goal binding: одинаковый текст из другого места и новая инструкция не переиспользуют прежний result.

Строгий JSON request, UTF-8/char/file/packet limits, duplicate/unknown fields и busy/pending guards завершают ошибку без partial output/clipping. Диагностика validation не отражает input values/context; regression проверяет отсутствие тестового secret sentinel. Никакого dispatch, моделей/сети, сохранения задач, canonical writes или human approvals P1 не выполняет. Native integration, реальный budget enforcement и result journal/adoption остаются последующими срезами.

Добавлен docs/subagent-handoffs.md: request example, CLI/MCP, paths/ranges/snapshot scope, роль отдельно от источника, ограничения и последовательный fallback. README, agent navigation, MCP docs и планы обновлены до P1 complete / P2 next. Исторические инструкции/skill adapters пересобраны штатным sync.

## Смысловые коммиты

1. b7939ae — canonical роли и canon sync, включая проверку отсутствия auto-loading.
2. 2bd617d — bounded snapshot/handoff core, readers/port/service и negative tests.
3. 51f54d2 — read-only CLI/FastMCP и real stdio parity.
4. d46a8c4 — сохранённое исправление безопасной диагностики и regression sentinel; при возобновлении коммит сохранён без переписывания.
5. Заключительный docs/report commit фиксирует завершение P1, результаты и следующий этап.

## Проверки 15.11.2026

- Финальный targeted suite: **34 tests, 19.088 s, OK** — P1 core/CLI/real stdio, instruction context/canon sync и P0 contracts.
- Clean base без MCP/model/SQL extras: **14 tests, 7.562 s, OK (skipped=1: MCP extra отсутствует)**; существующий полный файловый workflow completed/reopen/reapprove/copy/resume также прошёл, model_calls=0.
- Негативные случаи: unselected material не читается/не экспортируется, unsafe paths/implicit permissions/duplicate fields, Unicode/CRLF ranges, same text at another offset, changes outside excerpt, role/catalog changes, corrupt/revised/withdrawn/unregistered source, empty/missing guidance, size limits, busy/pending/invalid state, rehashed origin mismatch, invalid CLI request без partial stdout и без sentinel в error.
- Финальные static/secret checks: Ruff/sync9/docs210/repository history, git diff --check и native Gitleaks 8.30.1 history/tree/negative probes — OK.

Прежние yielded sessions после перерыва недоступны, поэтому финальные проверки выполнены заново; потерянный вывод не считается passed. Общий full suite повторно не запускался: новый read-only entrypoint проверен целевыми интеграционными/негативными тестами и существующим base workflow smoke. Реальные host adapters/модельные задачи/хуки не запускались, remote Actions result не подтверждён.

## Границы и следующий шаг

P1 завершён в границах preparation: подготовка stateless, UUID не резервируется; повтор с изменённым input даёт новый fingerprint. Raw claims/serialized sources — данные, не canonical proof или authentication. Hashes не дают прав, само наличие role guidance не подтверждает isolation/native support. Excerpts/outputs требуют review перед внешней передачей или принятием результата. Human choice/gates/semantic assessments не автоматизируются.

Далее P2: изолированный result journal/provenance, проверка exact task/snapshot/schema/budgets и current inputs, безопасный replay/conflict и review основным агентом. Затем P3 local hooks и P4 native opt-in adapters. R1/M6/M8 остаются открытыми. Новые dependencies/БД/контейнеры/LLM loop не добавлены; реальные .env/рабочие кейсы не читались. Стоимость и полная длительность IDE-сессии отдельно не измерялись.
