# Первый агентный проход: ответ по импортированным источникам

Срез выполняет вопрос → PostgreSQL FTS → фиксированные ревизии → JSON-ответ модели → проверку цитат → сохранение черновика. Это аналитический ответ на один вопрос, а не полный автономный цикл подготовки стратегии.

Задача по умолчанию — evidence_answer. Для [структурированных facts/hypotheses/gaps](evidence-extraction.md) добавлен отдельный профиль `--task evidence_extraction` со своей схемой и prompt version; task сохраняется вместе с checkpoint.

Для [critic-проверки](agent-critic.md) уже сохранённого run используйте отдельные critic prepare/start и pipeline resume. Она связывается с исходным run/hash, не повторяет поиск и не утверждает результат за человека.

Для [трёх стратегических предложений и их сравнения](strategy-options.md) используйте `--task strategy_options`. Задача не создаёт канонические options/decisions и не выбирает победителя.

## Запуск

Локально установите `python -m pip install -e ".[agent]"` (для файловых парсеров также extra documents). Docker-образ включает оба extra. Примените миграции, включая `0010_agent_runs`. В `.env` настройте LLM_BASE_URL, LLM_MODEL и LLM_API_KEY. Имя модели должно точно совпадать с моделью, доступной на выбранном endpoint; значение из плана само по себе не подтверждает доступность модели в API.

```powershell
psa-main agent analyze demo --question "Что известно об экспорте?" --query "экспорт" --dry-run
psa-main agent analyze demo --question "Что известно об экспорте?" --query "экспорт"
psa-main agent show demo RUN_UUID
```

Проект и источники должны уже существовать в PostgreSQL. `--query` задаёт ключевые слова для FTS; это отдельный параметр от вопроса. При отсутствии совпадений вызов модели не выполняется. `--dry-run` показывает точный запрос с текстом контекста локально, без HTTP-запроса и без создания записи запуска. Обычный analyze отправляет выбранные тексты настроенному провайдеру.

Для Docker команды выполняются через `docker compose --profile app run --build --rm app psa-main ...`. API-ключ должен находиться в локальном `.env`, а не в аргументах команд или Git.

## Границы контекста и ответа

Берутся до трёх актуальных FTS-результатов, для каждого — первые 8000 символов текста конкретной ревизии. Проверяются project_id, revision UUID и SHA-256 полного извлечённого текста. Источники передаются как недоверенные данные, без инструментов исполнения. Промпт версионирован: `evidence-answer-v1`. Длинные документы могут иметь совпадение вне выбранного префикса; в будущем потребуется подбор релевантных фрагментов.

Ответ проходит Pydantic-схему: answered с цитатами либо явный insufficient_evidence с ограничениями. Каждая цитата должна ссылаться на переданные source_id/revision, копировать locator и дословно присутствовать в отправленном фрагменте. Чужие, повторные и выдуманные цитаты отклоняются. Проверка точной цитаты не доказывает логическую обоснованность всего ответа и не заменяет человеческий review.

Результат — черновик. Claims, варианты, решения и workflow не изменяются автоматически.

## Провайдер и аудит

`OpenAICompatibleProvider` использует [LiteLLM SDK с OpenAI-совместимым endpoint](https://docs.litellm.ai/docs/providers/openai_compatible): `completion(model="openai/" + LLM_MODEL, api_base=LLM_BASE_URL)`. Префикс выбирает протокол; на сервер уходит исходный model ID, включая namespace и `/`. Qwen — значение LLM_MODEL. Отдельный LiteLLM Proxy не требуется. Сервер должен поддерживать `/chat/completions` и response_format=json_object. Неподдерживаемый JSON mode приводит к failed run без скрытого fallback.

LLM_MAX_OUTPUT_TOKENS по умолчанию 2048, LLM_TIMEOUT_SECONDS — 60. LLM_EXTRA_BODY={} задаёт необязательные параметры сервера, например `{"chat_template_kwargs":{"enable_thinking":false}}`. Клиент не отправляет thinking сам. Extra body не может переопределять model/messages/stream/token limit/response_format. Старые QWEN_BASE_URL/MODEL/API_KEY/MAX_OUTPUT_TOKENS/TIMEOUT_SECONDS читаются как alias; приоритет у LLM_*. QWEN_ENABLE_THINKING удалён: перенесите параметр в поддерживаемый сервером extra body.

HTTPS обязателен для удалённого endpoint; HTTP разрешён только для localhost/127.0.0.1/::1/host.docker.internal. Redirects, proxy-переменные, cache и автоматические retries отключены. Для локального endpoint ключ может быть пустым: SDK получает технический `local-no-key`, который отправляется как Bearer. Ответ ограничен 2 MiB до разбора SDK; незавершённая генерация отклоняется. HTTP timeout ограничивает операции транспорта, а не задаёт жёсткий process timeout. LiteLLM использует локальную карту моделей, загрузка внешней карты цен и журналирование сообщений отключены. Справочная стоимость не подставляется.

В `agent_runs` до HTTP-вызова создаётся checkpoint running, затем succeeded или failed. Сохраняются вопрос, query, модель, prompt version, ссылки/hash/длины выбранных контекстов, проверенный draft либо безопасный error_code. Полные запросы и невалидные сырые ответы в таблицу не записываются. Известные token usage и длительность сохраняются, неизвестная стоимость и usage — null, без подстановки нуля. Succeeded означает прохождение технических проверок, а не утверждение выводов человеком.

Для неуспешных запросов сохраняются уточнённые коды: HTTP-статус, timeout/TLS/connection, некорректный или незавершённый ответ, ошибка SDK. [Диагностика и порядок проверки](model-provider-diagnostics.md). Model ID должен точно совпадать с идентификатором сервера; для проверенного endpoint это `Qwen3.8-27B`.

После падения процесса run может остаться running: автоматический resume/retry пока не реализован. Повтор analyze создаёт новый запуск и может повторно расходовать токены. Готовые terminal records через сервис не перезаписываются. Show ограничен указанным проектом.

Для checkpointed запуска используйте [pipeline start/resume](agent-pipeline.md): он закрепляет исходный запрос и связывает attempt до вызова провайдера. Сохранённый успешный результат восстанавливается без повторной генерации; неизвестный исход внешнего запроса не повторяется автоматически. Ограничение standalone analyze выше сохраняется.

Проверка без платного API: `docker compose --profile app run --build --rm app python scripts/smoke_agent.py`. Она использует настоящий OpenAICompatibleProvider, LiteLLM SDK с httpx.MockTransport и PostgreSQL; это проверка протокола и оркестрации, а не качества реальной модели.
