# Архитектура MVP

```mermaid
flowchart LR
    U[Пользователь / рабочая среда агента]
    CLI[CLI psa]
    HOST[MCP host]
    MCP[MCPServer из официального Python SDK v2<br/>stdio, optional]

    subgraph CORE[Общее Python-ядро]
        WF[workflow.py<br/>этапы, approvals, режимы]
        SRC[sources.py<br/>локальный импорт и явный web fetch]
        LED[ledger.py<br/>claims, gaps, options, decisions]
        VAL[validation.py<br/>validate и verify]
        RND[rendering.py<br/>генерация Markdown]
        CRIT[critic.py<br/>пакет независимой критики]
        USE[usage.py<br/>учёт использования]
    end

    FS[(Каталог проекта<br/>state.json, JSONL, источники,<br/>черновики и артефакты)]
    NET[(Веб-источник<br/>только по явному fetch)]
    MODEL[LLM / внешний сервис<br/>вне runtime-пакета]

    U --> CLI
    HOST --> MCP
    MCP --> WF
    MCP --> SRC
    MCP --> LED
    MCP --> VAL
    MCP --> RND
    MCP --> CRIT
    MCP --> USE
    CLI --> WF
    CLI --> SRC
    CLI --> LED
    CLI --> VAL
    CLI --> RND
    CLI --> CRIT
    CLI --> USE
    WF <--> FS
    SRC <--> FS
    LED <--> FS
    VAL --> FS
    RND --> FS
    CRIT --> FS
    USE <--> FS
    SRC -. explicit HTTP request .-> NET
    U -. separate agent invocation, not implemented by package .-> MODEL
```

CLI и MCP вызывают одни Python-функции. MCP-сервер не содержит отдельной бизнес-логики. Файловое состояние проекта сохраняет переносимость между средами; SQLite, удалённый API-сервер и автоматический router моделей в MVP не включены.
