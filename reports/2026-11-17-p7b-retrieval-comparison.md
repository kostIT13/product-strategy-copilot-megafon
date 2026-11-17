# P7b — frozen test set и сравнение retrieval

17.11.2026 19:37 (Asia/Novosibirsk, UTC+7).

## Изменения и решение

До candidate зафиксированы 10 synthetic sources/16 gold queries и protocol с порогами (`88960f1`). Development-only literal-first token-window candidate, comparison runner, metadata и integrity/lifecycle tests добавлены отдельно (`adae42f`). Production interfaces/services не менялись; у evaluator добавлен optional method label для корректного различения результатов.

[Development run JSON](2026-11-17-p7b-retrieval-run.json) на commit `fa364061a741fec28efb39e817e877a5745071d9`, dirty=true (staged docs/reports): baseline TP5/FP0/FN6, precision1, recall5/11; candidate TP9/FP2/FN2, precision9/11, recall9/11. Все 5/11 возвращённых quotes точны. Candidate улучшает recall, но теряет precision из-за actor ambiguity и ослабления literal punctuation; он отклонён по заранее записанному критерию. Gold/пороги не исправлялись после результатов. Основной literal search сохранён.

Runtime по готовому snapshot: baseline mean0.00162276s, candidate mean0.00337044s,5 повторов каждого. Это kernel loop, не file/provider/IDE latency, SLA или масштабирование. Provider cost/memory/human/file-load неизвестны/null, model/external calls0. Source/input/protocol hashes и Python3.12.7/Windows/base dependency versions записаны в JSON. Canonical-content hash позволяет сравнить fixture при разных CRLF/LF.

## Проверки

- Candidate tests7 OK,1.889s: отказ в adoption при precision loss, baseline preservation, Unicode offsets,500-char/cross-section/top-k/invalid-scope boundaries, бюджет и lifecycle через реальный store.
- P7a evaluator tests5 OK,0.010s: старые метрики/null/duplicates/forged quote/hash не регрессировали.
- Existing file-search tests11,21.573s: OK с1 skipped (Windows symlink privilege unavailable), включая real FastMCP stdio parity и negative integrity/resource checks.
- Итого23 различных tests,1 skipped. Отдельный clean-base повтор обоих eval suites12 OK,1.793s, без optional document/MCP/LLM extras.
- Harness sync-check9, tracked docs, Ruff, native Gitleaks history/tree/negative probes и diff checks проверены для итоговой итерации.

Полный suite, binary parsers/web fetch suite, final release build и реальные IDE/native acceptances не выполнялись. Временный synthetic case использован только integration test; persistent user cases, human gates, решения, private configs и сети не менялись/не запускались. Недоверенный source text не исполнялся; LLM injection resistance здесь не оценивалась. Набор размечен тем же разработчиком, это не independent review.

Provenance JSON уточнён в `fa36406`: path и SHA-256 разнесены по отдельным полям после false positive Gitleaks на имени token_candidate рядом с hash. Сканер и правила не ослаблялись. Итоговый run повторён; metrics/adoption decision не изменились. Это development snapshot, не финальный clean release.

## План

[Runbook и таблица результатов](../docs/retrieval-comparison.md). P7b завершён как эксперимент с отрицательным решением об adoption. P7c — versioned registry существующих research tools с permissions/provenance/limits и offline fallback, без включения отклонённого candidate. Весь P7, P4/P5/P6, R1/M6/M8 остаются открытыми; P8/R5 требует отдельной независимой agent-level оценки. Итоговый documentation commit содержит планы, runbook, этот отчёт и immutable run record.
