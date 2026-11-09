# R2: IDE-authored research draft и файловый commit — 9 ноября 2026, 18:16 (Asia/Novosibirsk)

## Что реализовано

Отдельные typed ResearchPlan/ResearchQuestion/RecordResearchArtifact, port/service, filesystem bundle codec/journal repository, CLI group и MCP adapter. IDE-агент подаёт план исследования напрямую: kind, author, content, operation UUID, expected_version и expected_case_hash. API run/модель/БД не требуются. Автор — заявленная метка; результат всегда draft_only, без человеческого gate/решения/публикации.

Новый journal CASE/.psa/artifacts содержит immutable operations с шестью связанными файлами: request.json, artifact.json, artifact.md, event.json, receipt.json, base-snapshot.json и отдельным manifest.json. Под общей OS project lock сверяются версия и hashes известных входов, сохраняются bytes/manifest с fsync, после проверки единственная atomic replacement HEAD.json публикует всю операцию. Readers захватывают один HEAD, проверяют hash-linked chain и полный bundle. Genesis тоже публикуется целым каталогом, missing/corrupt HEAD не превращается в пустой журнал.

Exact replay того же normalized request/operation UUID возвращает прежний receipt, включая историю после новых версий; другая команда с тем же UUID отклоняется. Uncommitted preparation не видна в show; pending только инспектирует её, recover требует точный UUID, целую preparation, прежний predecessor и совпадающий case hash. Crash после HEAD reconciles без второй версии. Partial/corrupt files не создаются заново пустыми, committed history не откатывается автоматически.

Case snapshot сохраняет hashes state, 8 реестров, brief/research author inputs и 3 известных strategy/validation drafts, без копирования корпуса. Show показывает базовый snapshot и changed_input_files. expected_version относится к новому artifact journal; legacy writers ещё не транзакционны, что явно отражено в status. Это не доказательство semantic качества или неизменности источников, прочитанных вне этого списка.

CLI: artifact status/record/show/pending/recover с --projects-dir и --operation. Пять tools файлового psa-mcp используют тот же core; read/write/idempotent/open-world hints проверены. PG psa-main-mcp этим срезом не расширялся. Markdown выводит untrusted content как indented JSON. В журнале ограничены чтения файлов (512000 bytes) и история (1000 операций); новая версия сверх лимита отклоняется до записи, не делая HEAD нечитаемым. Автоматическое удаление/compaction отсутствуют.

## Проверки

Все 226 unit-тестов прошли; 15 новых покрывают:

- read-only status без создания journal, typed schema/strict version/extra-field rejection и отсутствие изменений legacy файлов;
- committed replay после новых версий, collision и stale case/version, snapshot differences, перенесённый каталог и project scoping;
- реальные subprocess kill во время записи, перед HEAD, после HEAD, после HEAD temp; invisible preparation, OS lock и recovery без второго commit;
- два процесса с одной expected_version, partial/tampered preparation, missing/corrupt HEAD и изменённый committed content;
- предел истории без публикации нечитаемой версии, rendering source text как данных;
- фактический CLI и отдельный FastMCP stdio процесс: одинаковые status/record/show/pending/recover и проверенные annotations, без API-ключа.

Оба файловых demo прошли validate/verify/coverage/resume/render в временных копиях, model_calls=0. Ruff, instruction-sync и forbidden-path/full-history прошли; docs (141 документов), diff и финальный instruction-sync прошли. PG/Docker/реальные model API и .env не использовались, новые зависимости не добавлялись. Рабочие кейсы в Git не создавались. Native Gitleaks остаётся R2; старый Docker scanner в этой итерации не запускался.

## Следующий шаг и границы

Новый structured research_plan — отдельный reviewable draft, root 02_research-plan.md остаётся legacy author input. Автоматической двусторонней синхронизации и gate approval нет. Дальше R2 — научить workflow потреблять конкретную structured версию/проверенное представление, затем переносить нужные readers/writers на общий commit protocol. Только после verified mapping/import/parity выводятся старые SQL/контейнерные dependencies и CI. Это ещё не полная замена PG backend.

Legacy/manual writer может изменить входы после проверки хэша: show это отмечает, но общий атомарный case snapshot не заявляется до переноса writers/readers. Гарантия касается участвующих writers и локальной FS; hash не является цифровой подписью или сертификатом physical power-loss durability. Неполная genesis preparation не содержит user draft, её явный retry не повторяет paid operation. История/неопределённый outcome не очищаются автоматически.

Планы, README и docs/file-core.md обновлены, новый контракт — docs/research-artifacts.md. Реальные IDE проверки R1/M8 и независимая M6 остаются отложенными. Длительность отдельно не замерялась.
