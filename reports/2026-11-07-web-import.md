# Импорт веб-источников — 7 ноября 2026

Добавлены отдельные URL policy, pinned HTTP transport, PublicWebFetcher, StaticWebPageExtractor, WebImportService и CLI `psa-main web import`. Миграция 0009_source_provenance сохраняет structured provenance в JSONB ревизии: исходный/конечный URL, media type, charset, fetched_at и SHA-256 тела ответа. Старые ревизии получают пустой объект.

Поддерживаются явные GET-запросы HTTP(S) на стандартных портах, HTML/plain text и до трёх redirects. Каждый DNS-адрес/redirect проверяется на публичность, соединение привязано к проверенному IP с исходным TLS hostname. Приватные/смешанные DNS-ответы, credentials, нестандартные порты, HTTPS downgrade, compressed/oversized/truncated ответы отклоняются. TLS-проверка включена. Лимиты и неполная изоляция общего времени описаны в `docs/web-import.md`.

Проверки из собранного Docker-образа на PostgreSQL 17:

- Миграция 0009 применена; `alembic check` не обнаружил новых операций.
- Все 47 unit-тестов адаптеров/сервисов прошли, включая проверки IP-политики, DNS recheck, pinned TLS, redirect loop, размера и усечения HTTP-body, кодировки, provenance и длины title.
- Детерминированный web smoke подтвердил идемпотентность, ревизию 2 при изменении текста и сохранность цитаты/исходной provenance.
- Реальный HTTPS GET `https://example.com/` через CLI прошёл. Контрольный проект финального образа: `web-a8812663c0f7` (`fixture_revisions: 2`, `live_fetch: true`). Предыдущий успешный проект: `web-412015bb72bb`.
- Общий сервисный smoke после миграции прошёл до completed: `smoke-b21851d4dba54c5d`, восемь workflow-событий.

Это импорт одного явно заданного URL, а не discovery-поиск или crawler. JavaScript, аутентификация, proxy, retries и скачивание PDF/DOCX по URL не добавлены. При неизменном извлечённом тексте provenance остаётся от первого сохранения версии. Оригинальный HTTP body не архивируется. DNS и socket timeouts не заменяют process isolation/egress firewall для production. Содержимое источника остаётся недоверенным; импорт не подтверждает истинность утверждений.
