# R3: read-only проверка числового фрагмента baseline

Завершено: 11.11.2026 01:33 (Asia/Novosibirsk). Ветка `feature/main-solution-roadmap`. Timestamp также записан в development-log.md. По указанию пользователя работа разделена на небольшие смысловые коммиты.

## Коммиты и результат

1. `ac8566d`: domain numeric anchor/parser/report, отдельный application service через существующий coherent validation/evidence port и 7 meaningful unit tests.
2. `361b88b`: CLI `psa validation numbers`, read-only FastMCP `psa_check_baseline_numbers`, реальный stdio parity test для literal_match/blocked и CLI exit 3.
3. Отдельный documentation/report commit: формат/границы, quality canon и generated adapters, основной план/roadmap, отчёт и timestamp.

Авторский psa-baseline-number-v1 block в drafts/validation-plan.md выбирает recorded claim/source/locator/quote, Unicode spans числа/единицы и явный decimal separator (по умолчанию точка). Проверяются текущий active factual proof, exact recorded citation, spans/bounds/token boundaries, Decimal value и буквальная единица. Нет rounding/scaling/unit aliases, подсчёта эффекта или поиска «подходящего» числа моделью. Corrupt/stale/withdrawn evidence и неподтверждённые citations блокируют packet. Unknown baseline — not_applicable, не числовое совпадение.

Packet содержит issues/evidence/anchor/hashes/review_hash; numeric_literal_matches/unit_literal_matches true только при успешном целом packet. Numeric_alignment_verified, semantic_alignment_verified, source_truthfulness_verified, experiment_approved и workflow_approval_granted остаются false. Значение числа, популяция, период, denominator и связь единицы с выбранной метрикой требуют отдельной смысловой проверки. Read-only check пока не является обязательным workflow gate; прежние gates/plan_report/receipts не менялись.

## Проверки

- Новые domain + CLI/real FastMCP tests: **8 tests, 27.571 s, OK**. До добавления interfaces отдельные 7 domain tests также прошли после явного decimal separator (12.126 s).
- Existing validation plan/gate/stdio regression: **10 tests, 21.795 s, OK**.
- Cases: exact read-only/repeat/fingerprints, mismatch value/unit/claim/recorded citation, missing anchor, stale revision/source withdrawal, unknown/malformed plan, signed decimals/comma/punctuation, partial/grouped/exponent/fraction tokens, duplicate/comment/example fences, malformed/overlapping/out-of-bounds spans и strict schema types.
- Base environment без MCP/model/SQL extras: 7 numeric tests (12.061 s), OK; полный synthetic workflow с reopen/redecision/recomplete/copy-resume OK. Оба demo OK, 0 model calls. Ruff, sync9, docs180, repository-history и diff checks прошли. Native Gitleaks 8.30.1 history/tree/negative probes — без находок.

Полный suite в этой итерации не запускался: добавлен отдельный read-only service/command, проверены его отрицательные сценарии и прежний validation contract. Последний полный прогон — 367 tests в source-withdrawal итерации; он не выдаётся за full result нового кода.

## Что осталось

Human semantic review с attribution/audit/freshness, более широкий numeric alignment и согласованное подключение к gates остаются R3. Новый разрешённый кейс для проверки полного результата, live R1/M8 и независимая M6 не объявляются пройденными. Hooks/subagents автоматически не включались. Не требуется собственный LLM API, PostgreSQL, Docker или новый agent loop.

Реальные кейсы/.env/БД не читались/не менялись; проверки — на синтетических временных данных и копиях demo. Модели/платные API не вызывались. Стоимость и длительность IDE-сессии отдельно не измерялись.
