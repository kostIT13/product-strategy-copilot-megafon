# Источники и доказательства

```mermaid
flowchart LR
    LOCAL[Локальный файл<br/>TXT / MD / CSV / JSON / HTML]
    WEB[URL]
    ADD[psa source add]
    FETCH[psa source fetch<br/>явный сетевой запрос]
    EXTRACT[Извлечённый текст<br/>CSV сохраняется как строки текста]
    HASH[SHA-256 и source_id]
    REG[(sources.jsonl)]
    COPY[(sources/S-*.txt)]
    CLAIM[psa claim add<br/>тип, формулировка, уверенность]
    CIT[Source ID + locator + точная цитата]
    CL[(claims.jsonl)]
    GAP[psa gap add<br/>неизвестное / метод закрытия]
    GL[(gaps.jsonl)]
    VERIFY[psa verify<br/>хэш и точная выдержка]
    RENDER[psa render]
    ART[03_evidence.md<br/>04_options.md<br/>05_strategy.md]
    UPDATE[Повторный импорт того же URI<br/>с новым содержимым]
    ARCHIVE[(sources/history/<br/>source_id/hash.txt)]
    REV[psa revisit list<br/>зависимые claims и decisions]
    ACK[psa revisit resolve<br/>автор, причина, reviewed IDs]
    EVENTS[(events.jsonl<br/>source_revised / reviewed)]

    LOCAL --> ADD --> EXTRACT
    WEB --> FETCH --> EXTRACT
    EXTRACT --> HASH
    HASH --> REG
    HASH --> COPY
    UPDATE --> HASH
    COPY -. старую версию .-> ARCHIVE
    HASH -. новое содержимое .-> COPY
    UPDATE --> EVENTS
    REG --> CIT
    COPY --> CIT
    CLAIM --> CIT --> CL
    CLAIM --> GAP --> GL
    REG --> VERIFY
    COPY --> VERIFY
    CL --> VERIFY
    REG --> RENDER
    CL --> RENDER
    GL --> RENDER
    RENDER --> ART
    EVENTS --> REV
    CL --> REV
    GL --> REV
    REV --> ACK --> EVENTS
```

Локатор `line:N` адресует одну строку, `lines:N-M` — включительный диапазон строк, `paragraph:N` и `p:N` — непустой абзац. `verify` проверяет сохранённую копию и цитату, но сам по себе не подтверждает истинность источника.
