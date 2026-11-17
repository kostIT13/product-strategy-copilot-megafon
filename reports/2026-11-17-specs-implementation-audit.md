# Сверка решения с полным ТЗ

17.11.2026 21:51 (Asia/Novosibirsk, UTC+7). Проверен source HEAD `e67bf3f7d19b048ead9877e0d26de07a1e1bff08`.

Основание — весь [specs/case.md](../specs/case.md), разделы1–13. Проверены текущие код/инструкции, tracked demos/examples/evals, host catalog, планы, release policy и доступные результаты проверок. Игнорируемые пользовательские кейсы, секреты и внешние личные хранилища не инспектировались. Отсутствие артефакта ниже означает отсутствие подтверждения в доступном репозитории/ссылках, а не утверждение о всех файлах команды вне репозитория.

**Вывод: полностью ТЗ ещё не закрыто.** Основной файловый workflow реализован; есть синтетический human-approved проход R3 и технические проверки. Не завершены доказательная приёмка IDE/переносимости/новых задач, измеренная польза и полные затраты, финальный комплект сдачи. Также найдены конкретные ограничения metadata/content checks и дефект source ZIP allowlist. Подготовка P8a не является выполненной оценкой.

## Матрица обязательных требований

«Механика реализована» означает наличие рабочего кода/инструкций/технических сценариев. Это не автоматическое подтверждение смыслового поведения агента на новых задачах.

| ТЗ | Что реализовано | Статус и открытая часть |
| --- | --- | --- |
| §1,§3: проект-папка IDE-агента | AGENTS/workflow/quality/safety,4 skills, knowledge, file CLI и optional FastMCP; IDE ведёт цикл | Формат соответствует. Отдельный автономный LLM runtime не требуется; поведение в fresh IDE session ещё не принято |
| §3: основания, варианты, стратегии, validation, сохранённое состояние | Sources/claims/gaps/options/decisions, drafts/render, typed checks, state/journals | Функциональная механика есть; содержательная готовность показана только на собственной синтетике, не независимой новой задаче |
| §4.1: вопрос/цель/получатель/ограничения, только полезные уточнения | Research skill, brief, structured research-plan draft | Инструкции/структуры есть; адекватность уточнений реальным IDE-агентом не измерена |
| §4.2: документы/таблицы/сайты, привязки и качество источника | TXT/HTML/CSV/JSON, optional PDF/DOCX/XLSX, bounded public HTTP fetch, source IDs/hashes/locators, web provenance | Форматы технически реализованы с объявленными ограничениями. Дата публикации/reliability остаются defaults; нужна содержательная оценка provenance, см. A2 |
| §4.3: исследование от влияющих на выбор вопросов, противоречия/пробелы | ResearchQuestion содержит decision_impact/method/permitted_source/sufficiency; gaps и contradicts; current/stale evidence | Механика есть. Сам research draft/реестр не доказывает, что агент действительно прочитал и сопоставил материалы; live research остаётся непроверенным |
| §4.4: минимум3 содержательно разных вариантов, status quo/stop, tradeoffs | OPTION_ROLES и gate проверяют3 роли, есть benefits/costs/risks/strongest_objection и типы fact/hypothesis/forecast/synthetic | Два tracked demo содержат все эти поля. Но writer/validator допускают пустые детали; смысловая разница механизмов не доказывается count/role check, см. A3 |
| §4.5: product/communication strategy и проверка эффекта | Проверка8 тематических sections, trace/coverage, capability promises, typed baseline/metric/comparison/window/guardrails/owner, arithmetic/numeric checks, human semantic review | Механика реализована и R3 «Слот» принят человеком по отчёту. Это не независимая оценка истинности стратегии/реального спроса; actual business pilot ТЗ не требует |
| §5: вести процесс, показывать прогресс, остановка/уточнение/исправление | Status/next/resume/context, IDE сообщения, authored drafts, correction/withdrawal/rollback/reopen | Частично принято. Stop/cancel принадлежит IDE, generic agent cancel CLI отсутствует; actual host control/последующее продолжение надо наблюдать. Gates на каждом этапе строже буквального требования человека при существенном выборе — UX следует проверить |
| §5: сохранение, recovery без скрытых повторов | UUID exact replay, immutable receipts, pending/recover, locks, version/hash binding и негативные crash/concurrency tests | Файловая механика реализована. Внешний/IDE model execution не объявляется recovered/cancelled по одной metadata записи |
| §5: действия/неизвестные/время/стоимость прозрачны | Events/usage/diagnostics, unknown/null, declared measured/estimated provenance | Частично: механизмы учёта есть, полный честный замер model+tools+retries+human по демонстрации не предъявлен. Invoice-grade automatic verification не требуется ТЗ, допустимы обоснованные approximate estimates |
| §5: перенос в другую поддерживаемую IDE | Generated adapters, stage context, file copy/resume, CLI/manual fallback | Host catalog: Codex/Cursor/Claude/Qwen/SourceCraft capabilities=not_verified. SDK stdio/OS CI не заменяют перенос между actual IDE. Не нужно обещать все5, требуется проверить заявленный scope |
| §6: раздельные инструкции/знания/проект/состояние, provenance и отзыв | agent/,knowledge/,.agents/,case files; source/claim lifecycle, dates/hashes/status/history | Механика реализована. Старый вывод не повышается автоматически до fact; knowledge effectiveness и host loading отдельно не приняты |
| §9: запуск без скрытых настроек, зависимости/платные services | README,uv.lock,doctor,base install,optional extras; нет обязательных .env/DB/model API | Основной запуск подтверждён локально/ранее в CI. Actual IDE/model доступы команды и полный demo cost ещё надо зафиксировать; CI/demo e67bf3f подтверждены success к завершению аудита; это не actual IDE acceptance |
| §10: только разрешённые данные, без secrets/PII, source instruction не меняет правила | Safety instructions, public-address checks, confinement, safe diagnostics, gitleaks, fixtures/selected excerpts | Технические/организационные меры есть. Synthetic injection test не равен доказанной LLM resistance; реальные интервью не проводились, их consent/PII процесс не был испытан |
| §11.1: репозиторий/архив, инструкция и ключевые решения | Git remote, README/docs, package/verify/allowlist, wheel/sdist/source ZIP tooling | Доступ жюри и актуальный clean submission bundle не подтверждены. Allowlist исключает документированный Slot example — конкретный дефект A1 |
| §11.2: демонстрационный проект с исходными материалами/стратегиями | Tracked demo/table-demo, reproducible Slot source package и R3 acceptance report | Только синтетика; основной demo остаётся status=validation, table-demo=completed; accepted Slot working case не коммитится. Бриф МегаФона отдельно в specs/ не найден. Финальный demo с разрешёнными материалами/свежим полным проходом ещё не принят |
| §11.3: обязательное видео≤10min | Требование запланировано в R6/P9 | Готовое видео/ссылка в доступных tracked материалах не найдены |
| §11.4: PDF или документ по ссылке со screenshots/архитектурой/промптами/расходами/ошибками | Markdown runbooks,reports,Mermaid и inventory | Не найдены финальный PDF/документ по ссылке и screenshot set. Markdown-отчёты и схемы сами по себе не закрывают эту форму сдачи |
| §12: анализ/нейротехнологии/имплементация/качество | Много проверяемых инструментов и контрактов | Число tools/tests не определяет оценку жюри. Quality/new-task usability/cost/удобство и measured effect ещё нужны; численные баллы готовности из этого аудита не выводятся |
| §13: измеримая польза компонентов, новые задачи, человеческий выбор | Human choice/gates, trace, limits и stop/exclusion policies | Измеренная independent польза не получена; P7/P8 это явно признают. Один известный synthetic case не доказывает generalization |

## Конкретные находки

### A1. Документированный Slot source package не попадёт в ZIP

[README](../README.md) ссылается на [examples/slot-workshop](../examples/slot-workshop/README.md). [Release allowlist](../src/product_strategy_agent/domain/release_policy.py) не включает examples/: `allowed('examples/slot-workshop/build_case.py')` и `allowed('examples/slot-workshop/product-strategy.md')` возвращаютFalse. Сборщик [package](../scripts/release/package.py) пропускает такие files. Поэтому ZIP по текущей policy исключит именно этот документированный пример и оставит ссылку на отсутствующий материал, хотя clone его содержит. Это вывод по actual predicate/code, не новый release build.

Исправление перед R6: узко allowlist нужный synthetic example, добавить archive/content/link smoke; не включать все пользовательские projects или ignored Slot state/approvals. Сохранённое человеческое согласие нельзя переносить в новые кейсы.

### A2. Source fields существуют, assessment workflow не завершён

[source_import.py](../src/product_strategy_agent/domain/projects/source_import.py) L60–62 устанавливает новым imports `published_at=None`, `reliability='unassessed'`. У tracked demo/table-demo те же значения. [Reader](../src/product_strategy_agent/adapters/persistence/files/source_reader.py) для plain local text подставляет parent directory name в publisher, для документов — None; HTTP [reader](../src/product_strategy_agent/adapters/persistence/files/web_reader.py) использует hostname. Это технический proxy происхождения, не проверенный автор/владелец. Каталог папки нельзя безусловно выдавать за source owner; fetched/accessed date не является publication date.

ТЗ не требует автоматического trust scoring. Нужен воспроизводимый способ сохранить/показать осмысленную проверку известных автора/даты/ограничений и надёжности по current revision, сохраняя unknown там, где данных нет. Rules/checklists уже просят такую оценку, но наличие полей с defaults её не подтверждает.

### A3. Проверка количества/ролей не гарантирует полноту options

[build_option](../src/product_strategy_agent/domain/projects/ledger_records.py) L178+ допускает пустые benefits/costs/risks/strongest_objection; pure builder это подтвердил без создания кейса. [options gate](../src/product_strategy_agent/workflow.py) L96+ проверяет3 roles/current dependencies. Оба tracked demos содержат поля полностью — речь о гарантиях для новой задачи, а не утверждении, что эти demos пустые.

ТЗ допускает осмысленную ручную оценку; оно не предписывает каждый такой validator. Нужны либо completeness checks/явное представление неизвестного, либо доказанный review готового сравнения перед переходом. Формальную роль change нельзя считать доказательством содержательно другой альтернативы.

### A4. P8 automation comparison не заменяет baseline исходного способа работы

[Новый P8 protocol](../evals/p8/protocol.md) сравнивает C1=наш sequential IDE/file workflow и C2=тот же workflow с opt-in automation. Это полезный incremental question для hooks/subagents. §8 ТЗ отдельно называет comparison с исходным manual/plain-chat способом. Старый [M6](../docs/evaluation/README.md) имеет exploratory self-assessment в известном контексте; actual равноусловный baseline ещё не выполнен.

Для основной пользы решения нужен C0=manual или обычный чат против C1; C2 добавляется для оправдания выбранных automation components. Это могут быть отдельные сравнения либо согласованный3-condition design. Independent/blind review — наш способ усилить evidence, а не буквально обязательная технология из ТЗ. Подготовленные пустые templates и passed technical smoke не являются результатами любого из сравнений.

### A5. Отложенная actual IDE/new-case приёмка

[Host catalog](../agent/hosts/catalog.json), [IDE runbook](../docs/ide-instructions.md) и [MCP acceptance](../docs/mcp-host-acceptance.md) не подтверждают fresh host loading/перенос. В [R3 Slot report](2026-11-14-r3-slot-human-acceptance.md) прямо указаны синтетика, отсутствие real research и unknown IDE time/cost. P8 scenario «Тетрадь» пока preparation, не фактический новый product run.

Main agent по ТЗ может оставаться IDE + instructions/skills/CLI; ещё один самостоятельный Python agent/LangGraph не требуется. Для приёмки нужен наблюдаемый проход в реально заявленной IDE, исправление/остановка/resume и перенос в другую заявленную среду. Native MCP/hooks не обязательны для CLI fallback, если так честно заявлен scope; нельзя обещать непроверенные native возможности.

### A6. Финальные материалы и описание архитектуры

В tracked files не найдено PDF/DOCX/video/screenshots; в README/docs/reports/examples/evals не найдены готовые submission video/document links по проверенным распространённым hosting patterns. Это не исключает существование материалов вне доступного репозитория. Обязательное видео и PDF/linked document со screenshots/моделями/сервисами/инструкциями/time/cost/errors/help/limitations остаются неподтверждёнными; доступ жюри — отдельная проверка владельца.

[diagrams/mvp/README.md](../diagrams/mvp/README.md) до сих пор говорит, что полная система планирует PostgreSQL. Это противоречит актуальным README/R2/основному плану. Исправить описание перед сдачей; возвращать DB ради устаревшего текста не нужно.

## Дополнительные/архитектурные возможности: не все являются обязательным checklist

| §7–8 | Фактическое состояние |
| --- | --- |
| Интервью/consent; модельные респонденты | Safety rules есть; dedicated interview/respondent procedure/runtime и consented real study не найдены. Generic synthetic fixture не является simulated interview capability |
| Images/audio/video/UX | Dedicated multimodal analysis/transcription/OCR/UX pipeline не найден; PDF text layer не является image understanding. Функции самой IDE не проверялись |
| Анализ данных | CSV/XLSX capture, visible cells/native locators, structured metric/baseline/period/unit,4 explicit arithmetic operations и numeric checks; не общий статистический пакет/исполнение spreadsheet formulas |
| Решения/пересмотр | Owner/revisit trigger/linked evidence, revision/correction/withdrawal/reopen/rollback и notifications реализованы; actual business pilot не является обязательной предпосылкой плана проверки |
| Skills/hooks/subagents/MCP |4 skills, fixed local opt-in hooks, role handoffs/journal/review и FastMCP/CLI реализованы; autonomous/native role dispatch и host acceptance не объявлены выполненными |
| Search/knowledge/memory/routing | Stage context, file memory/current literal search и tool registry есть; semantic/graph retrieval и automatic model routing не реализованы в основном IDE пути. P7b candidate отклонён по precision loss, RAG/provider не включён |
| Польза компонентов | Synthetic retrieval/technical invariants измерены в узких scopes; product/agent gain ещё не подтверждён. Нельзя превращать число компонентов в доказательство качества |

ТЗ не требует одновременно Docker/Postgres/SQLite/LangGraph/FastMCP конкретной марки, всех форматов media, всех5 IDE, native autonomous subagents или RAG. Требуются полезность выбранных решений, честные границы, основной сценарий и переносимость. Неподдержанная optional capability не считается реализованной только потому, что среда потенциально умеет её выполнять.

## Что проверить/доделать в первую очередь

1. Исправить A1/A2/A3 и documentation drift в объёме, необходимом реальному research/demo path; не возвращать retired infrastructure.
2. Пройти fresh IDE research case на разрешённых материалах: показать source assessment, вопросы/contradictions/gaps,3 разных варианта, действительный выбор человека, две стратегии/validation и resume. Синтетику явно маркировать; не требовать реального бизнес-пилота или закрытых данных.
3. Уточнить supported host scope и реально проверить другой заявленный IDE/перенос. Проверять ровно заявленные native функции; generic cancel/stop может обеспечиваться host, но его поведение нужно наблюдать.
4. Добавить к eval основной C0→C1 comparison, выполнить равноусловные прогоны с cost/time/human help/errors; C1→C2 использовать для incremental automation benefit. Не называть подготовку результатом. Обоснованные approximate costs допустимы; не обязательно строить billing integration каждого provider.
5. Собрать свежий clean submission archive/доступ жюри, финальный demo, обязательное видео≤10min и PDF/linked document со screenshots и полным описанием §11.

## Проверки, выполненные в этом аудите

`psa doctor`: ready (Python3.12.7,uv0.11.30,FastMCP установлен; наличие config, без вывода secret values). `scripts.ci.demo`: оба synthetic demos OK,2 citations/14 covered paragraphs, read-only corpus сохранён, render revalidated,model_calls0. `scripts.ci.research_smoke`:11 checks OK,4.5305614s, own temporary fixture, no gates/decision/network/model; final_case_ready=false после намеренного withdrawal. Source/option/release predicates прочитаны и проверены без модификации user cases. Harness sync9/docs263/Ruff/diff и native Gitleaks history/tree/negative probes OK для итогового audit export.

На начальном remote наблюдении CI ещё выполнялся; к завершению аудита [CI e67bf3f](https://github.com/kostIT13/product-strategy-copilot-megafon/actions/runs/44104919519) и [demo e67bf3f](https://github.com/kostIT13/product-strategy-copilot-megafon/actions/runs/44104919614) подтверждены completed/success. Это observed green проверенного source HEAD, не semantic/native acceptance. Полный unit suite локально повторно не запускался; новый release build, native acceptance, real research и independent evaluation этим audit не выполнялись. Последующий audit-only commit может запустить отдельный новый CI и не получает success автоматически от прошлого run.

Аудит не исправляет implementation автоматически и не меняет main plan/authorizations. Все находки относятся к указанному source revision; production-readiness milestones шире буквального ТЗ и не должны подменять необходимые доказательства/материалы сдачи.
