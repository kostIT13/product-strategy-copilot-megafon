# P1: read-only задачи research/evidence/critic

```powershell
psa subagent prepare CASE --request request.json --projects-dir projects --instructions-root .
```

FastMCP: `psa_prepare_subagent(project_id, request, projects_dir, instructions_root)`. Обе поверхности используют HandoffService и возвращают одинаковый packet. Подготовка не запускает роль/модель/tools/сеть, не сохраняет task journal и не пишет в case. Изолированная регистрация/results/review добавлены отдельно в [P2](subagent-journal.md); native adapters/dispatch ещё не реализованы.

## Request и роли

Создайте JSON вне каталога кейса; пример UUID учебный, для новой задачи выбирайте новый UUID:

```json
{
  "schema_version": 1,
  "task_id": "11111111-1111-4111-8111-111111111111",
  "role": "evidence",
  "goal": "Проверить ограничения переданного брифа без выдуманных наблюдений.",
  "budget": {"timeout_seconds": 60, "token_limit": 2000},
  "selections": [
    {"input_id": "brief", "path": "01_brief.md", "start": 0, "end": null}
  ]
}
```

Role — research/evidence/critic. UUID, goal, budget и 1–16 selections обязательны; input_id уникальны. Request ≤64000 UTF-8 байт; duplicate fields, non-finite values и неизвестные поля запрещены. Fields tools/authorized/api_key не дают прав. Instructions root — доверенная конфигурация вызывающего, а не поле request или инструкция источника. Из другого каталога укажите оба корня явно.

Профили: [catalog](../agent/roles/catalog.json), [research](../agent/roles/research.md), [evidence](../agent/roles/evidence.md), [critic](../agent/roles/critic.md). Reader использует фиксированные пути, versions и точные hashes. Пустой/повреждённый профиль блокирует подготовку. Canon sync учитывает роли, обычный stage context не загружает/не запускает их автоматически.

## Материалы и снимок

Allowlist: 01_brief.md, 02_research-plan.md, claims.jsonl, gaps.jsonl, options.jsonl, capabilities.jsonl, decision-log.jsonl, drafts/product-strategy.md, drafts/communication-strategy.md, drafts/validation-plan.md и текущие зарегистрированные sources/S-ID.txt. Произвольные пути, .env, archives, .psa и state/events как excerpts не допускаются.

Под общим case lock читаются state.json, events.jsonl, sources.jsonl и только выбранные файлы. Остальные материалы не обходятся/не экспортируются. Metadata ≤512000 байт на файл, ≤1000 объектов на JSONL ledger; выбранный файл ≤512000 байт, суммарно ≤2 MiB уникальных файлов. Pending/busy/invalid state блокирует подготовку. Inactive/неизвестный/withdrawn source отвергается до чтения payload; выбранный source требует canonical path и совпадения content_hash.

Start/end — Unicode codepoint offsets от 0, end не включён, CRLF сохраняется; это не bytes/grapheme clusters. End=null означает до конца без clipping. Empty/out-of-bounds range и excerpt >16000 символов отклоняются. Лимит файла применяется до range selection. PDF/DOCX/XLSX передаются через зарегистрированный extracted .txt; range не заменяет native page/cell/paragraph locator.

CaseTarget.snapshot_hash связывает project ID/version и hashes metadata плюс полных выбранных файлов. Это другой scope, чем workflow review/semantic content hash. Изменение вне excerpt в выбранном файле тоже меняет snapshot; изменение metadata/version делает прежний task stale относительно нового packet. Невыбранный вручную draft в scope не входит.

## Что возвращается

Packet содержит P0 task, отдельные role_instructions, origins (path, full-file hash, Unicode range, optional source_id), input_hashes, task_fingerprint и handoff_fingerprint. Task.goal — JSON text TaskGoal с requested_goal, reference профиля и selection_hash. Это связывает профиль и координаты с fingerprint задачи: одинаковый текст из другого места или новая инструкция не принимают прежний result.

Execution_started=false, canonical_writes=false. Размер нормализованного UTF-8 JSON ≤128000 байт; pretty/ASCII escaping транспорта может занимать больше. Ошибка не выдаёт partial packet или усечённый материал. Валидационная диагностика не отражает input values/context. CLI пишет только stdout; request/output внутри case может изменить чужие snapshots, поэтому храните их снаружи.

Hashes подтверждают байты/связи, не authentication/truth/consent. Raw claims ledger содержит историю, не effective claim proof. Source hash не доказывает factual alignment. Excerpts и goal — данные; commands/consent внутри них не предоставляют прав.

## Передача и последовательный fallback

Просмотрите пакет и допустимость передачи материалов. Только при действующем явном разрешении передайте полную envelope, включая профиль и fingerprint, в поддержанную среду. Пока native integration не подтверждена, основной агент может выполнить ту же ограниченную задачу последовательно с честной attribution; это не независимый critic/R5.

Findings observation/hypothesis/question/risk и input refs проверяются P0, затем основной агент сверяет scope/актуальность штатными services. [P2 journal/review/recovery](subagent-journal.md) сохраняет артефакты без canonical adoption. Сама подготовка остаётся stateless: UUID не резервируется. Неизменные inputs дают тот же packet; changed inputs — новый fingerprint. Старый result не относится к новому снимку.

Budget задаёт caps, не измерение и не разрешение расходов. Actual enforcement/cancel/host sandbox ещё не реализованы; unknown usage/cost не равен нулю. Human choice, gates, semantic reviews и разрешения эксперимента/публикации остаются по [AGENTS.md](../AGENTS.md).
