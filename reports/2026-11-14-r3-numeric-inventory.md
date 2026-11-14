# R3: инвентаризация digit tokens для human review

Завершено: 14.11.2026 20:08, Asia/Novosibirsk. Ветка `feature/main-solution-roadmap`.

## Результат

Добавлены отдельные domain, application service/port и filesystem adapter для read-only списка цифровых фрагментов в product/communication/validation drafts. Adapter объединяет существующие bounded readers под общим case lock и проверяет согласованность state/version; новые state/schema/journal formats не вводятся. Packet фиксирует input hashes, review hash, точные Unicode позиции/строки и явно ограниченный контекст каждого token. Все вхождения остаются unassessed.

CLI: `psa strategy numeric-inventory CASE`. FastMCP: `psa_numeric_inventory` с read-only annotations. При наличии tokens status=needs_human_review; без них no_digit_tokens. Это не quality pass. Отсутствующий документ даёт blocked/exit 3; pending workflow, invalid state/path, превышение file/token/packet limits дают ошибку без частичного результата. Никакой записи в реестры, gates, источники или approvals нет.

Сканируются цифры во всём raw text, включая IDs, URLs, dates, code/comments и typed blocks. Это помогает человеку увидеть область, которую не покрывает явный calculation/baseline contract, без автоматического исключения неоднозначных цифр. Числа словами и nondecimal numerals вне области; numeric coverage/evidence/alignment/arithmetic/approval не подтверждаются. [Контракт](../docs/numeric-inventory.md) описывает точный regex, координаты, лимиты и процедуру ручного review.

Обновлены quality canon, 9 generated adapters, README/MCP, основной план и roadmap. Реальный продуктовый кейс ради разработки не создавался.

## Коммиты

1. `d5aa30c`: domain/application/adapter и первые шесть тестов.
2. `676e939`: CLI/FastMCP, base CLI и настоящий stdio parity.
3. `9f97d46`: pending workflow и invalid state negative tests.
4. Отдельный docs/report commit фиксирует инструкции, планы и результаты.

## Проверки

- Финальный новый suite: **9 tests, 7.069 s, OK**; Unicode/CRLF/точные offsets, IDs/URLs/comments/code, отсутствие цифр и файлов, file/token/packet limits, bounded context, hash freshness, read-only повторение, pending guard, invalid state/path, CLI и real FastMCP parity.
- Существующие strategy structure + calculation stdio + case access: **16 tests, 25.163 s, OK**. Это включает existing CLI/FastMCP behavior и busy/lock contracts.
- Clean base без MCP/model/SQL extras: **9 tests, 0.928 s, OK (skipped=1: MCP extra отсутствует)**. Полный файловый workflow completed/reopen/reapprove/copy/resume также прошёл, model_calls=0.
- Ruff/sync9/docs188/repository history — OK. Native Gitleaks 8.30.1: history/tree без находок, negative probes passed.

Полный общий suite повторно не запускался: предыдущие 407 tests прошли на срезе calculation check, а текущий независимый read-only инструмент проверен новым suite, затронутыми регрессиями и base workflow. Результат прежнего full suite не объявляется полным прогоном новой версии. Remote Actions result не проверялся.

## Что остаётся

Новый разрешённый кейс и содержательная полнота numeric coverage остаются открытыми. Эта команда не завершает R3 сама по себе. Live R1/M8 и независимая M6 по-прежнему отложены; R4 unfinished workflow rollback — отдельная задача. Реальные кейсы/.env/БД не читались и не менялись; платные model/API calls не выполнялись, hooks/subagents/контейнеры/БД не добавлялись. Test actors/approvals — изолированные synthetic fixtures. Длительность и стоимость IDE-сессии отдельно не измерялись.
