# P5e — dependency и artifact integrity

Дата: 16.11.2026 18:07 (Asia/Novosibirsk). Ветка feature/main-solution-roadmap.

## Изменения

- Package проверяет exact backend/build-group policy и uv lock --check --offline до создания output/build. Verify повторяет preflight на unpacked source до sync/install. Stale graph не обновляется автоматически.
- Build backend закреплён на уже использованном cached setuptools82.0.1, одинаково в build-system и отдельной build dependency-group. uv.lock обновлён offline: добавлен только setuptools82.0.1 с wheel/sdist hashes, удалённых/изменённых версий runtime/extras нет.
- Временные constraints экспортируются из frozen build group с hashes. Isolated uv build использует --require-hashes; verifier wheel/sdist install — hashed local requirement, --no-deps и те же build constraints. Build backend не добавлен в base runtime.
- Install verifier использует общий bounded inspect_release вместо отдельного unbounded checksum pass. Внешние assets/manifest/ZIP проверяются до установки, stale archived lock тоже блокируется.
- [Контракт и сверка рисков](../docs/dependency-artifact-integrity.md), distribution runbook и планы обновлены. Локальные P5a–P5e срезы выполнены; P5 целиком не закрыт, host-зависимые/независимые проверки открыты. Далее независимый P6a diagnostics/outcomes без private texts и без замены unknown usage/cost нулём.

## Проверки

- Final release/dependency suites15,30.453 s,OK; distribution5,1.459 s,OK. Итого20 разных целевых tests. Реальный offline uv отказ на corrupted backend hashes; stale local graph без build/output; stale archived graph без installer; oversized checksum sidecar и changed external wheel до subprocess install. Existing release-hook fixed worker/real FastMCP parity/recheck tests сохранены.
- Clean base без optional extras: dependency5,2.454 s,OK и distribution5,1.345 s,OK. Full repository suite не повторялся.
- Реальная package сборка succeeded: wheel/sdist/ZIP +manifest/SHA256SUMS. Verify последовательно установил wheel и sdist в отдельный base environment Python3.12.7, проверил import из site-packages вне source, doctor/help, оба demo replay и base completed/copy/resume/reopen/reapprove. wheel_installed=true,sdist_installed=true,source_imports=false,model_calls=0; base smoke sql_dependencies=false.
- Ruff, sync9, tracked Markdown links, git diff checks и native Gitleaks8.30.1 history/tree/negative probes проверены перед push.

## Development artifact

Локальный ignored dist/p5e-check/product-strategy-agent-0.1.0.zip. Checked files711,assets4. Manifest commit098fd6815ec2aa3cdd34c542dfc53c5c2843020e,dirty=true: build сделан при разработке, это не архив чистого итогового HEAD и не комплект сдачи. Archive SHA256 eb791d2d4e737d56b329316003b884f08902a63ef70a944a6ad3895ea3597747; manifest SHA256 dc9979cd653840ef26c229ae660e5968ff9752050b9c76022d93700f2de17184. Финальный clean bundle собирается отдельно по P9/R6; публикации/тега не было.

## Коммиты и ограничения

19b7232 — frozen graph/build backend pin/hash constraints.
d06560f — bounded verifier/dependency preflight и negative tests.
Итоговый docs commit фиксирует runbook, планы и timestamp отчёт.

SHA проверяет целостность, не подпись автора; byte-for-byte reproducibility разных builds не заявлена. Полный набор Windows/Linux/Python versions и remote Actions success этой локальной проверкой не удостоверены. Install может получать locked packages из cache/сети; offline preflight не обещает отсутствие потребности в artifacts на чистой машине. Выбор cached backend не является заявлением о проверке его актуальности/CVE.

Workspace code/release metadata изменены по задаче; кейсы и native IDE settings не менялись. Прогоны workflow только на temp synthetic fixtures. .env/БД/volumes и private working данные не коммитились; native subagents/hooks не активированы, внешних моделей не вызывали. P4/R1/M6/M8 остаются открытыми, оставшиеся P5 границы перечислены в контракте.
