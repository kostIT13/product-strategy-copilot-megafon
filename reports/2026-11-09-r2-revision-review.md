# R2: recoverable review ревизии источника

Время: 9 ноября 2026, 19:08 (Asia/Novosibirsk, UTC+7). Длительность отдельно не замерялась.

## Сделано

- Revision review перенесён с прямого events append на общий state/events workflow bundle с ACTIVE/completion, явным recovery, caller UUID replay/collision и expected_workflow_version.
- Добавлены RevisionReview domain command и pure dependency mapper, отдельные application port/service и filesystem reader. Legacy revisit wrapper вызывает service; application не читает filesystem напрямую.
- Перед подготовкой проверяются однозначная зарегистрированная ревизия, отсутствие ранее записанного review, хэши текущего/архивного source text, confined sources paths и все ожидаемые claim/decision IDs. Учитываются собственные claim links, выбранные options и отвергнутые alternatives. Повторы/пропуски/лишние IDs отклоняются, порядок канонизируется.
- Review увеличивает shared workflow_version и updated_at, добавляет один review event. Этап, mode, stages, approvals и бизнес-реестры не меняются. Kind-specific semantics связывают review с исходным revision event и запрещают изменение state вне разрешённых полей.
- CLI/MCP получили operation UUID и optional expected version; прежние команды без UUID совместимы, но exact retry требует caller ID. Исторические gate/mode bundles и legacy review records не переписываются.
- Обновлены основной план/roadmap, README и контракты; добавлен docs/revision-review-recovery.md.

## Проверено

- Все 266 unit-тестов прошли. Восемь новых сценариев: реальные kill на шести границах, exact replay/канонизация IDs/cross-kind collision, full dependency coverage, human reason/version checks, current/archive hashes/escape/dot paths, portable copy/changed-input refusal, semantic stage mutation при пересчитанном file hash, CLI и настоящий MCP stdio recovery/replay/shared version.
- Финальные восемь review tests повторены после уточнения path validation. Оба deterministic demo прошли в временных копиях; model_calls=0.
- Ruff, instruction-sync (9 managed files), forbidden-path/full-history, Markdown links и diff checks прошли.

## Границы и далее

Сам source import/revision creation пока остаётся legacy writer: этот срез делает восстановимой запись человеческого review, а не всю цепочку обновления источника. Следующий R2-срез — его перенос, затем остальные необходимые writers, mapping/import и retire старой цепочки. Source/review не исправляют claims автоматически и не доказывают истинность материала. Изменение derived stale/re-review статусов при последующих зависимостях остаётся задачей R3. Shared workflow_version не является версией всех реестров; raw/manual доступ обходит lock.

БД/Docker/реальные модели не использовались; .env, зависимости и пользовательские кейсы не менялись. Docker-based Gitleaks заново не запускался. R1 live IDE и M6/M8 отложены, R2 не завершён.
