# R3: human semantic audit и adoption quality gates

Завершено: 11.11.2026 20:11 (Asia/Novosibirsk). Ветка `feature/main-solution-roadmap`. Timestamp и результаты записаны также в development-log.md. По запросу пользователя изменения разделены на смысловые коммиты.

## Коммиты

1. `25cc0d8`: domain command/content binding, application service/port, filesystem packet/proof, workflow v7 codec/reconstruction/recovery и 6 tests.
2. `9a89b89`: CLI/MCP review prepare/record, gate semantic selector/reference, cross-scope rejection/freshness, integration tests и clean-base smoke с реальными synthetic review operations.
3. Отдельный documentation/report commit: quality canon/9 generated adapters, README/MCP/recovery/numeric contracts, основной план/roadmap и timestamp.

## Поведение

Prepare собирает authored brief/research/strategies, current factual evidence и mechanical blockers под общим case lock; ничего не утверждает. Для validation добавляются measurement plan и numeric baseline preflight. Record требует explicit human instruction по политике, actor/reason/verdict, шесть строгих boolean checklist answers, reviewed packet hash/version и caller UUID. Accepted нельзя записать с blockers или неполным checklist; changes_requested сохраняет отрицательную оценку. Attribution — self-reported, не authentication. Review не продвигает workflow, не переписывает approvals/choices и не разрешает experiment/publication.

Workflow v7 сохраняет immutable packet и публикует только state/events, проверяет request/hash/version/content и полностью реконструирует event/after-state. Проверены реальные process interruptions на preparation/ACTIVE/state/events/receipt/completion с copy/recover/replay/later writes. Packet/encoded metadata bounded, без усечения. Старые v1–v6/request без нового selector сохранены.

После первого recorded review gate требует явно выбранный последний accepted/current audit UUID. Strategy adoption распространяет requirement и на validation. Более поздний rejection не обходится старым accepted, отсутствующим UUID или review другого scope. Generated render/usage и собственные review/gate metadata не инвалидируют assessment сами по себе; изменение semantic inputs/mode/reopen/source/claim lifecycle инвалидирует его. Validation зависит и от истории strategy assessments: новое strategy review требует нового validation review. При последнем strategy rejection или stale strategy proof принять validation нельзя.

Gate сохраняет actor/hash/UUID/verdict reference; его recovery/replay проверяет original review bundle/COMMITTED receipt и captured content binding. Проверено отсутствие dependency receipt при interrupted gate: отказ, затем успешное восстановление после возврата оригинального receipt. Historical completed gate replay не сбрасывает later state.

В ходе анализа отрицательных путей дополнительно закрыт cross-scope обход: strategy rejection после принятого validation review теперь блокирует validation до свежего принятия стратегии и нового validation review. Начатый full run перезапущен на окончательном коде. Первые 6 audit tests и 10 initial integration tests прошли; итоговый расширенный targeted run — **11 tests, 83.912 s, OK**.

## Проверки и границы

Clean-base workflow без SQL/model/MCP extras прошёл v7 reviews → selected gates → completed → reopen → новое решение/reviews → повторные gates → copy/resume. Оба demo прошли в копиях с 0 model calls. Полный suite: 386 tests за 614.179 s, OK (1 skipped: Windows symlink privilege unavailable). Ruff, instruction sync (9 adapters), docs (182 documents), repository-history/diff checks и native Gitleaks 8.30.1 history/tree/negative probes прошли без находок.

Legacy cases без recorded reviews сохраняют прежний путь. Global schema/policy migration ещё не реализована; канонические IDE-инструкции требуют review для новых кейсов. Человеческая self-reported оценка не становится машинной проверкой истины и не заменяет independent evaluation. Более широкий numeric alignment, новый разрешённый кейс, live R1/M8 и independent M6 остаются открытыми. Content freshness не обнаруживает изменение внешней реальности без обновления кейса и не имеет TTL. Hashes не защищают от владельца, переписывающего весь каталог.

Реальные кейсы/.env/БД не читались/не менялись; платные API/модели не вызывались. Все actor/checklist fixtures — синтетические временные данные, не человеческая продуктовая приёмка. Hooks/subagents, БД/контейнеры и второй agent loop не добавлялись. Длительность и стоимость IDE-сессии отдельно не измерялись.
