# P7a: inventory и offline baseline retrieval

Статус на 17.11.2026: inventory и воспроизводимый synthetic baseline реализованы. Это development eval, не продуктовый кейс, независимая оценка агента или native acceptance. P7 целиком остаётся открытым.

## Реализованные инструменты и границы

Это проверяемый по коду inventory, а не runtime permissions registry. Наличие инструмента не предоставляет разрешение на сетевой запрос, передачу материала или расходы.

| Инструмент / сценарий | Реализация и версия поведения | Permissions / provenance | Limits / offline fallback | Польза и критерий исключения |
| --- | --- | --- | --- | --- |
| Импорт разрешённого локального материала | `sources.add_local_source`, file source-import service; source schema v1 | Читает указанный файл, записывает source/event через штатный workflow; SHA-256 и revision history | До 10 MiB входа/извлечённого текста; PDF/DOCX/XLSX требуют optional documents extras; нет OCR или вычисления формул | Извлечение для последующей проверяемой цитаты; semantic fidelity отдельно не оценена. Не использовать parser, теряющий необходимую структуру |
| Явный HTTP(S) fetch одной public страницы | `adapters/web/fetcher.py`, `policy.py`, file web reader | Внешний GET только для разрешённого URL; public DNS/IP checks, pinned transport, redirect revalidation; requested/final URL, fetch time, response hash | 10 MiB, 3 redirects, timeout 10 s, time budget 30 s; static HTML/plain text, без браузера/login. Offline — разрешённая локальная копия, без скрытого fetch retry | Бounded получение provenance; польза против ручного импорта не измерена. Не обходить отказ policy/неполную JS-страницу |
| Поиск по current sources | `FileSourceSearchService`, `literal_ignore_case_v1`; CLI `psa source search`, MCP `psa_search_sources` | Read-only case lock; hash/paths/active workflow проверяются файловым adapter; withdrawn исключены; source_id/hash/locator/quote | 500 sources, 32 MiB corpus, 50000 sections, query 200 chars, limit 1–50; полностью offline | Ниже измерен kernel baseline; синонимы не поддержаны, порядок source ID не relevance ranking. Не считать empty hit доказательством отсутствия явления |
| Stage-scoped knowledge/context | `instruction_context_service.py`, harness bundle1.1.1, knowledge1.0.0 | Read-only выбранные methods/checklists/skills, versions/hashes и provenance из catalog; методика не evidence кейса | Явная stage selection; без vector DB/embeddings/внешнего API; fallback — ручное чтение canonical файлов | Польза stage selection на независимом кейсе не измерена. Исключать нерелевантный метод, не добавлять весь каталог в контекст |
| Research brief/plan и evidence checks | Research artifact service, `validate`, `verify`, `coverage` | Author documents отдельно от generated registers; точность quote отдельно от истинности вывода; human gates сохраняются | Файловый последовательный путь, без модели/БД; missing data остаются unknown | Existing deterministic checks, не semantic reviewer и не retrieval ranking. Не подменять человеческую оценку pass-результатом |

Код legacy `SourceSearchService` и [PG FTS](source-search.md) не являются текущим файловым search backend. Optional LiteLLM-клиент также не является orchestrator IDE и не участвует в этом eval. Новые search providers, RAG и индексы здесь не добавлены.

Контракты: [file search](file-source-search.md), [research artifacts](research-artifacts.md), [withdrawal](source-withdrawal.md), [knowledge](../knowledge/README.md).

## Воспроизведение baseline

Из корня checkout с установленным базовым пакетом:

```powershell
python -m scripts.evaluation.retrieval
python -m unittest discover -s tests -p test_retrieval_evaluation.py -v
```

Вход: [фиксированный corpus](../evals/retrieval/corpus.json), 5 синтетических sources и 8 заранее размеченных запросов. Он содержит извлечённый текст с PDF/XLSX markers, а не binary documents. Постоянный кейс не создаётся. Скрипт вызывает настоящий domain search kernel, проверяет каждый hit против отдельно записанных scope text/hash и печатает JSON в stdout. В файлы кейсов он не пишет; внешних запросов/моделей нет.

На этом наборе при k=3: TP=5, FP=1, FN=1; micro precision=5/6 и recall=5/6 (83.3%). Проверены 6 возвращённых quotes. Синоним «смена времени» пропущен; неоднозначный «перенос» возвращает также перенос данных. Найденное отрицание оплаты не означает поддержку платежей. Эти ошибки оставлены видимыми, gold не подогнан под выдачу.

Метрики считают `(source_id, locator)`; micro precision=TP/(TP+FP), recall=TP/(TP+FN). Нулевой знаменатель возвращает null. Для запросов без gold-релевантных фрагментов FP считаются, пустая выдача не получает искусственную оценку 100%. Runtime `elapsed_seconds` измеряет только evaluation loop по готовому snapshot; fixture load, создание snapshot, file I/O/locking и model/human time в него не входят. Provider cost=null; отсутствие вызовов не измеряет общую стоимость разработки.

JSON содержит fixture SHA-256. Время зависит от окружения и не является latency SLA. Малый известный набор — regression/smoke baseline, не holdout benchmark. Unit tests проверяют учёт null/FP/FN, отказ на неверные gold references, duplicates, forged hash/quote. File adapter integrity, withdrawals и CLI/MCP parity проверяются отдельно `tests/test_file_search.py` и `tests/test_source_withdrawal.py`; этот eval их не подменяет.

## Протокол для следующего сравнения

1. До реализации candidate заморозить дополнительный synthetic holdout: синонимы/словоформы, неоднозначность, отрицания, числа/единицы, отсутствие ответа, withdrawal/revision и malicious source text. Разметить релевантные scopes вручную; спорные ответы вынести в отдельную категорию. Не смешивать methodology documents с product evidence.
2. Запустить unchanged literal baseline и candidate на одинаковых current-source snapshots, query set и k. Зафиксировать commit, corpus/query hashes, окружение, конфигурацию, зависимости, права и версии. Один и тот же разрешённый объём материалов для обоих режимов.
3. Сравнить per-category и micro precision/recall, exact quote/hash/locator integrity, unanswered queries, truncation и stale/withdrawn references. Для end-to-end запусков отдельно измерить file load, peak resources, latency и human help. Missing measurements оставить null. Нельзя сравнивать kernel timing с полным provider roundtrip.
4. Критерий допуска candidate на согласованном holdout: ни одного fabricated/stale/withdrawn reference, все existing negative integrity tests проходят; recall выше baseline минимум на 10 процентных пунктов при отсутствии падения micro precision и literal/native-scope regression. Это предварительное engineering правило допуска, не доказанный product effect; пороги и ресурсный budget фиксируются до запуска candidate.
5. Для внешнего provider дополнительно нужны явные permissions и расходы, provenance/version/limits, offline fallback и разрешённые данные. Сам eval не разрешает сетевые/платные вызовы. Без согласованного cost/resource budget candidate не становится default.
6. Если улучшения нет, integrity нарушена или бюджет превышен — исключить расширение и оставить literal path. Успех на этом малом development corpus недостаточен для RAG/provider adoption.

P7b завершён: [token candidate отклонён из-за precision loss](retrieval-comparison.md). Далее P7c — versioned registry существующих research tools; literal path сохранён. Независимая оценка полного IDE workflow, subagents/hooks и human time остаётся [P8/R5/M6](evaluation/README.md). Native P4, P5/P6 в целом и R1/M8 остаются открытыми.
