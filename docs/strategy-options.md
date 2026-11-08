# Стратегические варианты и качественное сравнение

`strategy_options` — отдельная задача агента для подготовки трёх альтернатив по импортированным источникам. Результат является предложением для проверки и человеческого выбора. Канонические options/claims/decisions и approvals автоматически не создаются.

## Запуск

Примените миграцию `0014_strategy_options`, затем выберите task при обычном анализе или старте пайплайна:

```powershell
psa-main agent analyze demo --task strategy_options --question "Предложи и сравни стратегии развития экспорта" --query "экспорт" --dry-run
psa-main pipeline start demo --task strategy_options --question "Предложи и сравни стратегии развития экспорта" --query "экспорт"
psa-main pipeline resume demo PIPELINE_UUID --expected-version 0
psa-main pipeline resume demo PIPELINE_UUID --expected-version 2
```

Берите actual version из возвращённого состояния. MCP prepare_analysis/analyze/start_pipeline принимают `task: "strategy_options"`; get/resume остаются общими. Сама задача не добавляет tools; с явным selection текущий inventory — 14. Review packet имеет proposal_only=true, selection_required=true и requires_human_review=true.

## Состав результата

| Поле | Содержание |
| --- | --- |
| status | options_proposed или insufficient_evidence |
| options | При options_proposed — ровно три варианта с локальными ID O1/O2/O3 |
| name / approach | Разные названия и подходы; точные дубликаты без учёта регистра отклоняются |
| segment_hypothesis / value_hypothesis | Предположения о сегменте и ценности, не установленные рыночные факты |
| evidence | Одно обоснование источником с одной точной цитатой |
| assumptions | Одно допущение с validation_question |
| risks | Один явно названный риск |
| experiment | Предложенные question, method и success_signal |
| comparison | По одной строке для O1/O2/O3: сравнение с обоими другими ID, относительное преимущество, tradeoff и key_unknown |
| gaps / caveats | Не более двух пробелов и двух ограничений |

Текущий compact prompt — strategy-options-v2. Текстовые поля ограничены 400 символами, name — 200; цитаты — 400. В comparison/gap допускается не более одной цитаты. Первый экспериментальный prompt v1 сохранён для истории; подготовленные с ним синтетические checkpoints не выполняются под v2 молча.

Каждая comparison row должна ссылаться ровно на два других варианта. Unknown/duplicate/missing IDs и неполное сравнение отклоняются. Указанные citations в option evidence, comparison и gaps проходят общий source/revision/locator/quote контроль. Одну реальную цитату можно использовать как базу для разных предложений; это не делает их независимыми доказательствами.

При insufficient_evidence options/comparison должны быть пустыми и нужен хотя бы один gap. Schema не содержит winner, ranking, score или approved status; дополнительные поля запрещены. Prompt требует не выдумывать цены, затраты, конверсии и измеренный эффект. Числа или выводы внутри свободного текста не проходят отдельную экономическую/смысловую верификацию — для этого остаются critic и человек.

Сравнение качественное и предварительное. Одинаковый подход, перефразированный другими словами, не гарантированно обнаруживается формальной проверкой. Продуктовые возможности, спрос и готовность платить не считаются подтверждёнными только потому, что они упомянуты в предложении. Метрики эксперимента — предлагаемые критерии, не наблюдаемые результаты.

O1/O2/O3 — локальные ссылки внутри draft run, не UUID канонического OptionRecord. После проверки доказательств человек может явно сохранить варианты и решение через [selection](strategy-selection.md); автоматический выбор отсутствует.

## Critic и checkpoints

Для проверки сохранённого options run:

```powershell
psa-main critic prepare demo OPTIONS_RUN_UUID
psa-main critic start demo OPTIONS_RUN_UUID
```

Critic использует те же закреплённые source revisions и связывает input_run_id/hash. Items: options/O1…O3, comparison/O1…O3 и gaps/0…N. Каждый вариант оценивается целиком вместе с вложенными evidence/assumptions/risks/experiment; это не отдельная exhaustive assessment каждой текстовой фразы. Пропуск любого item блокирует техническую приёмку critic. Его verdict остаётся advisory и не выбирает вариант за человека.

Оригинальный options packet не меняется. Resume, fingerprint конфигурации и блокировка неизвестных платных исходов работают как в остальных задачах. Старые answer/extraction/critic prompts и schemas не менялись. Downgrade отказывается удалять task type при существующих strategy records.

## Лимит ответа и проверки

В живых проверках генерация исчерпала лимиты 2048 и 4096. Отдельная диагностическая попытка на 128 токенах показала пустой content и 128 reasoning tokens. При разовом отключении thinking через существующий LLM_EXTRA_BODY модель вернула валидный insufficient_evidence: три варианта на коротком источнике не предложены. Это проверка протокола и отказа при нехватке данных, а не успешная живая генерация трёх стратегий. Такой параметр описан в [официальной карте Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B); его поддержка зависит от endpoint. Универсальный клиент не добавляет его сам, локальный .env не изменён.

Production-команды используют LLM_MAX_OUTPUT_TOKENS без автоматического повышения или retry. Изменение лимита или extra body меняет provider fingerprint: уже подготовленный pipeline не выполняется с другими настройками молча. Failed run сохраняет известные usage, длины content/reasoning и лимит, но не сырой reasoning; неизвестная стоимость остаётся null.

```powershell
python -m unittest discover -s tests
python scripts/smoke_strategy_options.py
```

Smoke использует PostgreSQL, LiteLLM/MockTransport и отдельный stdio MCP subprocess. Проверяются pinned evidence, три варианта/сравнение, critic coverage, отказы неверных цитат/ссылок и отсутствие canonical side effects. Внешних вызовов нет.

Для отдельной живой попытки только на синтетических материалах:

```powershell
# Только если endpoint поддерживает этот параметр; override действует в текущем процессе PowerShell.
$env:LLM_EXTRA_BODY = '{"chat_template_kwargs":{"enable_thinking":false}}'
python scripts/smoke_agent_live.py --live --task strategy_options
Remove-Item Env:LLM_EXTRA_BODY
```

`--max-output-tokens` — явный разовый override для smoke (1–8192), в том числе выше настроенного лимита; `.env` он не меняет. Без флага действует прежний cap: 512 для answer, 2048 для extraction/options, не выше конфигурации. Timeout операций до 45 секунд, автоматических retries нет. Может расходовать токены; неизвестная стоимость сохраняется как null. Синтетические результаты не являются оценкой эффективности стратегий на рынке.

Диаграмма: `diagrams/main/strategy-options.mmd`.
