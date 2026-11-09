# R2: recoverable смена режима исследования

Время: 9 ноября 2026, 18:58 (Asia/Novosibirsk, UTC+7). Длительность отдельно не замерялась.

## Сделано

- Смена режима перенесена из legacy state.write/events.append в общий workflow write-ahead bundle/ACTIVE/completion/recovery. Файловая логика не дублируется.
- Добавлены отдельные ModeChange domain command, domain research profiles, ModeWorkflowStore port и ModeChangeService. Legacy workflow wrapper стал тоньше; application service не читает filesystem напрямую.
- Request kind=mode_change и отдельный semantic validator разрешают только mode/mode_history/updated_at/workflow_version, ровно одно добавление события. Этап, stages и approvals не меняются. Исторические gate request/bundle без kind продолжают читаться без переписывания.
- Workflow_version теперь общий для journaled gate и mode операций; старые незажурналированные mode changes не пересчитываются. Добавлены caller UUID, optional expected version, exact replay/cross-kind collision checks в CLI/MCP. Status показывает актуальную общую версию.
- Сохранены ограничения completed/same-mode и требования minimum_sources/high-priority gap после source_collection. Recovery не заменяет эти проверки и не создаёт approval.
- Обновлены планы/контракты/README; добавлен docs/file-mode-recovery.md.

## Проверено

- Полный прогон: все 258 тестов прошли. Семь новых mode сценариев проверяют real process kill на шести границах, recovery без продвижения этапа/approval, shared version/replay/cross-kind collision, source/gap требования, семантическую подмену stage при пересчитанном file hash, portable copy/changed-input refusal, CLI и настоящий MCP stdio recovery/replay/gate.
- Обновлён paused mode writer test под новый журнал. Первоначальные новые тесты ошибочно требовали approvals=[] в старом state без первого gate; ожидание исправлено на допустимое отсутствие поля, данные не дополняются искусственно. Полный набор повторно прошёл.
- После добавления version discovery дополнительно проверены целевые mode tests. Оба deterministic demo прошли в изолированных копиях, model_calls=0. Ruff, instruction-sync (9 managed files), forbidden-path/full-history, Markdown links и diff checks прошли.

## Далее и ограничения

Source/revisit/render и остальные legacy writes ещё без write-ahead recovery; следующий R2-срез — их необходимый перенос, затем mapping/import/retire старой цепочки. Shared workflow_version не является глобальной версией всех реестров. Старый runtime без mode_change не должен открывать новые mode bundles. Размеры journal/capture ограничены, raw/manual доступ обходит lock.

БД/Docker/реальные модели не использовались; .env, зависимости и пользовательские кейсы не менялись. Docker-based Gitleaks заново не запускался. R1 live IDE и M6/M8 отложены, R2 не завершён.
