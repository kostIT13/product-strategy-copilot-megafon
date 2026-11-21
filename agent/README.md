# Навигация по инструкциям

1. Прочитай [AGENTS.md](../AGENTS.md). Запусти `psa context ID`. Например, `psa context telecom-family-demo`.
2. Прочитай правила и материалы текущего этапа из ответа. При необходимости открой [порядок работы](workflow.md), [проверки](quality.md) или [безопасность](safety.md).
3. Если команда недоступна, покажи ошибку и открой нужные файлы ниже. При запуске из другого каталога укажи `--projects-dir PATH --instructions-root REPO`. Для установленного пакета используй канон из репозитория или ZIP.

| Задача | Навык | Методики |
| --- | --- | --- |
| Уточни задачу и запиши бриф | [Постановка](../.agents/skills/psa-intake/SKILL.md) | [Сегменты и задачи](../knowledge/methods/segmentation.md) |
| Спланируй исследование, оцени материалы и основания | [Исследование](../.agents/skills/psa-research/SKILL.md) | [Доказательства](../knowledge/checklists/evidence.md) |
| Сравни альтернативы и проверь возражения | [Варианты](../.agents/skills/psa-options/SKILL.md) | [Сравнение вариантов](../knowledge/methods/alternatives.md) |
| Обоснуй выбранный продуктовый подход | [Продуктовая стратегия](../.agents/skills/psa-strategy/SKILL.md) | [Польза и экономика](../knowledge/methods/economics.md) |
| Проверь сообщение, обещание и канал | [Коммуникационная стратегия](../.agents/skills/psa-communication/SKILL.md) | [Коммуникация](../knowledge/methods/communication.md) |
| Подготовь проверку эффекта | [План проверки](../.agents/skills/psa-validation/SKILL.md) | [Эксперименты](../knowledge/methods/experiments.md), [метрики](../knowledge/checklists/metrics.md) |
| Проверь финальные материалы перед согласованием | [Критический разбор](../.agents/skills/psa-critic/SKILL.md) | [Вопросы критика](../knowledge/checklists/critic.md) |
| Продолжи после паузы | [Возобновление](../.agents/skills/psa-resume/SKILL.md) | История кейса и материалы текущего этапа |
| Пересмотри выводы при новых данных | [Пересмотр](../.agents/skills/psa-revisit/SKILL.md) | [Доказательства](../knowledge/checklists/evidence.md) |
| Разбери интервью или подготовь модельного собеседника | [Исследование](../.agents/skills/psa-research/SKILL.md) | [Интервью и синтетика](../knowledge/methods/interviews.md) по задаче |

Запиши применённые ID методик, версии и хеш пакета в `analysis/methods-used.md`. Укажи, какой вопрос или вывод изменился.

При выборе инструмента используй `psa tools describe TOOL-ID` из [реестра](../docs/research-tool-registry.md). Описание инструмента не даёт разрешения на его запуск. Проверяй загрузку и перенос по [инструкции для IDE](../docs/ide-instructions.md). Адаптеры обновляй генератором. Детали [автоматизации](automation.md) открывай только по явному поручению.
