# Восстановимые render и adoption

Обновление R3: новые generations используют [builder v2 с effective claim lifecycle](claim-withdrawal.md). Frozen builder v1 сохранён для исторического replay; формат workflow v3 bundle не меняется. Внутренний builder_version записывается в новые requests, auto replay сохраняет прежнюю business identity.

R2: Markdown, недостающие author templates, integrity manifest и state/events публикуются одной recoverable workflow-операцией. Чистый version-one builder отделён от application service/port и filesystem codec/store. Render не утверждает этап или стратегию.

```bash
psa status CASE
psa render CASE --operation d64591e3-05d1-427a-9a92-72a3ce37112c --expected-workflow-version 0
psa workflow pending CASE
psa workflow recover CASE --operation UUID
```

Файловые MCP `psa_render`/`psa_render_adopt_existing` принимают `operation_id` и `expected_workflow_version`. UUID связывает mode, optional discard authorization/reason и expected version. Exact replay возвращает прежние relative result paths без перезаписи более поздних edits; CLI/MCP превращают paths в текущий case location. Смена request/kind под занятым UUID отклоняется. Без UUID создаётся новая операция. Общая workflow_version увеличивается, status/stages/mode/approvals не меняются.

## Состав операции

Обычный render собирает:

- 03_evidence.md, 04_options.md, decision.md, 05_strategy.md, 06_validation-plan.md;
- отсутствующие drafts/product-strategy.md, communication-strategy.md, validation-plan.md — только из established templates;
- render-manifest.json с точными SHA-256 публикуемых Markdown bytes;
- один render_completed либо generated_artifacts_regenerated event и обновлённые version/updated_at.

Существующие drafts не перезаписываются. Отсутствующие optional ledgers старого file MVP, например capabilities.jsonl, читаются как пустые и не создаются задним числом. Авторские данные/реестры, brief и research plan не переписываются. Builder использует captured input, не модель или сеть. Он не заменяет validate/verify/coverage/quality gates.

## Ручные правки и adoption

При valid manifest изменённый/удалённый generated file блокирует render. Перезапись требует явной команды:

```bash
psa render CASE --discard-generated-edits --by "Владелец правок" \
  --reason "Восстановить производные документы из drafts" --operation UUID
```

Audit event сохраняет authorized_by/reason и expected/edited hashes затронутых файлов. Имя — заявление вызывающего, не техническая аутентификация. Без manifest существующие generated files не перезаписываются даже с discard flags. Повреждённый manifest не считается разрешением на regeneration.

`psa render CASE --adopt-existing` / `psa_render_adopt_existing` сохраняют hashes текущего содержимого через тот же journal, не создавая Markdown/drafts. Это baseline tracking, не approval и не перенос текста в author drafts. При valid manifest и changed files adoption не позволяет обойти discard guard. Invalid/missing manifest можно явно заменить baseline текущих файлов без их перезаписи. Последующий render использует drafts/ledgers; нужный авторский текст следует хранить в drafts.

Compatibility helper `write_render_manifest` теперь также вызывает journaled adoption и записывает adopted_existing baseline: отдельная запись hashes не заявляет, что текст был сгенерирован. Для реальной генерации используется render_project.

## Workflow format v3

Прежние v1 gate/mode/review и v2 source bundles остаются читаемыми. V3 добавляет render-inputs.json, render-before.json, render-after.json, render-result.json. Codec проверяет fixed snapshot/target allowlists, заново запускает version-one builder, проверяет expected manifest/event/result, разрешение discard и неизменность stage/mode/approvals. Произвольные target paths не принимаются. Алгоритм builder/templates v1 является частью этого формата: будущие изменения требуют сохранения v1 reader/builder для истории.

До ACTIVE сохраняется полный bundle; затем общим temp+replace publisher записываются targets, state/events, completion receipt, ACTIVE удаляется последним. Participating readers/writers получают busy/pending, не промежуточный набор документов. Recovery сверяет каждый target с before/after и snapshot остальных входов. Ручные edits, появившиеся после подготовки, не перезаписываются. Copy case с journal позволяет завершить exact operation в другом projects-dir без повторной сборки из новых входов.

Common metadata ограничены 512000 байтами, каждый UTF-8 target — 512000 байтами, каждый render snapshot payload — 4 МиБ. Превышение отклоняется до публикации, текст не усекается. Raw/manual доступ обходит lock, power loss/NAS не сертифицированы. Canonical ledger/usage writers перенесены на workflow v4; перенос/retire старого контура остаётся R2.

Canonical ledger/usage append теперь поддерживает [workflow v4 replay/recovery](ledger-recovery.md); shared version учитывает эти записи, usage business ID отделён от journal UUID.
