# Жизненный цикл проекта

```mermaid
flowchart TD
    INIT[psa init<br/>brief, plan, state и пустые реестры] --> I[intake]
    I -->|человек утверждает бриф| RP[research_plan]
    RP -->|человек утверждает план| SC[source_collection]
    SC --> CHECK{Порог активного режима<br/>и источник / обоснованный gap?}
    CHECK -->|нет| SC
    CHECK -->|да, человек утверждает сбор| ER[evidence_review]
    ER -->|claims и gaps проверены человеком| OP[options]
    OP -->|status quo, stop, change| ST[strategy]
    ST -->|решение человека и черновики| VA[validation]
    VA -->|план проверки отрендерен и утверждён| DONE[completed]

    MODE[quick_scan / decision_grade / deep_research] -. source threshold и guidance .-> CHECK
    SET[psa mode set<br/>автор + причина] --> MODE
    SAVE[(state.json, approvals,<br/>mode_history, events.jsonl)] <--> I
    SAVE <--> RP
    SAVE <--> SC
    SAVE <--> ER
    SAVE <--> OP
    SAVE <--> ST
    SAVE <--> VA
    RESUME[psa resume / status / next] --> SAVE
```

`quick_scan` требует минимум один источник. `decision_grade` ориентируется на два, `deep_research` — на четыре; для двух последних допускается один источник и открытый пробел высокого приоритета. Каждое прохождение гейта требует автора; переходы не автоматические.
