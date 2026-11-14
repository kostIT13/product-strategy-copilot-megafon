# R3: полный синтетический кейс «Слот»

Завершено 14.11.2026 20:53 (Asia/Novosibirsk). Ветка feature/main-solution-roadmap. Пользователь явно поручил придумать полный кейс: реальных материалов нет, только синтетика.

## Сюжет и результат

Вымышленная студия мастер-классов решает, как помогать посетителю при изменении планов: O-001 ручной перенос (status_quo), O-002 закрытие отдельного self-service направления (stop), O-003 узкий перенос той же цены без платежей/возвратов (change). Условная рекомендация автора — сначала исследовать O-003; реальный human choice отсутствует. Сильнейшее возражение: без подходящего свободного времени интерфейс не создаст пользы, но может увеличить конфликты мест/поддержку.

Подготовлены brief/research plan, три synthetic исходных текста, 7 claims (3 факта о содержании учебного файла, 3 synthetic обстоятельства, 1 hypothesis), 3 high-priority gaps, три полных варианта, planned/unavailable capabilities, восемь разделов условных product/communication drafts, typed measurement plan с unknown реальным baseline/получением/окном/guardrails/owner/decision rule, два явных расчёта и methods/options notes. Учебные значения 40/200=0.2=20% не являются реальным спросом/наблюдением/эффектом. Реальные затраты, пороги/объём наблюдений и owner не назначены; даты/окно помечены как учебные предложения.

Исходный пакет и сборка: examples/slot-workshop/. Рабочий кейс: projects/slot-workshop-synthetic/, явно исключён из Git; воспроизводимые авторские synthetic assets коммитятся отдельно. Builder использует штатные init/source/ledger/render services, не пишет state/JSONL/generated Markdown вручную, не создаёт decisions/approvals и не вызывает внешние модели. Повторный запуск на заполненном кейсе запрещён; --use-empty-initialized проверяет нетронутый current seed под lock. Stage остаётся intake, semantic_review=required, approvals=0, decisions=0.

## Ошибка, обнаруженная полным кейсом

Default CLI validate/verify с relative projects path сообщали quality_policy: workspace path escaped its root. Initially_required передавал relative case root в confined path guard. Исправлено нормализацией Path.absolute перед guard (без следования symlink через resolve). Добавлены regression tests для relative/absolute receipts, legacy directory и default CLI validate/verify. Ошибка не скрыта сменой пути; исходные команды после исправления проходят.

## Коммиты

- 95b6078: исправление relative quality-policy paths и 2 regression tests.
- 7d89a7e: полный synthetic пакет/сборка и исключение локального working case из Git.
- Отдельный report/docs commit: протокол, оба плана и результаты.

## Проверки

- Новые relative-path tests: 2 tests, 0.491 s, OK. Весь quality-policy suite: 13 tests, 59.147 s, OK, включая recovery/anti-downgrade и real CLI/MCP.
- Штатные CLI на новом кейсе: validate/verify passed; coverage ok; strategy structure complete; validation complete; numbers not_applicable из-за честного unknown baseline; calculations arithmetic_match; numeric inventory 91 token, needs_human_review. Validation semantic prepare возвращает ожидаемый blocker отсутствующего current human decision. Это не accepted review.
- Clean base без MCP/model/SQL extras: новая сборка portable-slot, отказ обеих попыток перезаписи (обычная/--use-empty-initialized) с неизменными bytes; copy + validate/verify/coverage/calculations, 4 read-only checks без изменений. Model calls=0, approvals=0.
- Ruff/sync9/docs201/repository history и native Gitleaks 8.30.1 history/tree/negative probes — OK.

Full426 повторно не запускался: изменение runtime ограничено нормализацией policy path и покрыто всеми 13 policy tests; содержательный пример проверен реальной сборкой/CLI/переносом. Новых готовых approvals, независимого review и live host проверки нет. R3 не объявлен завершённым; R3.1 (hooks/subagents) начинается после явного прохождения человеческих этапов R3, R1/M6/M8 остаются открытыми.

## Происхождение и границы

Использованы локальные psa-research/psa-options и knowledge heuristics с версиями в methods-used.md. Psa-strategy как процесс принятой стратегии не запускался; условные drafts подготовлены по прямому запросу полного вымышленного сценария и не выданы за human selection. Все исходные материалы придуманы одним автором, независимого подтверждения нет. Реальные интервью/бизнес-данные/внешние страницы не исследовались. БД/.env/paid models/API не использовались. Стоимость и полная длительность IDE-сессии неизвестны. Прежние demo/table-demo и их история не менялись.