# Исправление утверждения с сохранением истории

Только после явного указания человека:

```powershell
psa claim correct CASE C-001 --replacement replacement.json --by OWNER --reason "Причина исправления" --operation UUID --expected-workflow-version N
psa claim impact CASE
```

MCP: `psa_correct_claim`, тот же application service и файловый journal. Автор и причина обязательны; имя является self-reported attribution, а не authentication. Replacement — объект ClaimPayload, например:

```json
{
  "text": "Уточнённый тезис по повторно прочитанному материалу",
  "claim_type": "fact",
  "source_ids": ["S-001"],
  "source_locators": ["paragraph:1"],
  "quotes": ["Точная короткая выдержка из текущего текста"]
}
```

CLI читает JSON размером до 64000 байт; повторный CLI-вызов требует исходный replacement-файл. MCP принимает объект. `supersedes` устанавливается в исправляемый ID; несовпадающее значение отклоняется. Допускается до шести source references. Для каждой ссылки обязательна точная непустая цитата в указанном locator scope; используется общий hash-checked snapshot текущих источников. Проверка точности выдержки не подтверждает истинность источника, смысловую достаточность или числовое соответствие тезиса.

## Публикация и влияние

Workflow v5 атомарно публикует append в claims.jsonl и изменения state/events через общий ACTIVE/receipt/recovery protocol. Исходная строка сохраняется побайтно; новая получает следующий C-ID. Событие содержит обе записи, hashes, автора, причину, время и impact. Decisions, options, capabilities и approvals автоматически не переписываются.

Исправить можно active или withdrawn claim без существующего replacement. Ветвление замен запрещено; цепочка C-001 → C-002 → C-003 разрешена. Исправление withdrawn claim не возвращает ему active status. Effective projection исключает старое основание; зависимые решения и capabilities требуют review. Для нового обещания/базового значения нужно явно выбрать актуальные supporting links и исправить authored drafts. Текущее затронутое решение требует нового выбора человека. Completed workflow остаётся историческим фактом.

Новый claim получает binding к текущим source hashes/revision events из v5 bundle. Promise preflight и reported baseline принимают этот proof наряду с прежним v4 claim creation. После correction новый validation gate требует свежий render v2; replay старой генерации и adoption не заменяют его.

## Повтор и восстановление

Одинаковый завершённый UUID/request возвращает прежний результат без повторного чтения источников, новой записи и сброса последующих изменений. Другой request под тем же UUID вызывает conflict. До публикации проверяются expected workflow version, действующие IDs, текущие цитаты и общий case lock.

При сбое используйте `psa workflow pending CASE` и `psa workflow recover CASE UUID`. Bundle содержит captured inputs, request, before/after claims и результат; восстановление реконструирует их семантику, проверяет hashes и before/after targets. Простого пересчёта manifest после подмены result недостаточно. Исторические workflow v1–v4 остаются читаемыми; для v5 нужен обновлённый runtime. Inputs ограничены 4 МиБ, encoded targets/results — 512000 байт; превышение отклоняется без усечения.

Проверены остановки отдельного процесса на этапах preparation/ACTIVE/claims/state/events/receipt/completion, перенос каталога, replay после потери текущего source text, отказ на неверных цитатах/версии/hash и CLI/реальный FastMCP stdio parity. Общие ограничения filesystem/power loss остаются в [recovery contract](workflow-recovery.md). [Явный completed review/reopen](workflow-reopen.md) реализован. Source withdrawal и semantic/numeric consistency остаются следующими задачами R3; live IDE и независимая оценка отложены.
