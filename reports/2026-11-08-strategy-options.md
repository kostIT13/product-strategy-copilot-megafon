# Стратегические альтернативы — 8 ноября 2026, 16:22 (Asia/Novosibirsk)

Продолжен этап 5 основной разработки. Ветка: feature/main-solution-roadmap. Длительность отдельно не замерялась.

## Реализация

- Отдельный доменный модуль strategy_options и текущий compact prompt strategy-options-v2; первый экспериментальный v1 сохранён для истории.
- Три варианта O1/O2/O3 с segment/value hypotheses, подходом, одним evidence basis и точной цитатой, допущением и вопросом проверки, риском и экспериментом. По три строки качественного сравнения с обоими другими вариантами. Численные рейтинги и winner отсутствуют в схеме.
- Строгая проверка IDs, полноты сравнения, дубликатов name/approach, source/revision/locator/quote; отдельный insufficient_evidence требует пустых options/comparison и явного gap. Все дополнительные поля запрещены.
- Новая задача использует существующие CLI, pipeline и девять FastMCP tools. Пакет помечен proposal_only/selection_required/requires_human_review; канонические claims/options/decisions, workflow и approvals автоматически не создаются.
- Linked critic принимает options run: options/O1…O3, comparison/O1…O3, gaps/0…N. Проверяются полнота покрытия, входной hash и закреплённые источники. Critic остаётся advisory; исходный packet не меняется.
- Alembic 0014 расширяет task constraints, downgrade блокируется при существующих strategy records. Старые answer/extraction/critic prompts и schemas не менялись.
- Диагностика различает provider_output_limit, provider_content_filtered и прочие incomplete completion. На отказе сохраняются известные usage, длительность/лимит и длины content/reasoning, без сырого reasoning. Неизвестные токены и стоимость не заменяются нулём.
- Live smoke получил явный --max-output-tokens (1–8192) только для разовой проверки; production лимиты не повышаются автоматически. Локальный .env не изменён.

## Проверки

- 140 unit-тестов — OK, включая 13 strategy tests и проверки сохранения безопасного usage при отказе.
- Миграция 0014 применена; Alembic check: No new upgrade operations detected.
- Итоговый PostgreSQL/stdio smoke: project strategy-13d3e04e2214, pipeline 79f2acdd-0aab-40f7-95da-97551124fac1, run a1c16e55-ecb6-4017-8ee6-9a9571cfc0d1, critic pipeline 9427b3ef-f08c-449a-9630-99f641b0272d. Три варианта/три сравнения, pinned revision после обновления источника, семь critic items, отказы неверной цитаты и сравнения, CLI/MCP parity, отсутствие canonical side effects. Только MockTransport, без внешней модели.
- Регрессия critic: project critic-569e8d07be95, pipeline 137f36a3-dc4d-4eba-9790-6c3b479913c9, critic run 94568067-b720-4cc8-9996-e09954dc4384, verdict needs_revision; stdio и recovery проверки прошли на фикстурах.
- Старый prepared critic checkpoint 9240c703-b099-4b58-87bf-2eef16eb302a восстановлен без генерации; старые профили не изменены.

## Живые попытки на синтетическом источнике

Всего пять явных вызовов настроенного OpenAI-compatible endpoint, модель Qwen3.8-27B. Автоматических retries нет; закрытые материалы не использовались. Цена неизвестна.

| Run | Профиль/лимит | Итог |
| --- | --- | --- |
| 13686811-43d0-4a99-9a6f-8e09e8b1e86a | v1, 2048 | Незавершённая генерация, старый код provider_incomplete_completion; usage тогда не сохранялся |
| a9944b36-3168-454e-804c-bd0ca7b2e35f | v1, явно 4096 | Тот же отказ; usage тогда не сохранялся |
| f7aad199-92f7-4391-87eb-0003361c8e5f | compact v2, явно 4096 | provider_output_limit; usage тогда ещё не сохранялся |
| f5f452ca-24c6-4f85-b320-3096f57b9fa9 | v2, диагностические 128 | provider_output_limit; input 2214, output 128, total 2342, reasoning_tokens 128, content_chars 0, reasoning_chars 663, duration_ms 2233 |
| 2e2400bf-a78a-4b5b-9cbd-3e2320b97b63 | v2, 2048, разовый enable_thinking=false | succeeded с валидным insufficient_evidence; 0 вариантов, 0 сравнений. Input 2178, output 147, total 2325, content_chars 500, duration_ms 2437; reasoning counters не предоставлены |

Разовый override LLM_EXTRA_BODY использовал chat_template_kwargs.enable_thinking=false из [официальной карты Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B). Параметр не зашит в универсальный клиент и не записан в .env. По последней попытке нельзя заявлять успешную живую генерацию трёх стратегий или отсутствие reasoning: подтверждены только валидный JSON и отказ при недостаточности evidence. Счётчики диагностического запроса не переносятся на более ранние попытки.

## Ограничения и следующий срез

Формальная проверка не доказывает экономическую состоятельность и смысловое различие перефразированных стратегий. Полный живой кейс с тремя альтернативами и независимая оценка качества остаются открытыми. Далее: явный перенос проверенных AI-предложений в канонические варианты и выбор человека, затем продуктовая/коммуникационная стратегия и план проверки. IDE instructions, полный workflow и отложенные приёмки не объявляются готовыми.

Инструкция: docs/strategy-options.md. Диаграмма: diagrams/main/strategy-options.mmd. Roadmap и общий план обновлены.
