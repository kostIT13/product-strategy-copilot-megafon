# R3: исправление claim с аудитом и актуальными источниками

Завершено: 11.11.2026 00:37 (Asia/Novosibirsk). Ветка `feature/main-solution-roadmap`. Время завершения и итоговые проверки — в development-log.md; длительность отдельно не замерялась.

## Сделано

Добавлены отдельные domain command/planner, application service/port, filesystem bundle codec и тонкие CLI/MCP interfaces. `psa claim correct CASE C-ID --replacement PATH --by PERSON --reason REASON` и `psa_correct_claim` используют один service. Политика требует явного указания человека; schema требует автора и причину. Typed replacement создаёт следующий C-ID с supersedes, original JSONL prefix сохраняется. Событие хранит обе записи, hashes, автора, причину, время и impact. Decisions/options/capabilities/approvals не переписываются.

Ссылки нового claim проверяются по текущему hash-checked source snapshot и точной цитате внутри locator scope. Все references, включая interpretation, требуют непустых цитат; ветвление replacement запрещено. Допускается исправление отозванного claim без возвращения ему active status. Current citations подтверждают точность выдержки, не истинность или semantic/numeric alignment.

Workflow v5 публикует claims/state/events через общий lock/ACTIVE/receipt protocol; старые v1–v4 reconstruct/replay сохранены. Новый codec реконструирует fixed targets/result/event из captured request/inputs. Повтор завершённого UUID возвращает прежний результат до чтения источников и не сбрасывает позднейшие writes. Generic pending/recover поддерживает interruption в любой проверенной точке.

Promise reader и reported baseline принимают v5 correction proof с текущими hashes/revision events. Effective projection/impact исключает прежнее основание, renderer v2 показывает audit. После correction новый validation gate требует свежую v2 generation. Base smoke теперь проходит через correction и использует новый claim в дальнейших supports/decision. Канонические quality instructions, 9 generated adapters, README, MCP/recovery docs и оба плана обновлены.

## Проверки

Восемь targeted tests: append/history/choices preservation; binding после source revision и reported baseline; malformed attribution, unsupported source/locator/quote, missing quotes, version/hash/busy; withdrawn target/chain/no branching; replay без источника; rehashed result tampering; реальные остановки отдельного процесса на семи границах с copy/recover/later writes; CLI и реальный FastMCP stdio parity.

Чистое базовое окружение без SQL/model/parser/MCP extras прошло completed workflow с correction/copy resume. Оба demo прошли в копиях с неизменными исходными файлами и 0 model calls. Ruff, instruction sync, docs и repository history прошли; native Gitleaks 8.30.1 проверил историю/рабочий export/отрицательные пробы без находок. Полный unittest suite: 354 tests за 437.485 s, OK (1 skipped: Windows symlink privilege unavailable). Последний targeted прогон: 8 tests за 48.234 s, OK. Финальные docs: 174 Markdown documents, без ошибок.

## Что дальше

R3 остаётся открытым: явный review/reopen завершённого workflow, source withdrawal и semantic/numeric consistency. Положительный структурный check не даёт разрешения на публикацию/эксперимент. Attribution не является authentication, структурный impact не обнаруживает все смысловые зависимости. Live R1/M8 и независимая оценка M6 остаются отложенными. Production-ready roadmap будет отдельно расширен после R3; hooks/subagents автоматически не включались.

Реальные продуктовые кейсы, .env и пользовательская БД не читались/не менялись. Вызовов моделей и платных API не было; стоимость/время IDE-сессии не измерялись. БД, контейнеры и отдельный agent loop не добавлялись.
