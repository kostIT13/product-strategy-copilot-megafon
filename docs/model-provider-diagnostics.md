# Диагностика OpenAI-compatible провайдера

> Историческая документация старого контура. PostgreSQL/Alembic/Docker и psa-main удалены 10.11.2026; эти команды больше не являются инструкцией запуска. Текущий путь — [README](../README.md), состояние переноса — [R2](legacy-retirement.md).

Неуспешный agent run сохраняет безопасную причину в `error_code`. CLI и MCP возвращают ID запуска и этот код; `agent show` / `psa_main_get_agent_run` позволяют посмотреть сохранённый checkpoint. Новая миграция не нужна: используется существующая колонка agent_runs.error_code.

| Код | Значение и проверка |
| --- | --- |
| `provider_invalid_endpoint` | Проверить базовый URL: HTTPS для удалённого сервера, без credentials/query/fragment |
| `provider_missing_key` | Заполнить локальный LLM_API_KEY для удалённого endpoint |
| `provider_invalid_extra_body` | Extra body не может менять model/messages/stream/token limit/response_format |
| `provider_dependency_missing` | Установить extra agent |
| `provider_http_400`, `provider_http_422` | Сервер отклонил запрос: проверить точный model ID, JSON mode и дополнительные параметры |
| `provider_http_401`, `provider_http_403` | Проверить ключ и разрешения |
| `provider_http_404` | Проверить базовый путь и доступность модели; смысл зависит от сервера |
| `provider_http_429` | Проверить квоту и ограничения частоты |
| `provider_http_5xx` | Ошибка удалённого сервиса; сохраняется фактический числовой статус, например provider_http_503 |
| `provider_timeout` | Истёк timeout операции транспорта |
| `provider_tls_error` | Ошибка TLS/certificate в цепочке исключений; проверка сертификата не отключается |
| `provider_connection_error` | Ошибка подключения/HTTP-транспорта |
| `provider_response_too_large` | Ответ превысил 2 MiB |
| `provider_invalid_json`, `provider_invalid_envelope` | Повреждённый JSON или несовместимый chat completion envelope |
| `provider_output_limit` | finish_reason=length: исчерпан выходной бюджет, включая возможный reasoning |
| `provider_content_filtered` | finish_reason=content_filter |
| `provider_incomplete_completion` | Другой finish_reason, отличный от stop |
| `provider_empty_content` | Текст ответа пуст |
| `provider_sdk_error` | Ошибка SDK/нормализации, не отнесённая к известным категориям |
| `provider_error` | Общий код для прежних записей и провайдеров без уточнения |

HTTP-код сам по себе не доказывает конкретную причину. В проверенном развёртывании HTTP 400 сопровождался неверным model ID: read-only GET `/models` предоставил `Qwen3.8-27B`, тогда как в конфигурации было `qwen3.8:27b`. После исправления анализ прошёл. Это имя относится к настроенному серверу; у другого провайдера alias может отличаться.

Тексты серверных ошибок, URL с секретами, заголовки, ключи и тела ответов не включаются в диагностические коды. Коды ограничены фиксированным списком и числовыми HTTP-статусами. Причина транспортной ошибки сохраняется отдельно от исключения, которым её оборачивает SDK. Для HTTP-ошибки тело не читается. Успешный ответ передаётся SDK только с поддерживаемыми полями text-only chat completion; нестандартные metadata исключаются, чтобы предупреждения SDK не печатали их значения. Исходный envelope остаётся в памяти для точного учёта отсутствующего usage и не записывается в БД.

Автоматических retries, переключения модели или fallback без JSON mode нет. Сначала проверяйте конфигурацию, затем запускайте новый анализ осознанно: он может расходовать токены.

```powershell
python scripts/smoke_agent_live.py --live
psa-main agent show PROJECT_KEY RUN_UUID
```

Live smoke использует только новый синтетический источник. Без override cap — 512 выходных токенов для answer или 2048 для extraction/options, не выше настройки. Явный --max-output-tokens задаёт разовый smoke-limit 1–8192 и может превышать конфигурационный; `.env` и production-команды не меняются. Timeout операций не более 45 секунд. Успешная техническая проверка не заменяет оценку качества модели, retrieval и обоснованности выводов.

Если сервер вернул usage при незавершённой генерации, failed run сохраняет известные счётчики input/output/total/reasoning tokens, длины content/reasoning, длительность и выходной лимит. Сырой reasoning не сохраняется. Отсутствующие счётчики и стоимость остаются null; длина текста сама по себе не является числом токенов.
