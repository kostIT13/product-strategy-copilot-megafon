# P7d — offline research smoke и сверка P7

17.11.2026 21:05 (Asia/Novosibirsk, UTC+7).

## Сделано

До реализации зафиксированы собственные synthetic JSON/protocol (`2e2216f`). Добавлены fixed runner и fault-injection tests (`390db41`), base-only demo CI step/summary и developer checks в AGENTS с bundle1.1.3/9 adapters (`86b076c`). Product skills/role profiles/registry1.0.0 не менялись. [Runbook и таблица оставшихся критериев](../docs/offline-research-smoke.md).

Runner создаёт только собственный temporary case: registry/local-copy fallback, stage context, две ревизии TXT, current/missing/untrusted search, synthetic claim с exact quote/hash/locator, render/validate/verify/nonempty coverage, research-plan draft и exact UUID replay, invalid/corrupt refusal, source withdrawal и invalidated coverage. Статус/stages/approvals/decision log сохранены; gates/decisions/semantic acceptance не выполняются. DNS/socket/process dispatch запрещены guard, public fetch не запускается. Case удаляется вместе с fixture; permanent user cases/receipts/private IDE config не трогались.

[Actual base-run JSON](2026-11-17-p7d-offline-research-run.json) на code commit `86b076cd4f4f298755825b90bf7945ec492b8709`, dirty=true (готовящиеся docs/reports):11 fixed checks passed, elapsed4.3602932s со cleanup, model/external requests0, provider_cost/human_seconds=null. Registry1.0.0, context bundle1.1.3, descriptor versions1.0.0; fixed fixture content hash указан в JSON. Это development snapshot и technical smoke, не measured agent benefit или production SLA. `final_case_ready=false` ожидаем: после withdrawal coverage правильно блокируется.

## Проверки

- Smoke7 tests OK,7.404s: полный путь/cleanup и отказ на forged quote, fake registry authority, DNS attempt, read-side write, fixture bounds/schema, sanitized nonzero report.
- Clean-base повтор7 OK,8.513s; отдельный actual base CLI run OK. Отсутствие SQL/LLM/MCP/document extras проверено явно через importlib (present=[]).
- Canonical context10 OK,4.414s; registry7 с реальной CLI/FastMCP stdio parity OK,8.558s. Итого24 различных targeted tests, без skips в dev run; base repeat не увеличивает это число.
- YAML parse и summary Bash syntax OK; Bash в Windows sandbox не загрузил DLL, тот же read-only syntax check вне sandbox завершился exit0.
- Harness write/check9, Ruff/docs259/diff и native Gitleaks history/tree/negative probes OK для итогового tracked export.

Full suite, release build, native IDE и independent reviewer не запускались в этой итерации. Предыдущий P7c HEAD76be0c0 отдельно подтверждён зелёными [CI](https://github.com/kostIT13/product-strategy-copilot-megafon/actions/runs/44096852387) и [demo](https://github.com/kostIT13/product-strategy-copilot-megafon/actions/runs/44096852468); это не заранее успешный результат P7d. Новый push запускает новую matrix/demo с research step.

## Осталось и следующий шаг

P7a–P7d локальные contracts выполнены. **P7 целиком остаётся открытым**: measured benefit каждого инструмента, фактическое применение knowledge IDE-агентом и независимая semantic оценка не получены. Candidate/RAG/provider не включены.

Следующий независимый подготовительный срез P8a: равноусловный sequential baseline и opt-in automation evaluation protocol/neutral packets. Открытые prerequisites P4–P6, live R1/M8 и независимый M6 явно сохраняются. Подготовка не разрешает paid/model/native run, dispatch ролей или утверждение новых product gates. Итоговый documentation commit фиксирует планы, runbook и этот отчёт.
