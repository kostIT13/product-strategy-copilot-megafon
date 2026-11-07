# Импорт локальных документов основной системы

```powershell
psa-main document import demo ./research.html --publisher "Организация"
psa-main document import demo ./notes.txt --encoding cp1251
```

Поддерживаются TXT, Markdown, CSV, JSON, HTML/HTM. Первые четыре формата читаются как текст; структурная аналитика CSV/JSON не выполняется. HTML разбивается на текстовые блоки, title сохраняется отдельно; script/style/noscript/svg/template исключаются. Сеть, JavaScript и связанные ресурсы не загружаются. По умолчанию используется UTF-8 с поддержкой BOM, другая кодировка задаётся явно. Ошибки декодирования не заменяются молча потерянными символами.

Размер входного файла ограничен 10 MiB; чтение ограничено лимитом плюс один байт. Пустые, неподдерживаемые и содержащие NUL документы отклоняются. PDF/DOCX/XLSX и OCR пока не поддерживаются.

По умолчанию идентичность источника задаётся абсолютным file URI; `--uri` позволяет задать устойчивый исходный URL или иной идентификатор. `--title` и `--publisher` передают метаданные. Результат проходит через SourceService: сохраняются текст, его SHA-256, locator и ограничения извлечения. Повтор неизменённого текста идемпотентен, изменение создаёт ревизию. Оригинальный файл не архивируется, SHA-256 относится к извлечённому тексту.

При работе через Docker документ должен быть доступен внутри контейнера. Например, разрешённый материал из `projects/demo/research.html` импортируется командой `docker compose --profile app run --build --rm app psa-main document import demo /app/projects/demo/research.html`.

Проверки адаптера: `PYTHONPATH=src python -m unittest discover -s tests -p test_documents.py` (для PowerShell задайте `$env:PYTHONPATH='src'`). Интеграционный сценарий: `docker compose --profile app run --build --rm app python scripts/smoke_documents.py`. Он оставляет синтетический проект с уникальным ключом для аудита.
