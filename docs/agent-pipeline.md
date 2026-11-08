# Checkpointed агентный пайплайн

Первый многошаговый срез разделяет фиксацию доказательств, получение проверенного ответа и сборку пакета для человека. Это отдельное состояние выполнения агента; human-approved workflow проекта не изменяется. В пайплайне один модельный вызов, финальная проверка детерминированная, без LLM critic.

[Critic](agent-critic.md) запускается отдельным связанным pipeline через critic start для уже сохранённого draft run. Исходный pipeline остаётся неизменным; critic input_run_id/hash и собственный модельный checkpoint проходят те же правила resume.

## Команды

Установите `.[agent,mcp]`, поднимите PostgreSQL и примените `alembic upgrade head`, включая миграцию `0011_agent_pipelines`.

```powershell
psa-main pipeline start demo --question "Что известно об экспорте?" --query "экспорт"
psa-main pipeline show demo PIPELINE_UUID
psa-main pipeline resume demo PIPELINE_UUID --expected-version 0
psa-main pipeline resume demo PIPELINE_UUID --expected-version 2
```

Берите фактическую version из последнего ответа/show. При обычном проходе start возвращает prepared/version 0; первый resume получает черновик и возвращает draft_ready/version 2; второй собирает review packet и возвращает completed/version 3. Version 1 относится к резервированию running attempt перед HTTP. Каждый resume продолжает один шаг. Completed означает готовность пакета, а не одобрение человеком.

Start принимает `--task evidence_answer` (default) или `--task evidence_extraction`. [Extraction](evidence-extraction.md) формирует типизированные черновики фактов, гипотез с validation question и gaps. Task закреплён в pipeline/run; resume использует соответствующие prompt/schema/citation checks. Старые checkpoints мигрируются как evidence_answer без изменения исходного answer prompt.

MCP над тем же сервисом: `psa_main_start_pipeline`, `psa_main_get_pipeline`, `psa_main_resume_pipeline`. Для resume передайте project_key, pipeline_id и expected_version. Start пишет состояние без обращения к LLM; resume из prepared отправляет текст провайдеру и может расходовать токены. Show и финальный review не вызывают модель.

## Состояния и восстановление

| Checkpoint | Что делает resume |
| --- | --- |
| prepared | Восстанавливает исходный запрос, атомарно резервирует attempt, выполняет один модельный вызов |
| draft_running, связанный run succeeded | Восстанавливает draft_ready из сохранённого результата без нового запроса |
| draft_running, связанный run failed | Сохраняет failed и безопасный error_code |
| draft_running, run ещё running/исход неизвестен | Отказывается повторять запрос: нужно проверить worker и run |
| draft_ready | Повторно проверяет схему и точные цитаты, формирует human_review_packet |
| completed | Возвращает тот же результат без побочных эффектов, включая повтор со старой version |
| failed | Сохраняет историю ошибки; автоматического retry нет |

Если процесс упал после записи succeeded agent_run, но до обновления пайплайна, следующий resume использует этот run. Если падение произошло после резервирования или отправки запроса до сохранения ответа, running checkpoint не позволяет определить, был ли запрос выполнен и оплачен. Автоматического восстановления внешнего ответа и exactly-once гарантии провайдера нет. Не запускайте новый платный проход вслепую: проверьте активный worker и состояние провайдера. Автоматическое снятие running, retry failed и ручной reset в этот срез не входят; новый pipeline — явная новая попытка.

## Снимок и конкурентность

Start фиксирует source/revision UUID, hash, locator, длины выбранных фрагментов, model/prompt version, хэш точного запроса и fingerprint конфигурации провайдера. Полные промпты и raw model output в pipeline не сохраняются. Resume читает закреплённые ревизии, перепроверяет SHA-256 и восстанавливает тот же запрос, не повторяя FTS. Новая ревизия источника после start не меняет подготовленный материал.

Изменение endpoint/model/max_tokens/extra_body, prompt/schema или закреплённого текста блокирует возобновление до вызова модели. API-ключ и timeout не входят в fingerprint: можно сменить ключ или транспортный timeout без изменения запроса. Внутреннее обновление модели сервером под тем же alias fingerprint не обнаруживает. Завершённый пакет можно читать и повторно получать независимо от текущей конфигурации.

Резервирование записывает running agent_run и ссылку pipeline на него одной PostgreSQL-транзакцией под блокировкой строки и проверкой version. Внешний вызов выполняется после commit. Конкурирующий resume получает conflict и не вызывает модель. Composite FK не позволяет связать pipeline с run другого проекта. Rollback до commit не оставляет orphan attempt. Проектное ограничение — локальная целостность данных, не многопользовательская авторизация.

Review packet содержит черновик, ссылки на доказательства, usage и requires_human_review=true. Проверка совпадения цитат не доказывает смысловую обоснованность всего ответа; semantic_entailment помечен not_evaluated. Insufficient_evidence остаётся явным статусом черновика. Claims, варианты, решения, возможности и approvals по-прежнему создаются отдельными действиями.

## Проверки

```powershell
python -m pip install -e ".[agent,documents,mcp]"
python -m unittest discover -s tests
python scripts/smoke_agent_pipeline.py
alembic check
```

Smoke проверяет PostgreSQL-транзакции и двух конкурирующих workers с синтетическим ModelProvider, CLI и отдельный stdio subprocess. Внешняя модель не вызывается. Синтетические checkpoints остаются в development-БД, в том числе намеренно оставленный draft_running для проверки неизвестного исхода. Регрессия LiteLLM отдельно покрыта существующими agent/MCP smoke-сценариями.

Диаграмма состояний: `diagrams/main/agent-pipeline.mmd`.
