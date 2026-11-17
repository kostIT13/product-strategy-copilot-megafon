# Refresh инструкций: opt-in subagents/hooks и diagnostics

Дата: 17.11.2026 01:44 (Asia/Novosibirsk). Ветка feature/main-solution-roadmap. Запрос — актуализировать все проектные инструкции после реализации automation/P6c.

## Сделано

- Обновлены AGENTS.md, agent/README/workflow/quality/safety и четыре canonical .agents skills. Удалена устаревшая оговорка resume о ещё не реализованном отзыве R2/R3. Human choice/semantic assessments/gates и последовательный default сохранены.
- Добавлен agent/automation.md: explicit research/evidence/critic handoffs/journal/review, local preflight/run/source notice/release check, P6a/b/c diagnostics, host/disabled lifecycle, pending/recovery/version boundaries. Навигация ведёт к актуальным runbooks без дублирования schemas. Guidance/pass/ready не предоставляют mutation/native permissions, встроенные checks и development tests не требуют повторного opt-in внутри уже разрешённой задачи.
- Instruction bundle1.1.0 и три role profiles1.1.0. В profiles уточнены v1 usage fields/unknown, отсутствие verified/budget claims и запрет расширять доступ ради telemetry. SubagentResult/journal schemas остались v1; сохранённые пакеты/receipts не переписывались.
- Manifest navigation включает agent/README.md и agent/automation.md. Они входят в delivered context и context/canonical fingerprints. Fixed allowlist не разрешает role/host autoload или path escape. Legacy manifest без navigation сохраняет прежний путь.
- Пересобраны9 generated adapters: CLAUDE.md, QWEN.md, .cursor rule, .codex/.claude README и4 Claude skills. Они наследуют один канон; actual config/настройки global host не менялись. В AGENTS добавлено правило актуализировать canonical navigation/skills при дальнейших CLI/MCP/workflow changes.
- README, [контракт IDE context](../docs/ide-instructions.md) и планы обновлены. Это refresh канона, не реализация P6d и не активация native hooks/subagents/MCP connection.

## Проверки

- Context/navigation10,5.130 s,OK: delivery/hash drift/required missing file, reject path escape/role autoload/duplicate/malformed navigation, legacy manifest, actual CLI context из другого cwd, no case writes.
- Handoffs14,15.927 s,OK; task journal12,35.776 s,OK; host profiles9,10.173 s,OK. Итого45 разных целевых tests, включая real FastMCP parity, profile/snapshot binding и historical/copy recovery.
- Final base context10,4.599 s,OK без optional MCP/LLM extras. Full repository suite, hook workers и base completed smoke не повторялись: изменены instruction assets/context loader, поведение local checks не менялось.
- Skill-creator quick_validate прошёл для4 canonical+4 generated skills в UTF-8 режиме. Восемь CLI command forms из маршрутов проверены parser-ом, commands_executed=0. Это не behavioral/native IDE acceptance.
- Sync9, Ruff, tracked Markdown links, git diff checks и native Gitleaks8.30.1 history/tree/negative probes проверены перед push.

## Коммиты и границы

52e1620 — optional navigation delivery/hash validation и meaningful compatibility tests.
4359353 — canonical instructions/skills/profiles1.1 и generated adapters.
Итоговый docs commit фиксирует планы/отчёт/IDE runbook.

Profile/canonical hashes изменены осознанно. Перед дальнейшим использованием saved task нужно проверить freshness; старый ready/replay не становится разрешением нового результата. Старые records/human approvals остаются историей, текущие кейсы не мигрировались и не редактировались. Navigation связывает её собственные тексты/links, а не автоматически загружает все linked runbooks/roles.

Native host loading/connection/callbacks/dispatch не проверялись/не активировались. Реальные IDE config, working cases/.env/БД/volumes не читались/не менялись. Тесты используют temp synthetic fixtures; моделей/внешней передачи case materials не было. Skill-creator применён для scoped edits/validation; независимые subagents не запускались. P4/P5/R1/M6/M8 открыты; следующий функциональный срез остаётся P6d.
