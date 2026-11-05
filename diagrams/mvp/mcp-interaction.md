# Взаимодействие MCP

```mermaid
sequenceDiagram
    actor User as Пользователь
    participant Host as MCP host / агент
    participant Server as MCPServer (SDK v2)
    participant Core as Общая функция Python-ядра
    participant Files as Файлы выбранного проекта

    User->>Host: Просит проверить источники или состояние
    Host->>Server: tools/call psa_status / psa_verify
    Server->>Core: Передаёт project_id и аргументы
    Core->>Files: Читает state.json / JSONL / sources
    Files-->>Core: Локальные записи
    Core-->>Server: Состояние или результат проверки
    Server-->>Host: Результат MCP tool
    Host-->>User: Показывает ответ

    opt Пользователь явно просит загрузить URL
        User->>Host: Просит импортировать URL
        Host->>Server: tools/call psa_fetch_source(url)
        Server->>Core: fetch_web_source(...)
        Core->>Files: Сохраняет извлечённый текст и provenance
        Core-->>Server: Метаданные и source_id
    end
```

MCP stdio — необязательный интерфейс поверх существующих операций. Доступные tools и настройка host описаны в [docs/mcp.md](../../docs/mcp.md). Полноценная проверка подключений в целевых IDE — отдельный пункт плана.
