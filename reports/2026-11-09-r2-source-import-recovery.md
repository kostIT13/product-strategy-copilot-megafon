# R2: восстановимый source import/revision

Время: 9 ноября 2026, 19:25 (Asia/Novosibirsk, UTC+7). Длительность отдельно не замерялась.

## Сделано

- Local/HTTP source import и создание revision перенесены с разрозненных записей на общий workflow journal v2. Одна операция связывает sources.jsonl, current extracted text, old-text archive при изменении, event и state.
- Добавлены SourceImport command/pure plan, application service/ports, отдельные reader и source payload codec. Legacy sources wrapper сохранил established extraction/IDs/registry shape и стал тоньше; application service не читает filesystem напрямую.
- Общий publisher/recovery расширен derived targets и bounded binary payloads; исторические workflow v1 bundles сохранены. ACTIVE блокирует participating operations, before/after checks защищают каждый source target и unrelated input snapshot, parent directories синхронизируются там, где поддерживается.
- CLI/MCP source add/fetch получили caller UUID/expected shared workflow version. Replay проверяется до local read/HTTP; captured result не перезапрашивается. Recovery после подготовки использует captured bytes, включая old text для архива, без original input/сети.
- New/unchanged content пишут source_imported без фиктивной revision; изменённый hash — один source_revised с current/previous hashes/paths. Unregistered current target, corrupt current/archive, duplicate registry IDs и noncanonical old paths не перезаписываются.
- Версия workflow теперь учитывает source import; review fixtures обновлены по фактическим двум import операциям. Этап/mode/approvals source-операция не меняет.
- Обновлены README, основной план/roadmap и контракты; добавлен docs/source-import-recovery.md.

## Проверено

- Все 274 unit-теста прошли. Восемь новых source tests: реальные kill после подготовки/ACTIVE/registry/text/archive/state/events/completion/завершения; first/same-content imports; exact replay без deleted-file read и повторного HTTP; version/UUID rejection до acquisition; partial preparation и changed-input/target refusal; corrupt/unregistered source protection; portable copy/CLI recovery; настоящий MCP stdio recovery/replay/version.
- HTTP response/redirect проверены через mock, внешняя сеть не использовалась. Final source tests повторены с 600000-byte текстом (больше metadata limit) и отказом от raw input >10 МиБ без изменения state. Тексты/архивы после recovery проверены verify.
- Восемь review compatibility tests также прошли с workflow_version, учитывающей imports. Оба deterministic demo прошли в временных копиях, model_calls=0.
- Ruff, instruction-sync (9 managed files), forbidden-path/full-history, Markdown links и diff checks прошли.

## Границы и далее

Exact replay требует caller UUID; без него запрос создаёт новую операцию. Crash до полного bundle может оставить acquisition без receipt; скрытого повторного fetch нет. Journal/common metadata имеют отдельные limits, raw/saved text — до 10 МиБ. Старый runtime без workflow v2 не использовать для новых source bundles. Raw/manual доступ обходит lock, power loss/NAS не сертифицированы.

Render и остальные нужные legacy writers ещё требуют recovery; затем mapping/import и retire старой SQL/container цепочки. Semantic correction/re-review/quality остаются R3; hash/recovery не доказывают истинность источника и не утверждают стратегию.

БД/Docker/реальные модели не использовались; .env, зависимости и пользовательские кейсы не менялись. Docker-based Gitleaks заново не запускался. R1 live IDE и M6/M8 отложены, R2 не завершён.
