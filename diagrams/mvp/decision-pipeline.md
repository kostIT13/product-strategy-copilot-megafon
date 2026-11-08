# Варианты и человеческое решение

```mermaid
flowchart TD
    C[Claims<br/>факты, интерпретации,<br/>гипотезы и прогнозы] --> G[Gaps<br/>открытые вопросы,<br/>приоритет и метод]
    C --> OPT[Сравнение вариантов]
    G --> OPT
    OPT --> SQ[status_quo<br/>оставить как есть]
    OPT --> STOP[stop<br/>закрыть направление]
    OPT --> CHANGE[change<br/>изменить или проверить]
    SQ --> COMP[Польза, затраты,<br/>риски, возражение]
    STOP --> COMP
    CHANGE --> COMP
    COMP --> HUMAN[Человек выбирает вариант<br/>psa decision add]
    HUMAN --> LOG[(decision-log.jsonl)]
    HUMAN --> DRAFT[Продуктовый и<br/>коммуникационный черновики]
    LOG --> RENDER[psa render]
    DRAFT --> RENDER
    RENDER --> PLAN[План проверки<br/>метрики, baseline,<br/>окно и guardrails]
    PLAN --> GATE[Человек утверждает validation]
    GATE --> COMPLETE[Проект завершён]
```

Система формирует сравнимые материалы и сохраняет владельца решения, основания, отклонённые варианты, риски и условие пересмотра. Она не принимает решение вместо человека.
