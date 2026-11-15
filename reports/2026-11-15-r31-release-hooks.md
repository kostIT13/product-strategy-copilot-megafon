# R3.1/P3d — офлайн release checks

Завершено 15.11.2026 18:43 (Asia/Novosibirsk). Локальные явные механизмы P3a–P3d реализованы; далее P4 host capability/adapters/fallback. R3.1 и отложенные R1/M6/M8 остаются открытыми.

## Сделано

- Общий domain/release_policy: allowlist/required files и прежний forbidden_path. Package/CI repository checker переиспользуют политику; чувствительные hidden paths дополнительно исключены из release allowlist.
- Bounded checked_archive/inspect_release: strict manifest metadata/hash/member list, обязательные файлы, безопасные paths/duplicate/case/Windows names, отсутствие symlinks/encryption, wheel/sdist assets и SHA256SUMS/побайтовое соответствие внешних assets. Общий checked_archive используется scripts.release.verify перед распаковкой.
- ReleaseReader port, ReleaseCheckService и ReleaseRun, отдельный fixed release worker с process timeout/watchdog, переиспользующий существующую execution/output boundary. Target связывается с hash сырых manifest bytes; stale/dirty/integrity failures блокируются.
- CLI hook prepare-release/check-release и read-only FastMCP psa_prepare_release_hook/psa_check_release_hook. Release path — явная конфигурация, отсутствует в untrusted packet. Каждая проверка live/read-only, без cached pass и без case journal; CLI0 только passed, blocked/failed CLI1.
- Хук не распаковывает/не исполняет archive code, не устанавливает зависимости, не вызывает модели/сеть и не создаёт tag/draft/publish. Static pass не подтверждает trusted provenance/clean install/полную готовность релиза.
- [Runbook](../docs/release-hooks.md), distribution/MCP/automation docs и планы обновлены. R3.1 сохраняет native acceptance открытым; автоматическая activation выключена.

## Проверки

- Новый release suite10, 27.056 s, OK: реальный worker/timeout, schema/hash/sidecar/path negatives, dirty/stale/tamper recheck, recursion cleanup, CLI/real stdio и отсутствие исполнения инертных packaged bytes.
- Existing distribution5, 1.127 s, OK; P0 contracts12, 0.032 s, OK; прежний preflight CLI/stdio2, 25.120 s, OK. Итого 29 разных целевых tests.
- Чистая base-установка без MCP/LiteLLM:10, 11.054 s, OK (1 ожидаемый MCP skip). Первый CLI прогон обнаружил лишнюю зависимость release-команд от projects_dir; исправлено, указанные финальные прогоны повторены успешно.
- Полная локальная **офлайн** сборка --require-clean: version0.1.0, source commit `370ee657189e6a008dd5fe89c6d6f1bdb7722bdb`, dirty=false; 642 ZIP entries с manifest, 641 проверенный файл и 4 external assets. Итоговая docs/report правка сделана после этой сборки; артефакт не заявляется сборкой финального docs commit.
- Реальный bounded hook на архиве: passed. Manifest SHA-256 `2ebfaaff05cb4c65b560e98cc69f532ce58b2ca2cb3eca6c65370908feaa7d00`; archive SHA-256 `3c6081d020e18f8cc97d30677e4cef447775ea1f5877b79cf53e5fb79de3c1e7`. Локальные ignored assets: dist/hook-release-check/.
- Отдельно от hook выполнен scripts.release.verify с UV_OFFLINE=true: wheel_installed=true, sdist_installed=true, source_imports=false, model_calls0. Doctor/help вне source, оба synthetic demos, base completed/copy/reopen/reapprove прошли установленными wheel/sdist. Ничего не опубликовано.
- Ruff/sync9/tracked Markdown links/git diff checks и native Gitleaks8.30.1 history/tree/negative probes проверены. Общий full unit suite не повторялся; проверены изменённые механизмы, прежние distribution/CLI contracts и полный install/demo path.

## Коммиты и ограничения

bd6be92 — общие policy/archive checks; ebb430d — release service/worker; 370ee65 — CLI/FastMCP/parity. Итоговый docs commit фиксирует runbook/план/этот отчёт.

Это статическая целостность, не signature/авторизация публикации и не secret-content scan. Согласованный manifest сам по себе не удостоверяет автора/remote commit или фактическую чистоту checkout; full verify и CI остаются отдельными проверками. Release hook stateless/live, case journal/recovery P3b к нему не относится; повтор rechecks текущие bytes. Check ограничен wall time/bytes, prepare синхронный; общий CPU/memory/OS sandbox не заявляется. Native IDE hooks/subagents не активированы, реальные модели/внешние сообщения не запускались. Рабочие кейсы/.env/пользовательские БД/volumes не читались/не менялись; build/export читает только allowlisted tracked публичные материалы и synthetic demos.
