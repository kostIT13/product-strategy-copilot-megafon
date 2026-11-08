# Универсальный OpenAI-compatible клиент — 7 ноября 2026

Время завершения: 23:10 Asia/Novosibirsk. Длительность блока отдельно не замерялась.

По запросу пользователя Qwen отделён от провайдера: модель задаётся конфигурацией, endpoint реализует OpenAI-совместимый Chat Completions API. Старый QwenChatProvider заменён OpenAICompatibleProvider на LiteLLM SDK. Версия LiteLLM зафиксирована: 1.108.2; при проверке использован upstream SDK openai 3.46.0. Отдельный LiteLLM Proxy не нужен.

Изменения:

- `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_MAX_OUTPUT_TOKENS`, `LLM_TIMEOUT_SECONDS`, JSON `LLM_EXTRA_BODY` в typed config и `.env.example`. Конкретный облачный сервис больше не выбран по умолчанию. Нужно указать свой endpoint и доступный там model ID.
- Существующие QWEN_* адрес/ключ/модель/лимит/timeout читаются как alias с приоритетом LLM_*. QWEN_ENABLE_THINKING удалён; специфичные параметры сервера передаются через extra body. Локальный `.env` переименован без вывода значений; в Git он не включён.
- LiteLLM выбирает OpenAI-совместимый протокол префиксом `openai/`, исходное имя модели уходит в HTTP body без этого служебного префикса. Проверены имена с namespace, например `Qwen/Qwen3-32B`.
- Сохранены ModelProvider port, прикладной сервис и схемы ответа, точные цитаты и PostgreSQL audit. Миграции БД не требуются. CLI подключён к новому адаптеру.
- Отдельный BoundedTransport ограничивает ответ до 2 MiB перед SDK parsing, корректно обрабатывает content encoding и проверяет обязательный envelope. Raw usage используется для сохранения отсутствующих значений как null, поскольку SDK может нормализовать их в нули. Справочная стоимость не выдаётся за реальную.
- Нет retries на уровнях SDK/LiteLLM/HTTP, redirects, proxy env или cache; удалённый endpoint требует HTTPS и ключ. Локальный сервер без ключа получает технический Bearer `local-no-key`, необходимый SDK. Загрузка внешней pricing map и журналирование сообщений LiteLLM отключены.

13 тестов HTTP-контракта и настроек прошли на Windows с настоящим LiteLLM SDK и httpx.MockTransport: JSON mode, исходный model ID, extra body и запрет переопределения контракта, usage, malformed/truncated/oversized ответы, gzip, HTTP 302/401/429/500 без повторов, timeout и ошибки без утечки тела/ключа, alias/приоритет настроек.

Docker-образ собран с extra agent. Все 70 unit-тестов прошли в контейнере. `scripts/smoke_agent.py` прошёл с настоящим LiteLLM SDK, MockTransport и PostgreSQL: успешный черновик и три failed run для неверной цитаты, повреждённого JSON и HTTP 429; сохранены проектная изоляция, ревизии и CLI dry-run/show. Контрольный проект `agent-161bb7dda5dd`, успешный run `f334f874-9e24-402c-a321-58d2910b5256`; `live_model: false`. Синтетические записи оставлены локально для просмотра. `git diff --check` прошёл.

Реальный внешний endpoint модели не вызывался. Это проверка клиента и протокола, а не доступности конкретной модели или качества её анализа. Полный стратегический workflow и resume остаются следующими срезами разработки.

Инструкция: `docs/agent-analysis.md`; планы и README обновлены.
