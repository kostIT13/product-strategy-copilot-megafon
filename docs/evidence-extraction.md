# Структурированное извлечение доказательств

Задача `evidence_extraction` готовит черновики утверждений и пробелов по импортированным источникам. Обычный ответ остаётся задачей `evidence_answer` по умолчанию. Обе задачи используют общий retrieval, LiteLLM port, проверку цитат, сохранение runs и checkpointed pipeline.

## Запуск

Примените миграцию `0012_agent_tasks`. Она добавляет task в agent_runs и agent_pipelines, существующие записи получают evidence_answer. Старый answer prompt/schema не изменён; хэши подготовленных ранее запросов сохраняют совместимость. Downgrade отказывается удалять task, если уже есть extraction-записи, чтобы не представить их как обычные ответы.

```powershell
psa-main agent analyze demo --task evidence_extraction --question "Выдели факты, гипотезы и пробелы об экспорте" --query "экспорт" --dry-run
psa-main agent analyze demo --task evidence_extraction --question "Выдели факты, гипотезы и пробелы об экспорте" --query "экспорт"
psa-main pipeline start demo --task evidence_extraction --question "Выдели факты, гипотезы и пробелы об экспорте" --query "экспорт"
```

Пайплайн продолжается обычными pipeline show/resume с expected_version. Task фиксируется при start и не меняется при resume. В MCP передайте `task: "evidence_extraction"` в psa_main_prepare_analysis, psa_main_analyze или psa_main_start_pipeline. Сама extraction-задача не добавляет новых инструментов, параметр optional с прежним default. С учётом critic и явного selection текущий main inventory — 14.

## Схема черновика

| Поле | Требование |
| --- | --- |
| status | extracted либо insufficient_evidence |
| statements | До 20 черновиков; при extracted нужен хотя бы один |
| statement.kind | fact или hypothesis |
| statement.text | Непустой текст до 2000 символов |
| statement.citations | 1–5 точных цитат из переданного контекста |
| statement.validation_question | Обязателен для hypothesis; не используется у fact |
| gaps | До 20 пробелов с непустыми question и reason |
| gap.citations | Необязательны; каждая указанная цитата проверяется так же, как у утверждений |
| caveats | До 10 непустых ограничений анализа |

Insufficient_evidence требует пустой statements и хотя бы один gap. Неизвестные поля и kinds отклоняются. Чужие/выдуманные цитаты и дубли одной цитаты внутри отдельного statement/gap отклоняются; одну реальную цитату разрешено использовать в разных утверждениях.

Fact означает «источник это сообщает». Это не независимая проверка истинности и не запись канонического claim. Hypothesis содержит вопрос для последующей проверки; gap фиксирует недостающую информацию в выбранном контексте и не доказывает её отсутствие во всех источниках. Ничто автоматически не переносится в claims, решения, capability registry или human workflow approvals.

## Архитектура и ограничения

Task registry `application/agent_tasks.py` связывает стабильный ID с версионированным prompt, Pydantic-схемой и проверкой цитат. Схемы extraction находятся в domain/agent/extraction.py, prompt — application/prompts/evidence_extraction_v1.py. Оркестратор остаётся общим; task сохраняется с run и pipeline и проверяется при резервировании/исполнении. Финальный review packet содержит task, типизированный draft и requires_human_review=true.

Количество источников и границы контекста прежние: до трёх ревизий, первые 8000 символов каждой. Лимит ответа берётся из LLM_MAX_OUTPUT_TOKENS; он не растёт автоматически. Незавершённый ответ не принимается и не превращается в частично подтверждённый результат. Для больших схем/корпусов лимит нужно выбирать явно; изменение запроса/конфигурации не переисполняет существующий pipeline скрыто.

Технические проверки схемы и точного совпадения цитат не доказывают semantic entailment или качество гипотез. Для отдельного [LLM critic](agent-critic.md) сохранённого run добавлены critic prepare/start; эта модельная оценка также требует человека и не является независимой верификацией.

## Проверки

```powershell
python -m unittest discover -s tests
python scripts/smoke_evidence_extraction.py
```

Smoke использует PostgreSQL, настоящий LiteLLM SDK с MockTransport, CLI и отдельный stdio MCP-процесс. Он проверяет закреплённую ревизию, типизированное хранение, отказ неверной цитаты в gap, привязку task и отсутствие автоматических claims/approvals. Внешняя модель не вызывается.

Живая проверка запускается отдельно: `python scripts/smoke_agent_live.py --live --task evidence_extraction`. Она отправляет только новый синтетический источник и ограничивает выход 2048 токенами, не выше настроенного значения. Для evidence_answer прежний smoke-limit — 512. Timeout операций не выше 45 секунд; retries нет. В проверке 8 ноября Qwen3.8-27B вернула два fact drafts и два gaps с четырьмя точными цитатами; стоимость неизвестна. Это один простой технический кейс, не оценка качества на реальном корпусе.
