# R2: утверждение конкретной structured версии плана

Время: 9 ноября 2026, 18:25 (Asia/Novosibirsk, UTC+7). Длительность отдельно не замерялась.

## Сделано

- ResearchArtifactService разрешает выбор только текущей committed operation/version; проверяет journal integrity и свежесть base inputs. Отсутствие selectors, старый UUID/version или изменённые входы блокируют gate.
- CLI `psa gate approve --stage research_plan` получил `--artifact-operation` и `--artifact-version`; файловый FastMCP `psa_approve_stage` — соответствующие поля. Оба используют общий workflow/service.
- Существующий structured draft нельзя обойти содержательным legacy Markdown. Кейсы без committed structured плана сохраняют прежний путь через `02_research-plan.md`. Повреждённый journal не вызывает fallback.
- Явное human approval сохраняет в state/history и events ссылку с operation_id/version/manifest_hash/base_case_hash; запись draft сама не переводит этап. Указанное имя человека/роли не является технической аутентификацией.
- Workflow gates используют общий OS project lock с artifact writers. Обновлена подсказка следующего шага; авторский Markdown не перезаписывается и не создаёт второй канон утверждённого плана.
- Обновлены основной план, roadmap и файловые контракты.

## Проверено

- Все 234 unit-теста прошли. Восемь новых проверяют точную привязку approval, отсутствие согласия/селекторов, старые версии, изменённые входы, занятый lock, corrupt journal, legacy compatibility, CLI и отдельный настоящий MCP stdio process.
- В первоначальном CLI-тесте неверно ожидался JSON вместо штатного текстового вывода и не учитывалась Windows encoding. Тест исправлен; целевые восемь и полный набор повторно прошли.
- Оба deterministic file demo прошли в временных копиях; model_calls=0.
- Ruff, instruction-sync (9 managed files), forbidden-path policy по рабочему дереву/полной истории и diff checks прошли. Markdown links проверены после добавления отчёта.

## Границы и далее

State.json/events.jsonl gate пока записываются legacy способом, без multi-file atomic commit/recovery и idempotent approval replay. Сбой между файлами может оставить несогласованность. Общий lock защищает от участвующих artifact/gate writers; прочие legacy writers/ручные правки ещё могут обходить его. Следующий срез R2 — перенос workflow state/events на commit/recovery-протокол, затем нужных writers/readers и import/retire старой цепочки.

Сам approval изменяет base inputs исторического draft: флаг show об изменённых входах после перехода ожидаем и не означает автоматический отзыв approval. Новые draft-версии не меняют историческую ссылку.

БД, Docker, реальные модели, .env и пользовательские кейсы не использовались/не менялись; зависимости прежние. Docker-based Gitleaks заново не запускался. R1 live IDE, M6/M8 остаются отложенными; R2 не завершён.
