# FastMCP для основной PostgreSQL-системы

Команда `psa-main-mcp` запускает отдельный FastMCP 4.x сервер по stdio. Он использует те же прикладные сервисы и JSON-представления агентного прохода, что и `psa-main`. Общая сборка зависимостей находится в `bootstrap.py`; server, agent tools, search tools и обработка ошибок разделены по модулям в `interfaces/mcp/`.

`psa-mcp` продолжает обслуживать файловый MVP. Новый сервер работает с PostgreSQL и открывает четырнадцать инструментов:

| Инструмент | Что делает | Побочные эффекты |
| --- | --- | --- |
| `psa_main_search_sources` | FTS по актуальным ревизиям в одном проекте | Чтение БД |
| `psa_main_prepare_analysis` | Подготовка точного запроса, как CLI `--dry-run` | Чтение БД; полный выбранный текст возвращается MCP-клиенту |
| `psa_main_analyze` | Поиск, вызов настроенного LLM, проверка схемы/цитат | Отправка текста провайдеру, расход токенов, запись agent run |
| `psa_main_get_agent_run` | Просмотр успешного или неуспешного запуска | Чтение только в указанном проекте |
| `psa_main_start_pipeline` | Фиксация источников и запроса нового пайплайна | Запись checkpoint без вызова модели |
| `psa_main_get_pipeline` | Просмотр состояния, version и review packet | Чтение БД |
| `psa_main_resume_pipeline` | Продолжение одного этапа с expected_version | Из prepared — платный вызов; review/recovery/completed без нового вызова |
| `psa_main_prepare_critic` | Точный запрос для проверки сохранённого run | Чтение; текст источников и черновика возвращается клиенту |
| `psa_main_start_critic` | Новый critic pipeline с input_run_id/hash | Запись checkpoint без вызова модели |
| `psa_main_preview_selection` | Варианты, связанный critic, hashes и stale-source flags | Чтение; без модели |
| `psa_main_record_selection` | Явная человеческая команда сохраняет три варианта, решение и аудит | Атомарная идемпотентная запись; без claims/approvals/модели |
| `psa_main_get_selection` | Неизменяемая квитанция выбора по source run | Чтение в указанном проекте |
| `psa_main_prepare_strategy` | Точный запрос внутренних стратегических черновиков по selection | Чтение; решение/заметки/источники возвращаются клиенту |
| `psa_main_start_strategy` | Закрепляет decision input snapshot и pipeline | Запись без модели; генерация через resume |

Анализ остаётся черновиком: claims, решения и workflow не утверждаются автоматически. Повторный analyze создаёт новый run. Read-only инструменты не вызывают провайдера и не пишут runs. Поиск и подготовка работают без API-ключа. Материалы источников остаются недоверенными данными.

## Локальный запуск

```powershell
python -m pip install -e ".[agent,mcp]"
docker compose up -d postgres
alembic upgrade head
psa-main-mcp
```

Запускайте сервер из корня проекта: конфигурация `.env` загружается относительно рабочего каталога. Для MCP-клиента задайте абсолютный путь к Python из окружения, аргументы `-m product_strategy_agent.interfaces.mcp.server` и рабочий каталог репозитория. Альтернативно используйте установленную команду `psa-main-mcp`. Секреты остаются в локальном `.env` или явно передаваемом окружении; не копируйте их в отслеживаемую конфигурацию клиента.

Локальный DATABASE_URL использует `127.0.0.1`: в проверенном Windows-окружении соединение через localhost зависало, а IPv4 loopback работал. Docker Compose продолжает задавать внутренний hostname postgres. При необходимости задайте `connect_timeout=5` в query string DATABASE_URL для ограничения ожидания подключения.

Проект и материалы создаются через существующий CLI. Пример аргументов подготовки/анализа: `{"project_key":"demo","question":"Что известно об экспорте?","query":"экспорт"}`. Для поиска: `{"project_key":"demo","query":"экспорт","limit":10}`; для просмотра: `{"project_key":"demo","run_id":"UUID"}`.

stdout занят протоколом; сервер не печатает прикладные результаты через print. Стартовый banner отключён. Модули CLI не импортируются сервером. Инструменты имеют [аннотации FastMCP](https://gofastmcp.com/docs/servers/tools), обозначающие чтение, повторяемость и обращение к внешнему провайдеру. Аннотации описывают поведение и не заменяют разрешения клиента. Сервер не открывает HTTP-порт и предназначен для доверенного локального процесса; project scoping не является многопользовательской авторизацией.

Ошибки агента содержат ID запуска и безопасный код; этот run можно прочитать через get. Неожиданные ошибки backend заменяются общим сообщением. Проверка schema ограничивает длины question/query, UUID и search limit. Инструменты импорта произвольных файлов и URL в этот срез не входят.

[Коды ошибок модельного провайдера и диагностика](model-provider-diagnostics.md) одинаковы в CLI и MCP: например provider_http_401, provider_timeout, provider_incomplete_completion. Ключи и сырые серверные ошибки в checkpoint не сохраняются.

Prepare/analyze/start_pipeline принимают optional task: evidence_answer (default), [evidence_extraction](evidence-extraction.md) или [strategy_options](strategy-options.md). Для [critic](agent-critic.md) используются отдельные prepare_critic/start_critic с run_id; выполнение — через тот же resume_pipeline. Предложения и оценки не создают канонические claims/options/decisions и не меняют approvals. Inventory — четырнадцать; явный человеческий выбор описан в [strategy-selection.md](strategy-selection.md).

## Проверка

```powershell
python -m pip install -e ".[agent,documents,mcp]"
python -m unittest discover -s tests
python scripts/smoke_main_mcp.py
```

Smoke использует настоящий PostgreSQL и LiteLLM SDK с httpx.MockTransport для двух in-process анализов. Затем запускает production-сервер отдельным stdio-процессом и сравнивает поиск, подготовку и чтение с CLI; внешняя модель не вызывается. Синтетический проект остаётся в development-БД.

Отдельная живая проверка запускается явно: `python scripts/smoke_agent_live.py --live`. Она создаёт новый синтетический проект и делает одну попытку анализа через настроенный провайдер. Без override cap — 512 выходных токенов для answer либо 2048 для extraction/options, не выше конфигурации. Явный `--max-output-tokens N` задаёт разовый предел smoke от 1 до 8192, в том числе выше настройки `.env`; production-команды от этого не меняются. Timeout операций не более 45 секунд. Может расходовать токены. Это не жёсткий process timeout и не оценка качества модели; автоматического повтора нет. Результат и ID запуска выводятся без ключа и сырых ошибок сервера.

Текущий frozen Docker-образ включает documents/agent/mcp; stdio inventory и startup проверяются offline smoke. Автоматическая регистрация в IDE и проверка UI Codex/Qwen Coder/SourceCraft не выполняются. Semantic entailment и оценка качества реальной модели остаются следующими срезами.

Первый [checkpointed pipeline и resume](agent-pipeline.md) реализован: evidence → checked draft → локальный review packet. Отдельный linked critic pipeline оценивает сохранённый результат. Они не повторяют completed шаги или запрос с неизвестным исходом. Полный стратегический workflow, автоматическое восстановление неизвестного внешнего ответа и независимая оценка качества остаются следующими срезами.

Планирование по записанному выбору: [strategy-plan.md](strategy-plan.md). Результат internal-only и не даёт разрешения на публикацию.
