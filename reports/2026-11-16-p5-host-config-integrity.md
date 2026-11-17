# P5a — config journal integrity и recovery копии

Дата: 16.11.2026 17:10 (Asia/Novosibirsk). Ветка feature/main-solution-roadmap.

## Сделано

- ACTIVE/COMMITTED публикуются через private staging, flush/fsync и atomic replace. Published v1 schema совместима с прежними завершёнными операциями.
- Explicit recovery сохраняет точные interrupted staging bytes с SHA в ignored private journal, затем восстанавливает staging из валидного intent. До16 snapshots/operation, без автоматической очистки. Authoritative corruption и полный JSON с неизвестным binding/schema не ремонтируются.
- Полный staged COMMITTED сохраняет исходный applied_at и позволяет завершить receipt publication без перезаписи последующих manual edits target. Без completion fact сохраняется current before/after hash guard.
- Read-only audit проверяет intents/receipts/ACTIVE/staging/snapshot hashes, возвращает фиксированные issue codes и counts без private bytes. CLI config-audit и FastMCP psa_audit_host_config используют общий service/store. Лимит1000 операций проверяется независимо от ACTIVE.
- Publication/audit вынесены в отдельные persistence modules; CLI/MCP остаются тонкими. Runbook, README и три плана обновлены. Следующий независимый срез P5b — остальные journal/path/resource boundaries; отложенная native приёмка P4 остаётся открытой.

## Проверки

- Config regression suite13,26.716 s,OK: прежние10 tests плюс начальные3 integrity tests; CLI и реальный FastMCP stdio audit parity, read-only hints, private canary не возвращается.
- Финальные integrity5,11.158 s,OK: copied backup recovery после остановки процесса на partial ACTIVE/COMMITTED/config staging и captured completion; exact snapshots, сохранение later edits, retention limit, authoritative corruption/unsupported intent, complete invalid/duplicate/deep JSON и history bound.
- P0 contracts12,0.052 s,OK. Итого27 разных целевых tests (15 config +12 contracts); повторные прогоны не увеличивают число.
- Clean base без MCP/LiteLLM: config13,17.823 s,OK (1 ожидаемый MCP skip); этот прогон предшествовал двум последним расширениям negative tests. Base completed/copy/resume/reopen/reapprove smoke OK, sql_dependencies=false, model_calls=0.
- Ruff, sync9, tracked Markdown links, git diff checks и native Gitleaks8.30.1 history/tree/negative probes OK. Итоговый docs check включает этот отчёт. Full repository suite не повторялся.

## Коммиты и границы

07338d7 — atomic metadata publication, preservation/audit core и recovery tests.
432a14c — CLI/FastMCP audit и real-stdio parity.
ca405d9 — точный audit resource limit и regression.
Итоговый docs commit фиксирует отчёт и планы.

Изменения config и backups выполнялись только во временных синтетических fixtures. Реальные IDE settings, рабочие кейсы, .env, БД/volumes не менялись; native hooks/subagents/модели не запускались. Ignored private данные не включены в commits/release. SHA — целостность, не аутентификация владельца. Проверено восстановление согласованной копии после process termination; power-loss/NAS/живое копирование и транзакция с внешним редактором не заявляются. Authoritative partial metadata прежнего writer требуют ручного разбора. P5 целиком, P4 native enable/acceptance и R1/M6/M8 не закрыты.
