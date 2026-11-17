# Исправления GitHub Actions: demo bytes и Windows TEMP

17.11.2026 19:57 (Asia/Novosibirsk, UTC+7).

## Причины из удалённых логов

В [CI d45765c](https://github.com/kostIT13/product-strategy-copilot-megafon/actions/runs/44086558965) base-install/docs/secrets прошли, Ubuntu unit завершились ошибками demo integrity. [Demo того же commit](https://github.com/kostIT13/product-strategy-copilot-megafon/actions/runs/44086558718) падал с `Generated artifact changed or is missing`. В предыдущем [Windows unit](https://github.com/kostIT13/product-strategy-copilot-megafon/actions/runs/44084029819/job/134041639039) массовая первичная ошибка — `workspace path escaped its root`; сбои child interruption/recovery были её следствием.

1. Десять generated Markdown двух synthetic demos в рабочем Windows checkout имели CRLF и точно совпадали с manifest, но Git хранил LF. На Linux checkout hashes переставали совпадать. Добавлен `/projects/** -text` в `.gitattributes`; сохранены существующие проверенные bytes десяти файлов, без изменения текста, manifest/hash declarations, state или gates. `.gitattributes` включён в source archive allowlist. Scoped whitespace policy разрешает CR в конце строки, сохраняя обычные whitespace checks.
2. `confined` сравнивал resolved child с lexical root. Системный alias выше TEMP на Windows меняет canonical location; сравнение давало ложный escape. Теперь сравниваются оба resolved пути, но lexical walk по самому root и его внутренним путям по-прежнему отклоняет symlink/junction. Traversal/absolute paths и настоящий resolved escape остаются ошибкой.

Коммиты: `1189669` (byte-preserving checkout и regression), `615d507` (resolved-root comparison и regression). Actions YAML, required checks, strict evidence policy, resource limits и production gates не ослаблялись. Пользовательские кейсы, БД, private IDE config, согласования и source data не изменялись. В Git обновлены только уже отслеживаемые synthetic generated demo files с доказанным соответствием прежним manifest.

## Локальная проверка на момент записи

- Path regression:3 tests OK,0.014s; ancestor alias смоделирован, root/internal link и escapes запрещены.
- Git-index checkout regression:1 test OK,1.065s; обе ОС-политики autocrlf true/false и оба demo, проверяются реальные source/render hashes из staged/index bytes.
- Existing CI checks:6 tests OK,10.937s; demo replay/read-only и deliberate quote/locator errors проходят.
- Distribution:5 tests OK,0.856s, включая allowlist и отказ tampering/traversal/symlink.
- Итого15 различных целевых tests OK. Ruff/harness sync-check9/docs254/native Gitleaks history/tree/negative probes/diff checks OK.
- Точная demo-команда завершилась OK:2 cases,14 covered paragraphs,2 citations,model_calls0; read-only bytes сохранены, render revalidated. Полный local suite на момент записи ещё выполняется. Отдельный push запускает новую Linux3.11/Linux3.12/Windows3.12 Actions matrix и demo; окончательный статус нужно читать на GitHub для исправленного HEAD. Эта запись не заявляет remote green до завершения jobs.

Fix не закрывает native R1/M8, независимую оценку M6 или весь P7. После стабилизации CI возвращаемся к P7c — versioned registry существующих research tools. Новые paid/model calls и release publication не выполнялись.


## 17.11.2026 20:19 — уточнение по полным suites

Локальный full620 завершился за1092.337s с3 privacy subtest failures и1 Windows symlink skip: read_text oracle нормализовал CRLF, хотя service сохраняет bytes. На GitHub46dc863 Linux3.11/3.12 и demo прошли (Ubuntu3.12:620 tests,206.273s,OK), Windows620 за789.622s дал6 failures/1 error: тот же privacy oracle,3 canonical-vs-RUNNER~1 path assertions и demo CLI resume с непрезентабельной кириллицей в default pipe encoding.

Исправлены только test oracles: trusted role читается bytes.decode UTF-8, expected workspace paths разрешаются canonical resolve. Privacy/security assertions остаются строгими. CI/demo/release теперь задают PYTHONUTF8=1 для одинакового subprocess encoding. Отдельно воспроизведён resume exit1 при cp1252 и exit0 с valid UTF-8 stdout в UTF8 mode. Runtime role content, human controls, CLI/MCP interfaces и timeout/required checks не менялись.

Targeted повтор: privacy5 OK (11.663s), workspace11 OK (11.826s),CI6 OK (10.558s). С предыдущими path/checkout/distribution —31 различных targeted tests; R1/M6/M8 не закрыты. Повтор всей матрицы запускается новым push; full локально повторно не запускался, поскольку оставшиеся причины воспроизведены и проверены узкими suites, а удалённая полная матрица обязательна. Текущая запись не называет предыдущий failed Windows run зелёным.
