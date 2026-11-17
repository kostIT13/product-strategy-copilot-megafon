# P7a — inventory research/knowledge/retrieval и baseline

17.11.2026 19:28 (Asia/Novosibirsk, UTC+7).

## Сделано

- Сверены реальные файловые adapters/services: local import, bounded public HTTP fetch, literal search, stage-scoped knowledge/context и research/evidence checks. [Inventory и protocol](../docs/retrieval-evaluation.md) разделяют permissions, provenance/version, limits, fallback и пока не измеренную пользу.
- Добавлен `python -m scripts.evaluation.retrieval`: 5 синтетических sources, 8 gold queries, k=3; вызывается настоящий domain search kernel. Quotes/hash проверяются против отдельно записанных scopes; никакого persistent product case, source fetch, модели или canonical writes.
- Результат: TP=5, FP=1, FN=1, micro precision=recall=5/6; 6 quotes проверены. Синоним пропущен, неоднозначный перенос даёт лишний hit. Null при пустом знаменателе не превращается в 100%; provider cost=null.
- Зафиксирован протокол дополнительного holdout и допуска candidate до RAG/index/provider. Нет нового retrieval backend или default activation. Исправлена устаревшая фраза knowledge README о ещё не завершённом выводе PG; catalog1.0.0/external source check dates не менялись.
- Три плана получили актуальный статус P7a и следующий независимый P7b. Канонические роли/skills и instruction contracts не менялись. Generator write/check подтвердил все 9 adapters без differences; bundle1.1.1 сохранён.

## Доказательства

Среда: Windows, Python3.12.7. Код/fixtures/tests: commit `aa5ce89` в `feature/main-solution-roadmap`; следующий документационный commit содержит этот отчёт и protocol.

SHA-256 raw fixture при запуске: `d64203fd2926891788207a785b9a0d3cf51a5a7ec4ade9de1b5a630b9415885e`. Hash зависит также от окончания строк JSON; метрики определяются содержимым. Первый loop runtime 0.0013779 s по готовому snapshot — не file/CLI/provider latency и не SLA.

- `test_retrieval_evaluation.py`: 5 tests OK, 0.012 s после форматирования; повтор в clean base без optional extras: 5 OK, 0.007 s.
- `test_file_search.py`: 11 tests, 22.179 s, OK с 1 skipped (Windows symlink privilege unavailable). Проверены current revision, integrity/refusal, read-only, native locators и реальный FastMCP stdio parity.
- Итого 16 различных tests, из них 1 skipped; base повтор не увеличивает число различных tests.
- Harness write/check9, docs250, Ruff и diff checks OK. Native Gitleaks8.30.1: history/tree clean, negative probes passed; итоговая проверка включает этот отчёт.

Полный suite, binary parser suite, web fetch suite, final release build, native host acceptance и независимый reviewer не повторялись. HTTP/provider requests и модели не запускались. Пользовательские кейсы, gates, решения и private IDE config не менялись.

## Что дальше

P7a завершён в заявленном локальном scope; P7 не закрыт. P7b — заранее размеченный holdout и сравнение простого локального candidate с unchanged literal baseline. Runtime registry/adoption и доказательство полезности инструментов требуют следующих срезов. Небольшой synthetic kernel corpus не подтверждает полезность стратегии, независимость review или production readiness. P4/P5/P6 в целом, R1/M6/M8 остаются открытыми; P8/R5 требует отдельного равноусловного agent-level eval.
