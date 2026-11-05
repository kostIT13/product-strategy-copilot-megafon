# Структура данных проекта

```mermaid
erDiagram
    PROJECT ||--|| STATE : tracks
    PROJECT ||--o{ SOURCE : registers
    PROJECT ||--o{ CLAIM : records
    PROJECT ||--o{ GAP : records
    PROJECT ||--o{ OPTION : compares
    PROJECT ||--o{ DECISION : stores
    PROJECT ||--o{ APPROVAL : advances
    PROJECT ||--o{ USAGE_EVENT : measures
    SOURCE ||--o{ CLAIM : supports
    CLAIM ||--o{ OPTION : informs
    CLAIM ||--o{ DECISION : justifies
    OPTION ||--o{ DECISION : selected_or_rejected
    PROJECT ||--o{ DRAFT : authors
    PROJECT ||--o{ RENDERED_ARTIFACT : generates

    PROJECT {
        string project_id
        int schema_version
    }
    STATE {
        string status
        string mode
        json stages
        json mode_history
        string next_action
    }
    SOURCE {
        string source_id
        string uri_or_path
        string content_hash
        string extracted_text_path
        string status
    }
    CLAIM {
        string claim_id
        string type
        string text
        string confidence
        json source_ids
        json source_locators
        json quotes
    }
    GAP {
        string gap_id
        string question
        string priority
        string status
    }
    OPTION {
        string option_id
        string role
        string name
        string description
        json claim_ids
    }
    DECISION {
        string decision_id
        string owner
        string option_id
        string rationale
        string revisit_when
    }
    APPROVAL {
        string event_id
        string stage
        string approved_by
        string approved_at
    }
    USAGE_EVENT {
        string event_id
        string provider
        string model
        int input_tokens
        int output_tokens
    }
    DRAFT {
        string filename
        string authored_content
    }
    RENDERED_ARTIFACT {
        string filename
        string generated_content
    }
```

На диске `PROJECT` — каталог; состояние, approvals и mode history находятся в `state.json`, события source revision/review также дописываются в `events.jsonl`. Предыдущие извлечённые версии сохраняются в `sources/history/`. Остальные сущности хранятся в соответствующих JSONL-файлах, черновики — в `drafts/`, сгенерированные Markdown-файлы — в корне проекта. Связи в диаграмме показывают смысловые ссылки по ID, а не реляционную базу данных.
