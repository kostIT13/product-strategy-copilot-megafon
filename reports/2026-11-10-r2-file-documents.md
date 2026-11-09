# R2: файловый импорт документов

Дата фиксации: 10 ноября 2026, 01:09 (Asia/Novosibirsk). Ветка: `feature/main-solution-roadmap`. Длительность отдельно не замерялась.

## Сделано

Существующие PDF/DOCX/XLSX parsers подключены к файловому `psa source add` и `psa_add_source`. Acquisition остаётся отдельным adapter, typed metadata/native citation scopes — в domain. Запись использует общий SourceImportService и workflow v2: lock, version check, source history, ACTIVE/completion, explicit recovery и UUID replay без повторного чтения бинарного файла. Dependencies не добавлялись.

Source records сохраняют формат, обзорный locator и ограничения extraction; CLI показывает их, MCP возвращает. PDF verify ограничен указанной страницей, XLSX — значением конкретной видимой ячейки. Неоднозначные markers/coordinates отклоняются; формулы не вычисляются. DOCX использует непустые строки извлечённого текста и существующий paragraph locator. Publisher не выводится из файлового пути.

Созданы контракты file-document-import и legacy-retirement. Инвентаризация основана на коде; пользовательская БД не читалась, экспорт/миграция не выполнены. Обновлены README и планы. Следующий нужный срез — перенос public-HTTP guards и расширенного provenance, затем нужных функций и проверенный mapping/import/retire.

## Проверка

- Полный unittest suite: **301 тест, OK** (271.223 s).
- Девять новых document tests прошли отдельно: реальные синтетические PDF/DOCX/XLSX, native quote scopes, parser errors, optional-import isolation, interruption/recovery после переноса каталога и удаления исходного PDF, CLI/MCP replay.
- Оба CI demo прошли: read-only unchanged, render revalidated, 0 model calls.
- Ruff, sync harness (9 adapters), docs links, repository/history и diff checks проверены перед коммитом; итог в development log.
- После полного suite изменена только строка CLI help и документация; parser/source/verify код не менялся.

## Ограничения

Текстовый PDF без OCR; DOCX не сохраняет всю структуру Word; XLSX исключает hidden sheets и не рассчитывает формулы. По 10 MiB для оригинала и извлечённого текста, дополнительные parser limits сохранены. Raw binaries автоматически не архивируются; source revision/hash относится к извлечённому тексту. Старые v2 Text/HTML receipts поддержаны, новым local_document receipts нужен обновлённый runtime.

БД, Docker, real LLM, .env и пользовательские данные не использовались/не менялись. Старые entrypoints/dependencies/CI ещё не удалены; R2 открыт. Docker-based gitleaks и remote Actions в этой итерации не запускались. R1 live IDE, M6 и M8 остаются отложенными, не пройденными.
