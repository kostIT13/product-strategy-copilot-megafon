# R3: read-only аудит существующих синтетических демо

Завершено 14.11.2026 20:39 (Asia/Novosibirsk). Runtime revision: aeed3a3; ветка feature/main-solution-roadmap. Пользователь разрешил новый кейс при успешном существующем и сообщил, что опишет новый; описание/материалы пока не получены. Новый кейс не создавался.

## Фактический результат

Для projects/demo и projects/table-demo последовательно выполнено по 10 штатных CLI проверок, всего 20: validate, verify, coverage, strategy check, validation check/numbers/calculations, strategy numeric-inventory, policy show и review prepare --scope validation. Это read-only диагностика разработки, не содержательное исследование нового продукта и не independent evaluation.

| Проверка | demo | table-demo |
|---|---|---|
| validate / verify / coverage | Exit 0, passed / passed / ok=true | Exit 0, passed / passed / ok=true |
| strategy check | Exit 0, complete | Exit 3, incomplete: отсутствуют все 8 обязательных sections |
| validation check | Exit 3, incomplete: нет ровно одного psa-validation-v1 JSON block | То же |
| validation numbers / calculations | Exit 3, blocked: отсутствует measurement block | То же |
| numeric-inventory | Exit 0, needs_human_review, 4 tokens | Exit 0, needs_human_review, 15 tokens |
| policy show | Exit 0, legacy_adoption, status=validation | Exit 0, legacy_adoption, status=completed |
| validation review prepare | Exit 0, blocker отсутствующего measurement block | Exit 0, blockers measurement, strategy sections, C-001: claim_evidence_snapshot_missing и source_revision_stale_or_unbound |

Review prepare с exit 0 лишь формирует packet; наличие blockers не даёт accepted assessment. Numeric inventory не подтверждает корректность цифр. Legacy completed и прохождение validate/verify/coverage не подтверждают новые требования R3. Источник table-demo не объявляется устаревшим фактом: диагностика сообщает stale_or_unbound, а отсутствующий evidence snapshot требует отдельного разбора/штатной привязки.

## Что сделано в репозитории

Добавлен docs/r3-case-check.md: входы и разрешения, read-only preflight, содержательная матрица вопрос/evidence/alternatives/human choice/стратегии/numbers/review, правила corrections/render/согласований, фиксация passed/blocked/not_verified, измеренного/неизвестного usage и условия перехода R3 → R3.1. Оба плана ссылаются на протокол и фактические gaps старых demo.

Материалы, реестры, state/events, policy и approvals демо не менялись; их автоматическая миграция/переутверждение не выполнялись. Checks JSON со всеми true и новые человеческие choices не создавались. Hooks/subagents не запускались. Новых runtime функций/зависимостей нет. Новый кейс ожидает описания пользователя; R3 и отложенные R1/M6/M8 остаются открытыми.

## Проверки и ограничения

Текущая итерация — аудит/документация, без изменения Python-кода. Unit suite не перезапускался; предыдущий full426 не объявляется приёмкой кейса. Сами 20 CLI вызовов — meaningful smoke, выявивший blockers. Документационные проверки: sync9/docs193/Ruff и git diff --check — OK. API/модели/БД/.env не использовались; фактическое время/стоимость IDE-сессии отдельно не измерялись. Новое описание кейса и явные human gates/выборы не заменяются предположениями.