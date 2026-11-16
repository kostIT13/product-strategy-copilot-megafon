# P4c: review отчётов и disabled Codex MCP preview

Продолжение [P4b observations](host-observations.md). Новые операции сохраняют явную оценку конкретного immutable отчёта и готовят отключённый конфигурационный фрагмент. Native support/activation остаются not_verified/false, матрица P4a не повышается.

## Review/adoption

```powershell
psa host review-prepare --report REPORT_UUID --instructions-root .
psa host review-record --request review.json --instructions-root .
psa host review-show --operation REVIEW_UUID --instructions-root .
psa host review-pending --instructions-root .
psa host review-recover --operation REVIEW_UUID --instructions-root .
```

Prepare возвращает точный report/hash, checklist и scope freshness. Raw captured evidence включается только при явном `--include-evidence`; по умолчанию остаётся локально. Для review.json задаются schema_version1, новый operation_id, report_operation_id, expected_report_hash, reviewed_by, reason, verdict, evidence_ids и checks.

Checklist требует четыре ключа: scope_matches, evidence_read, outcomes_supported, limitations_recorded. Verdict: accepted_for_preview / changes_requested / rejected. Для accepted нужны все checks=true, все captured evidence IDs, reported passes по обязательным проверкам и current scope. Неверные refs/hash, неполный checklist и конфликт UUID отклоняются. Отказ/запрос изменений допускает stale отчёт, сохраняя отрицательные результаты.

Adoption ограничен **подготовкой disabled preview**. Reviewer/checklist — заявленная оценка, не аутентификация личности или доказательство реальности native tests. Verdict не принимает runtime/config как проверенный и не даёт разрешения включить сервер. Reviews индивидуальные: нет автоматического latest verdict/глобального переключателя. Для связи с preview явно выбирается конкретный REVIEW_UUID; host/version/platform/feature/mode должны совпасть.

Review store использует отдельный .psa/host-acceptance/reviews/v1 канал и общий с observations OS lock. Hash/ID родительского отчёта проверяется при чтении, публикации и recovery. Exact replay исторический; новые инструкции не откатываются. Prepared review восстанавливается только при валидном exact parent; partial/corrupt bytes сохраняются. Старый observation record protocol не изменён. Локальные records остаются ignored/private.

## Конкретный preview

```powershell
psa host preview-codex --request codex-mcp-plan.json --interpreter ABSOLUTE_PYTHON_PATH --instructions-root .
psa host preview-codex --request codex-mcp-plan.json --review REVIEW_UUID --instructions-root .
```

Поддержан один renderer: Codex/mcp_stdio/native с локальной platform scope. Host version остаётся заявленным caller контекстом. Bootstrap preview без review получает not_reviewed; выбранный accepted/current review — selected_for_preview. Оба возвращают только фрагмент, hash и metadata. Наличие bootstrap пути позволяет подготовить первое подключение без выдуманной успешной host-проверки.

Фрагмент для `.codex/config.toml` содержит `[mcp_servers.psa]`, существующий абсолютный interpreter path, фиксированные args `-m product_strategy_agent.mcp_server`, cwd и **enabled=false**. Allowlist включает только реально зарегистрированные read-only tools: psa_status/psa_validate/psa_verify/psa_coverage; approval mode prompt, parallel hint false. Документированные поля сверены 15.11.2026 по [MCP guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) и [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference). Проверка формата не является приёмкой установленной версии host.

Renderer экранирует значения как TOML-compatible literals; tests разбирают результат через tomllib и сверяют tool names/annotations с настоящим stdio discovery. Интерпретатор только проверяется как существующий local file: Python/MCP runtime им не запускается и не подтверждается. Артефакт не содержит добавленных tokens/env settings и не меняет действующую политику унаследованного окружения хоста.

`configuration_written=false`, `execution_started=false`, `native_activation_allowed=false`, `host_acceptance_verified=false` сохраняются всегда. Существующий config не читается/не разбирается/не перезаписывается, fragment требует отдельного merge. [P4d disabled-only plan/apply/restore](host-config-lifecycle.md) реализован отдельно с exact config hashes; enable/cross-version migrations остаются будущими срезами; bootstrap/accepted preview сами по себе не дают права на эти действия. Для прочих adapters сохраняется последовательный fallback, renderer не утверждает отсутствие vendor возможностей.

## CLI/MCP и проверки

CLI code0 означает успешную запись/чтение review либо создание preview, без host approval. Read-only tools: psa_prepare_host_review (include_evidence=false по умолчанию), psa_host_review, psa_host_review_pending, psa_preview_codex_mcp. Пишут только review journal: psa_record_host_review и psa_recover_host_review. Raw source/captured instructions не становятся executable instructions/consent.

Проверены exact report binding, stale/failed/checklist/UUID negatives, disabled TOML/no config IO, CLI/real-stdio parity и partial/prepared/committed process-kill/copy recovery. [P4d controlled disabled merge/lifecycle](host-config-lifecycle.md) реализован; P4 остаётся открытым для native enable/acceptance и cross-version migrations. Действующее откладывание live IDE тестов сохраняется; R3.1/R1/M6/M8 не закрыты.
