# Инструкции агента

Opt-in роли research/evidence/critic доступны через [read-only handoff preparation](../docs/subagent-handoffs.md). Это отдельный явный запрос, не автоматический этап workflow или native запуск субагентов; последовательный путь остаётся базовым.

Канон правил — [AGENTS.md](../AGENTS.md); тематические документы: [workflow](workflow.md), [quality](quality.md), [safety](safety.md). Skills хранятся в [.agents/skills](../.agents/skills/psa-research/SKILL.md); Claude-копии и тонкие host adapters генерируются `scripts/sync_harness.py`, проверяются с `--check` и не редактируются отдельно.

`psa context ID` возвращает текущий этап и полный текст подходящих skills/knowledge с версиями и SHA-256. Команда только читает файлы. Из установленного wheel без репозитория передай `--instructions-root PATH_TO_REPO`; автономная упаковка всего context в wheel ещё не реализована. Source ZIP включает весь проект; sdist также включает канонические instruction assets, но не заявляется отдельным полным IDE-проектом со всей документацией. Для установленного пакета используй instruction root из репозитория/ZIP.

| Задача | Skill | Методики |
| --- | --- | --- |
| Бриф, исследовательские вопросы, источники | [psa-research](../.agents/skills/psa-research/SKILL.md) | M-SEGMENT-01, C-EVIDENCE-01 |
| Основания, пробелы, альтернативы | [psa-options](../.agents/skills/psa-options/SKILL.md) | M-OPTIONS-01, C-EVIDENCE-01 |
| Решение, стратегии и эксперимент | [psa-strategy](../.agents/skills/psa-strategy/SKILL.md) | M-EXPERIMENT-01, C-STRATEGY-01, C-CRITIC-01 |
| Продолжение, изменение источников | [psa-resume](../.agents/skills/psa-resume/SKILL.md) | C-EVIDENCE-01 |

Отметь реально использованные ID@version и context hash в авторской заметке `analysis/methods-used.md`: задача, применение/ограничения, дата, что изменило вывод. Существование заметки или packet не доказывает поведение модели; фактическая загрузка в IDE и качество на новом кейсе проверяются отдельно по [runbook](../docs/ide-instructions.md).

Для SourceCraft и любой среды без проверенного native loader: явно попросить открыть AGENTS.md и выполнить context; формат скрытых settings не придумывать. Файлы .codex/README.md и .claude/README.md — пояснения, а не исполняемая конфигурация. MCP в этом срезе автоматически не регистрируется.
