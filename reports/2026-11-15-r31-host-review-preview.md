# R3.1/P4c — report review/adoption и disabled Codex preview

Завершено 15.11.2026 19:33 (Asia/Novosibirsk). Разработка репозитория; native host acceptance/activation не выполнялись.

## Сделано

- Shared observation record store получил overridable codec/prefix/identity без изменения старого serialized protocol; отдельный review channel .psa/host-acceptance/reviews/v1 использует тот же OS lock, fsync/atomic publication и exact parent validation при read/publish/recover.
- ReviewHostReport/HostReviewRecord и отдельный HostReviewService: report ID/hash, explicit evidence refs, четыре checklist checks, accepted_for_preview/changes_requested/rejected, UUID conflicts/historical replay. Accepted требует current complete reported passes и всех captured refs; отрицательный review может документировать stale report.
- Adoption ограничен disabled preview, без global latest verdict. Observer/reviewer identity не аутентифицированы; host_acceptance_verified/native_activation_allowed/human_approval_granted false. Matrix P4a остаётся not_verified и не повышается по reviews.
- HostPreviewService и Codex MCP stdio renderer: существующий абсолютный interpreter path, fixed module argv/cwd, TOML literals, enabled=false/required=false, prompt approval и parallel hint false. Bootstrap без review явно not_reviewed, explicit selected review требует exact current scope. Existing config не читается/не изменяется, merge не выполняется, runtime интерпретатора не проверяется и не запускается.
- CLI review-prepare/record/show/pending/recover/preview-codex и шесть FastMCP tools. Raw captured evidence только по explicit include_evidence, default metadata. Четырём существующим inspection tools добавлены readOnly annotations; preview allowlist проверен настоящим discovery и включает только psa_status/psa_validate/psa_verify/psa_coverage.
- Использован skill openai-docs для проверки Codex config format; сверены официальные [MCP guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) и [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) 15.11.2026. Это documentation check, не проверка установленной версии.
- [Runbook](../docs/host-review-preview.md), README и планы обновлены: P4c implemented, далее config merge/enable/disable/migration и actual native acceptance. R3.1/R1/M6/M8 открыты.

## Проверки

- Final review/preview suite9,22.622 s,OK: parent/hash/refs/checklist/failed/stale/UUID negatives, explicit selection, valid disabled TOML/no existing config IO, CLI/real-stdio parity и реальная read-only tool allowlist. Три process-kill boundaries partial/prepared/committed, перенос копии, сохранность later instructions, отсутствие parent блокирует recovery.
- Observation regression10,21.980 s,OK после codec refactor. P0 contracts12,0.048 s,OK. Итого31 разных целевых tests.
- Чистая base-установка без MCP/LiteLLM:9,11.663 s,OK (1 ожидаемый MCP skip). Existing base completed/copy/resume/reopen/reapprove smoke OK,model_calls0/sql_dependenciesfalse.
- Первый stdio прогон обнаружил CLI-only context в предложенном allowlist и отсутствие readOnly hints у старых inspection tools. Исправлены allowlist/annotations, указанный финальный suite повторён успешно.
- Ruff/sync9/tracked Markdown links/git diff checks и native Gitleaks8.30.1 history/tree/negative probes проверены. Full unit suite всего репозитория не повторялся; новые механизмы, прежний journal/base workflow проверены отдельно.

## Коммиты и границы

8827879 — shared immutable channel codec; 987a58e — review/disabled preview core; 7df38bb — CLI/MCP и allowlist; b7db5a7 — process recovery tests. Итоговый docs commit сохраняет отчёт/планы.

Предлагаемый Codex фрагмент не записывается в .codex/config.toml и всегда отключён. Для остальных hosts/features renderer пока не реализован, это не заявление об отсутствии их vendor capabilities. Review принимает только основания для подготовки preview; точный будущий config/launch runtime identity и разрешение activation остаются отдельными шагами. Raw evidence/checklist/outcomes — данные, не authority; helper не удостоверяет истинность теста или личность reviewer. Power-loss/NAS/OS sandbox не заявлены. Действующее откладывание live IDE проверки сохраняется. Пользовательские/global IDE settings, рабочие кейсы/.env/БД/volumes не читались/не менялись; тесты synthetic, native hooks/subagents/модели/внешняя передача не запускались.
