# Critic-проверка сохранённого черновика

> Историческая документация старого контура. PostgreSQL/Alembic/Docker и psa-main удалены 10.11.2026; эти команды больше не являются инструкцией запуска. Текущий путь — [README](../README.md), состояние переноса — [R2](legacy-retirement.md).

Critic — отдельный проход по успешному evidence_answer, evidence_extraction или strategy_options run. Он читает тот же закреплённый контекст и оценивает сохранённые формулировки. Новый поиск не выполняется, оригинальный run/packet не переписывается. Это модельная оценка соответствия источникам, не независимое подтверждение фактов и не human approval. В текущем срезе используется тот же настроенный провайдер в новом контексте, без передачи истории генерации.

## Запуск

Примените миграцию `0013_critic_inputs`. ID исходного run берётся из agent analyze или pipeline.agent_run_id.

```powershell
psa-main critic prepare demo INPUT_RUN_UUID
psa-main critic start demo INPUT_RUN_UUID
psa-main pipeline resume demo CRITIC_PIPELINE_UUID --expected-version 0
psa-main pipeline resume demo CRITIC_PIPELINE_UUID --expected-version 2
```

Берите actual version из show/последнего ответа. Prepare показывает полный запрос без обращения к LLM и без записи состояния. Start фиксирует critic pipeline, также без LLM. Resume из prepared выполняет один модельный вызов; следующий resume собирает review packet локально. Повтор completed возвращает прежний пакет. Это отдельный pipeline со ссылкой на input_run_id, а не дополнительная мутация уже завершённого исходного пайплайна.

MCP: `psa_main_prepare_critic(project_key, run_id)` и `psa_main_start_critic(project_key, run_id)`, затем существующие get/resume_pipeline. Prepare возвращает полный текст исходников и черновика MCP-клиенту. С учётом явного selection в main server 14 tools. `evidence_critic` — внутренний task с обязательным input binding; обычный agent analyze --task / pipeline start --task его не принимают.

## Что оценивается

Для answer проверяется item_id=answer. Для extraction проверяются statements/0…N и gaps/0…N. Каждый item должен получить ровно одну assessment; пропуски, повторы и неизвестные ID отклоняются.

Для [стратегических предложений](strategy-options.md) items имеют ID options/O1…O3, comparison/O1…O3 и gaps/0…N. Вариант рассматривается целиком вместе с evidence, допущениями, рисками и экспериментом; proposal_only явно указывает, что это предложение. Это не отдельная exhaustive проверка каждой вложенной фразы и не выбор победителя.

| Поле assessment | Смысл |
| --- | --- |
| verdict | supported, needs_revision или insufficient_evidence |
| reason | Непустая причина до 2000 символов |
| citations | До пяти точных цитат из исходного контекста |
| revision_request | Обязателен для needs_revision/insufficient_evidence; у supported отсутствует или null |

Supported для item, отличного от gap, требует хотя бы одну цитату. Для gap разрешено отсутствие цитаты: пробел может описывать информацию, которой нет в выбранном фрагменте. Все указанные цитаты проверяются по source_id/revision/locator и точному тексту. Совпадение цитаты само по себе не доказывает логический вывод, поэтому critic отдельно должен оценить масштаб утверждения, гипотезы и отсутствующие данные.

Общий critic_verdict вычисляется сервером при сборке packet: любое needs_revision имеет приоритет, затем insufficient_evidence, иначе supported. Это не команда применения изменений. Packet всегда требует человека; semantic_entailment помечается model_assessed_not_verified. Никаких approved claims, решений, capability-подтверждений или workflow approvals не создаётся.

## Checkpoints и границы

К input_run_id добавлен SHA-256 канонического review target: task, исходный вопрос, model/prompt metadata, items/caveats и ссылки на контекст. Текст target восстанавливается из сохранённого исходного run, а не копируется в pipeline. Перед резервированием и финальной сборкой target пересобирается и сверяется с input_hash/request_hash. Изменение исходного черновика или source snapshot блокирует продолжение до вызова модели. Project-bound composite FK не позволяет сослаться на input другого проекта.

В модели API-запроса передаётся до 48000 символов сериализованного target, плюс исходные фрагменты — максимум три по 8000 символов. Слишком большой target отклоняется, без молчаливого пропуска части items. Ограничение символов не гарантирует соответствие token context конкретной модели; выходной лимит остаётся конфигурационным. Оценок максимум 40: до 20 statements и 20 gaps. Caveats показываются critic как ограничения, отдельные обязательные assessments для них не создаются.

Target должен быть succeeded и иметь task answer/extraction/strategy_options; failed/running runs и результаты другого critic не принимаются. Резервирование новой попытки использует прежние row lock/expected_version/atomic insert правила. Если critic run уже succeeded, resume восстанавливает pipeline без нового запроса. Если исход внешнего запроса неизвестен, платный вызов не повторяется автоматически. Unknown/failed reset, retries и автоматическая правка исходного текста в этот срез не входят.

Смена task/schema/prompt/провайдерной конфигурации не переисполняет старый checkpoint скрыто. Старые answer/extraction записи мигрируются с null input references; их prompts и request hashes не менялись. Downgrade не удаляет binding, если critic-записи уже существуют. Usage относится только к critic run; стоимость предыдущего анализа с ним автоматически не суммируется, неизвестная стоимость остаётся null.

## Проверка

```powershell
python -m unittest discover -s tests
python scripts/smoke_agent_critic.py
```

Smoke создаёт синтетический черновик с точной цитатой, но преувеличением «экспорт безлимитный и бесплатный»; это намеренно подготовленная ошибка. Затем проверяет настоящий LiteLLM SDK/MockTransport, PostgreSQL input FK/hash, coverage, recovery, отсутствие rewrite/approvals, CLI и отдельный stdio subprocess. Новая source revision не меняет контекст critic. Для проверки защиты hash синтетический target временно меняется прямым SQL и восстанавливается; прикладные сервисы terminal runs не редактируют.

Опционально `python scripts/smoke_agent_critic.py --live` выполняет ещё одну critic-попытку на этом синтетическом материале через настроенный endpoint. Максимум 2048 выходных токенов, не выше настроенного лимита, timeout операций до 45 секунд. Может расходовать токены. Автоматических повторов нет. Совпадение verdict с ожидаемым на одном кейсе не является оценкой надёжности critic на реальных кейсах.

Диаграмма связей и восстановления: `diagrams/main/agent-critic.mmd`.

Также поддерживается [decision-bound стратегия](strategy-plan.md): разделы product_strategy/communication/experiments/gaps и связь с зафиксированным решением.
