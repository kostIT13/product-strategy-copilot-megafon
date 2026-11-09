# Импорт веб-источников основной системы

> Историческая документация старого контура. PostgreSQL/Alembic/Docker и psa-main удалены 10.11.2026; эти команды больше не являются инструкцией запуска. Текущий путь — [README](../README.md), состояние переноса — [R2](legacy-retirement.md).

```powershell
psa-main web import demo https://example.com/
docker compose --profile app run --build --rm app psa-main web import demo https://example.com/
```

Примените миграции до запуска: 0009 добавляет JSONB provenance к ревизии источника (у прежних записей пустой объект). Загрузка выполняется только явной командой, один URL за вызов. Поддерживаются HTTP/HTTPS на стандартных портах и ответы 200 с text/html, application/xhtml+xml или text/plain. Статический HTML проходит тот же extractor, что локальный импорт. JavaScript, ссылки страницы, PDF-download, cookies, аутентификация и crawling не поддерживаются.

Каждый URL и redirect заново проверяются: credentials в URL запрещены, все DNS-адреса должны быть публичными unicast. Local/private/link-local/metadata endpoints и IPv6 transition/scoped addresses отклоняются. Транспорт подключается к одному проверенному числовому IP, сохраняя исходный hostname для TLS/SNI и Host. Системные proxy-переменные не используются. HTTPS→HTTP redirect запрещён. Это политика приложения; для production дополнительно требуется сетевое ограничение исходящего трафика.

Лимиты: URL 4096 символов, 3 редиректа, 10 MiB тела, socket timeout 10 секунд и проверяемый между операциями временной бюджет 30 секунд. Сжатые ответы не принимаются (`Accept-Encoding: identity`). DNS и медленная передача заголовков не имеют гарантированного общего process timeout. Проверка TLS-сертификата включена. При неудаче первого DNS-IP автоматического перебора адресов и retries пока нет.

Кодировка берётся из HTTP Content-Type или по умолчанию UTF-8 с BOM. Невалидная кодировка не заменяется молча; HTML meta charset не анализируется. Название ограничено 500 символами.

URI идентичности — нормализованный исходный URL без fragment; redirects не меняют source_id. В provenance сохраняются requested_url, final_url, media_type, charset, fetched_at UTC и SHA-256 тела HTTP-ответа. Хеш source content_hash по-прежнему относится к каноническому извлечённому тексту. Повтор одинакового текста не создаёт новую ревизию: provenance остаётся от первого сохранения этой версии. Отдельный журнал каждого повторного HTTP-наблюдения пока не ведётся. Оригинальный HTTP-body не архивируется.

`python scripts/smoke_web.py` проверяет извлечение, provenance и ревизии на PostgreSQL с детерминированным fixture fetcher. Опция `--url https://example.com/` дополнительно выполняет реальный HTTP-запрос через CLI. В контейнере: `docker compose --profile app run --build --rm app python scripts/smoke_web.py --url https://example.com/`.
