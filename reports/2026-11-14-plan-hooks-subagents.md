# План: субагенты и хуки непосредственно после R3

Завершено 14.11.2026 20:33 (Asia/Novosibirsk). Ветка feature/main-solution-roadmap.

По указанию пользователя добавлен отдельный этап R3.1 в основной план и краткий roadmap. Порядок: R3 → R3.1 (субагенты и хуки) → продолжение R4 → R5 → R6. Уже реализованный rollback R4 сохраняется; R3 не объявлен завершённым.

Этап включает: контракты/host capabilities/permissions/budgets/fallback; роли research/evidence/critic с изоляцией и provenance; hooks before-approval validation, source-revision/revisit и release checks; host adapters, runbook и positive/negative/replay/failure/injection/timeout tests. Зафиксированы критерии готовности, opt-in активация и сравнение с последовательным сценарием. Human gates/решения/semantic assessments не автоматизируются; собственного agent loop/API/БД/Docker не добавляется. Формулировка будущего production roadmap согласована с явным этапом R3.1.

Это только изменение плана: hooks/subagents не реализовывались и не запускались. Реальные кейсы/.env/БД не читались/не менялись, модели/API не вызывались. R1/M6/M8 остаются открытыми. Runtime и instruction canon не менялись, generated adapters не требуют пересборки. Unit suite не перезапускался для документационной правки; sync9/docs191/Ruff и git diff --check прошли.