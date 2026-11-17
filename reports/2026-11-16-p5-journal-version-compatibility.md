# P5c — namespace compatibility и upgrade/rollback policy

Дата: 16.11.2026 17:39 (Asia/Novosibirsk). Ветка feature/main-solution-roadmap.

## Реализовано

Общий persistence namespace guard вызывается до поиска записи в task/hook/host observation/review/config v1 stores. Если существует только неизвестный v2, смешанный v1/v2, файл вместо версии, неканонический V1 либо чужой entry, доступ отказывает. Неизвестная история не считается пустой и не разрешает новую публикацию. Scan bounded, confinement сохранён; ошибки не отражают private names/contents.

Известный reviews companion разрешён в host-acceptance; review channel дополнительно проверяет свой namespace. Config plan/apply/historical replay/show/audit/recover проходят ту же границу. CLI и реальный FastMCP проверены на refusal без частичного ответа или изменений config/journal.

Published v1 schemas не менялись. Совместимая backup-копия возвращает прежний receipt без новой записи config, исходная история с неизвестным namespace сохраняется. [Runbook](../docs/journal-version-compatibility.md) описывает согласованную приватную копию, проверку upgrade на копии и rollback совместимым кодом/backup без смешивания snapshots. Будущая cross-schema migration требует конкретной целевой схемы и отдельного конвертера; такого конвертера сейчас нет.

## Проверки

- Namespace + directory negatives7,14.354 s,OK: пять stores/channels, future-only/mixed/file/alias/unknown entry, read/pending/recover отказ, byte preservation, missing/known empty v1, apply/replay guards, compatible copy replay. P5b early enumeration/junction checks сохранены.
- Task journal12,39.541 s,OK; hook runs11,59.701 s,OK; host acceptance/reviews/config/profiles43,58.171 s,OK. Проверены process termination/copy recovery и реальный CLI/FastMCP replay/refusal/parity.
- Итого73 разных целевых tests. Full repository suite не запускался. Независимые suite шли параллельно; времена не являются benchmark production.
- Чистая base-установка без MCP/LiteLLM: namespace/directory7,11.950 s,OK; base completed/copy/resume/reopen/reapprove smoke OK,sql_dependencies=false,model_calls=0.
- Ruff, sync9, tracked Markdown links, git diff checks и native Gitleaks8.30.1 history/tree/negative probes проверены перед push.

## Коммиты

eadebaa — namespace guards и negative/copy-compatibility tests.
82d3a52 — CLI/real-MCP refusal parity.
Итоговый docs commit фиксирует runbook, планы и timestamp отчёт.

## Границы

Namespace check не заменяет record validators и не превращает pending в полный аудит всех final records. Реальные исторические binaries, cross-schema conversion, native IDE acceptance и power-loss/NAS не проверялись. Устаревший binary без нового guard нельзя считать защищённым этой правкой. External path substitution вне participating lock не является покрытой транзакцией.

Все mutations выполнены только на временных synthetic fixtures. Реальные IDE configs, рабочие кейсы, .env и БД/volumes не менялись; native subagents/hooks не активированы, внешние модели не вызывались. Private данные не коммитились. P5 частичный; далее P5d privacy/injection diagnostics. Live P4, R1/M6/M8 открыты.
