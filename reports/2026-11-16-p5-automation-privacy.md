# P5d — privacy diagnostics и selected-material injection corpus

Дата: 16.11.2026 17:48 (Asia/Novosibirsk). Ветка feature/main-solution-roadmap.

## Сделано

- Закрыта подтверждённая CLI утечка private path через OSError в host/hook/subagent. Runtime I/O, encoding и необработанный Pydantic validation преобразуются в фиксированные сообщения отдельным interface formatter; exception chain подавлена при automation SystemExit. Авторские domain refusals (например unsupported namespace/stale binding) сохранены.
- Subagent prepare/journal MCP применяют тот же fallback к ValueError subclasses. Их existing safe I/O replies и host/hook generic errors сохранены. Malformed role catalog уже очищался в HandoffService; это закреплено regression, а не объявлено новой утечкой.
- Корпус проверяет реальные CLI stderr для трёх command groups, CLI schema/encoding errors, реальный MCP prepare/register malformed catalog и prepare invalid UTF-8. Без private canary/input_value/partial stdout или записи в кейс.
- Три псевдо instruction/tool/permissions payloads в selected authored материалах остаются data в task.inputs отдельно от role instructions; goal/authority не заменяются, canonical_writes/execution_started false и case bytes сохраняются.
- [Runbook и границы](../docs/automation-privacy.md), README и планы обновлены. Далее P5e dependency/artifact integrity и сверка оставшихся рисков перед P6. P5 целиком не закрыт.

## Проверки

Privacy5,13.657 s,OK. Handoffs14,16.170 s,OK. Task journal12,38.229 s,OK. Hook runs11,59.191 s,OK. Host acceptance/reviews/config/profiles43,57.950 s,OK. Итого85 разных целевых tests; независимые suites выполнялись параллельно. Regression включает CLI/реальный FastMCP stdio, replay/refusal и process termination/copy recovery.

Чистая base-установка без MCP/LiteLLM: privacy5,5.583 s,OK (1 ожидаемый MCP skip). Full repository suite и base completed workflow smoke в этой итерации не повторялись: изменён error rendering, успешные automation flows проверены целевыми suites.

Ruff, sync9, tracked Markdown links, git diff checks и native Gitleaks8.30.1 history/tree/negative probes проверены перед push. Новых runtime dependencies нет.

## Коммиты

b5fff83 — safe automation error rendering для CLI/subagent MCP.
c95202d — privacy и injection regression corpus.
Итоговый docs commit фиксирует runbook, планы и timestamp отчёт.

## Ограничения

LLM не вызывалась: это проверка программных границ данных/permissions, не semantic prompt-injection eval или независимое доказательство пользы. Success packets намеренно содержат выбранный текст; автоматической redaction authored actor/reason/materials нет. Не заявляется глобальный scrubber legacy CLI, argparse, debugger или чужих logs. Обычный domain ValueError должен содержать авторскую диагностику, не пересказ внешнего исключения.

Все mutations только на временных synthetic fixtures. Реальные IDE settings, рабочие кейсы, .env и БД/volumes не менялись; native subagents/hooks не активированы, внешних моделей/передачи данных не было. Private данные не коммитились. Live/native P4 и R1/M6/M8 остаются открытыми; future cross-schema converter требует целевой схемы.
