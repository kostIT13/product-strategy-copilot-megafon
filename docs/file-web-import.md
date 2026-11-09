# Публичные веб-источники в файловом psa

`psa source fetch ID https://example.org/page` и файловый MCP `psa_fetch_source` используют общий PublicWebFetcher/StaticWebPageExtractor через файловый SourceImportService. Это явная загрузка одной страницы, без БД, LLM API или автоматического обхода ссылок.

## Правила загрузки

- Только HTTP(S), стандартные порты 80/443; без credentials, whitespace/control characters и scoped IPv6.
- Все DNS-ответы должны быть публичными unicast адресами. Private, loopback, link-local, multicast, reserved и специальные IPv6 transition ranges отклоняются.
- Соединение идёт к проверенному числовому IP, без повторного DNS lookup транспорта. TLS проверяет сертификат и исходное имя хоста; HTTP Host сохраняет hostname.
- Каждый redirect повторно проверяется, включая DNS. Максимум три перехода; циклы, отсутствие Location и HTTPS → HTTP отклоняются.
- Только HTTP 200 и `text/html`, `application/xhtml+xml`, `text/plain`. Сжатые ответы не поддерживаются. Content-Length и фактический объём ограничены 10 MiB; извлечённый UTF-8 текст также ограничен 10 MiB.
- Действуют socket timeout до 10 s и проверяемый между операциями/чтениями budget 30 s. Это не жёсткий wall-clock deadline DNS/блокирующего I/O. Не выполняются JavaScript, linked resources, authentication или crawling; переменные HTTP proxy не используются прямым pinned transport.

Текст декодируется строго по объявленному charset (по умолчанию UTF-8 с поддержкой BOM). Неизвестная кодировка, повреждённый текст, NUL или пустой результат дают ошибку без публикации источника. HTML extraction отбрасывает scripts/styles и другие игнорируемые элементы; это не визуальная копия страницы и не подтверждение истинности её содержания.

## Происхождение и журнал

Source record сохраняет `provenance`: normalized requested URL, final URL, media type, charset, fetched_at и response_sha256. Ограничения extraction доступны в `limitations`, выводятся CLI и возвращаются MCP. `content_hash` отдельно относится к сохранённому извлечённому UTF-8 тексту с завершающим newline; response_sha256 — к исходному HTTP body. Raw body автоматически не архивируется.

Journal request сохраняет исходный URL без fragment; identity/ID источника по-прежнему определяется final URL. Изменение redirect destination может создать другой источник, а не revision прежнего. Это сохранённая семантика файлового source journal, не молчаливый перенос legacy ID.

`--operation UUID` и `--expected-workflow-version N` используют [общий source recovery contract](source-import-recovery.md). Version conflict проверяется до fetch. После capture recovery и точный UUID replay используют сохранённые material/text/result, не DNS и не HTTP. Другой UUID — новая явная загрузка. При неизменном извлечённом тексте новая загрузка обновляет metadata с новым событием import; текстовая revision создаётся при изменении text hash. Прежняя metadata остаётся в immutable operation bundles.

Workflow v2 не меняется. Новые capture metadata строго валидируются при построении/recovery; отсутствие metadata в исторических v2 web bundles поддерживается без их перезаписи и без retroactive provenance. Старые тексты не извлекаются заново новым parser. Новым provenance-bearing receipts нужен обновлённый runtime.

## Проверка и дальнейший перенос

Tests используют synthetic HTTP payloads, fake DNS и transport mocks, а не внешние сайты: policy/transport tests, файловый import, rejection без записи, raw URL controls, legacy replay, реальная остановка процесса/копирование/recovery и CLI → MCP stdio replay. Это локальная проверка механики, не live-проверка IDE или качества исследования. Оставшийся [план retire](legacy-retirement.md) включает нужный поиск/preflight, mapping/import/parity и вывод старых dependencies.
