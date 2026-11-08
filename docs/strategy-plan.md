# Стратегия по сохранённому решению

`strategy_plan` готовит внутренний черновик продуктовой стратегии, коммуникационных гипотез и экспериментов по ранее записанному человеческому выбору. Это отдельный связанный task, не новый поиск и не повторный выбор варианта. Нужна миграция `0016_strategy_plans`.

## Запуск

Сначала завершите [selection](strategy-selection.md). Здесь нужен исходный options run UUID с квитанцией выбора; одна ручная DecisionRecord без этой цепочки не подходит.

```powershell
psa-main strategy prepare demo OPTIONS_RUN_UUID --question "Подготовь стратегию и план проверки выбранного пилота"
psa-main strategy start demo OPTIONS_RUN_UUID --question "Подготовь стратегию и план проверки выбранного пилота"
psa-main pipeline resume demo PIPELINE_UUID --expected-version 0
psa-main pipeline resume demo PIPELINE_UUID --expected-version 2
```

Берите фактическую version из ответа. Prepare возвращает точный запрос с решением, гипотезами, заметками человека, critic и источниками, без записи/модели. Start сохраняет неизменяемый input snapshot и prepared pipeline, без модели. Снимок content-addressed и может повторно использоваться разными pipelines; при неудаче создания pipeline может остаться неиспользованный cached input. Повтор start создаёт новый pipeline; это явная операция, а не автоматический retry.

Resume из prepared отправляет этот контекст настроенному LLM и может расходовать токены. Snapshot содержит self-reported owner и review notes: их тоже увидит провайдер. Лимит/extra body берутся из обычных LLM_* настроек, не повышаются автоматически. Неизвестный внешний исход не повторяется; успешный run восстанавливается без второй генерации.

Main MCP добавляет `psa_main_prepare_strategy` и `psa_main_start_strategy`; теперь 14 tools. Они используют тот же core; get/resume остаются общими. Generic agent analyze/pipeline start с fresh task не принимает strategy_plan без selection.

## Состав черновика

- decision_id и selected_option_id обязаны совпадать с закреплённым решением.
- product_strategy: segment/value hypotheses, scope proposal, non-goals, assumptions, risks и 1–2 source evidence items с точными цитатами.
- communication: 1–3 внутренних сообщения с kind hypothesis/open_question, audience/channel hypotheses и validation_question. Kind commitment и дополнительные поля запрещены. Проверка типов не доказывает, что свободный текст не содержит скрытого обещания: смысл проверяют critic и человек.
- experiments: 1–3 предложенных проверки с assumption/question/method и качественными success/stop signals. Это не измеренные результаты и не задания к автоматическому исполнению.
- gaps/caveats: до трёх каждого; caveats обязательны при plan_proposed. При insufficient_evidence product_strategy=null, communication/experiments пусты и нужен gap.

Текстовые поля ограничены 400 символами. Prompt требует краткости и запрещает выдумывать цены, затраты, эффекты или численные пороги. Проверяются UUID выбора, а не смысловое соответствие каждого scope/тезиса выбранному подходу; это задача critic и человека. Semantic entailment/экономическая пригодность формально не доказаны.

## Привязка и актуальность

При подготовке сверяются selection request hash, source/critic fingerprints, каноническое решение и его три dispositions, выбранный canonical option и исходное предложение. Input snapshot закрепляет эти значения и source references, хранится в strategy_inputs с project-bound FKs к источнику-run и решению. Snapshot также сохраняет gaps/caveats этапа вариантов и предварительное сравнение выбранного варианта; его размер ограничен 48 000 символов, без молчаливого обрезания. Hash/request реконструируются на resume; только для strategy_plan введена каноническая сериализация JSON, чтобы JSONB reorder не менял байты запроса. Старые answer/extraction/options/critic prompts и запросы не изменялись.

На prepare и перед генерацией проверяется актуальность source revisions; при новой ревизии требуется новый reviewed выбор. Это проверка в момент подготовки, не блокировка БД на время внешнего LLM-вызова. Уже сгенерированный результат можно завершить на исходных ревизиях, но packet получает stale_source_ids и source_freshness=stale_at_review. Completed replay возвращает исторический packet; он не подтверждает сегодняшнюю актуальность источников. Изменившиеся decision/selection/snapshot блокируют reconstruction.

Packet всегда requires_human_review=true, communication_internal_only=true, publication_approved=false. Он не переписывает решение, claims/capabilities и workflow approvals. Capability-backed customer commitments, утверждение/экспорт стратегии и публикация остаются следующими срезами. Учёт identity/RBAC также не добавлялся.

## Critic и проверки

```powershell
psa-main critic prepare demo STRATEGY_RUN_UUID
psa-main critic start demo STRATEGY_RUN_UUID
python -m unittest discover -s tests
python scripts/smoke_strategy_plan.py
```

Critic сохраняет связь с strategy run/input hash/decision/selected option и теми же источниками. Items: product_strategy, communication/N, experiments/N, gaps/N; каждый обязателен в assessment. Это оценка целого раздела, не исчерпывающая проверка каждой фразы. Verdict advisory, без права утверждения/публикации.

Smoke использует PostgreSQL, фиксированные ответы MockTransport и реальный stdio MCP: canonical selection fixture, одинаковый preview CLI/MCP, одна генерация при конкурентном resume, recovery без повторного запроса, schema/citation/decision отказы, stale-source flags, critic coverage и отсутствие canonical side effects. Его стартовый fixture повторно использует standalone selection smoke; живой модели нет. Режим replay записанных реальных модельных ответов не добавлялся.

Диаграмма: [strategy-plan.mmd](../diagrams/main/strategy-plan.mmd).

Для ручного review доступны [методики и чек-листы knowledge/](../knowledge/README.md). Они пока не подгружаются в strategy prompt автоматически.
