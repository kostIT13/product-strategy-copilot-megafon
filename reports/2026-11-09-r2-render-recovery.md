# R2: render/adoption через workflow v3

Время: 9 ноября 2026, 19:46 (Asia/Novosibirsk, UTC+7). Длительность отдельно не замерялась.

## Сделано

- Render перенесён с последовательных filesystem writes на общий write-ahead publisher: пять generated Markdown, недостающие author templates, integrity manifest, state/events и completion receipt.
- Выделены RenderRequest/pure plan, version-one Markdown builder/templates, RenderStore port, RenderService и filesystem render bundle codec. Legacy rendering/artifacts wrappers стали тоньше; builder не читает/не пишет filesystem.
- Workflow format v3 хранит captured render inputs, before/after и reproducible result; targets ограничены fixed allowlist. Codec заново строит документы/manifest/event, проверяет snapshots, authorization и неизменность stage/mode/approvals. Исторические v1/v2 packages сохранены.
- Сохранены защита existing drafts и запрет перезаписи untracked/edited generated files. Discard требует explicit actor/reason, event хранит expected/edited hashes. Adoption также journaled и не переписывает Markdown/drafts; compatibility write_render_manifest теперь tracking/adoption, без ложного rendered baseline.
- CLI/MCP render/adopt получили operation UUID/expected workflow version; exact replay не сбрасывает более поздние edits. Shared recovery поддерживает render result и перенос case.
- Обновлены основной план/roadmap, README/контракты; добавлен docs/render-recovery.md.

## Проверено

- Набор вырос до 283 тестов. Первый полный прогон: 282 passed, одна ошибка в CI demo, запущенном до исправления compatibility старого case без optional capabilities.jsonl.
- Исправлено capture-поведение: отсутствующий optional ledger читается как пустой, не создаётся автоматически. Оба deterministic demo затем прошли в изолированных копиях, model_calls=0. Повтор всей CI-группы: все 6 тестов прошли. Повтор полного набора после этого исправления не запускался.
- Девять новых render tests прошли до и после compatibility fix: real process kill на 15 границах outputs/drafts/manifest/commit, exact replay/version/UUID conflicts, manual edits/discard audit, adoption, invalid manifest, before/after/input refusal, перенос case/CLI и настоящий MCP stdio recovery/replay/adopt.
- Авторский CRLF draft сохраняется побайтно. Новый renderer публикует точные captured UTF-8 bytes с соответствующим manifest.
- Ruff, instruction-sync (9 managed files), forbidden-path/full-history, Markdown links и diff checks прошли.

## Границы и далее

Journal v3 требует runtime с v3 codec и сохранения version-one builder/templates для исторического восстановления. Common metadata/target limit — 512000 байт, render snapshot — 4 МиБ; данные не усекаются. Raw/manual доступ обходит lock, power loss/NAS не сертифицированы. Render/adoption не являются quality gate, human selection или разрешением на публикацию.

Остальные canonical ledger/usage writers ещё требуют восстановления после сбоев; затем mapping/import/retire старого контура. БД/Docker/реальные модели не использовались; .env, зависимости и пользовательские кейсы не менялись. Docker-based Gitleaks заново не запускался. R1 live IDE и M6/M8 отложены, R2 не завершён.
