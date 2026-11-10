# Полнота разделов стратегии: R3, первый срез

```powershell
psa strategy check CASE
```

Файловый MCP: `psa_check_strategy(project_id, projects_dir)`. Оба интерфейса вызывают один StrategyStructureService/reader/domain checker. Команда read-only, не использует сеть/модель и не создаёт approvals или drafts. CLI выводит JSON: exit 0 — structurally complete, exit 3 — incomplete; ошибки доступа/формата завершают команду ошибкой.

## Обязательные разделы

Используйте обычные ATX-заголовки второго уровня (`##`) из существующих templates либо точные English aliases. Регистр и лишние пробелы несущественны. Другие заголовки допустимы как дополнительные, но не заменяют обязательные.

| Файл | ID | Заголовок | English alias |
| --- | --- | --- | --- |
| product-strategy.md | audience_job | Аудитория и задача | Audience and job |
| product-strategy.md | value_alternatives | Ценность и альтернативы | Value and alternatives |
| product-strategy.md | choice_refusals | Выбор и осознанные отказы | Choice and deliberate refusals |
| product-strategy.md | economics | Связь пользы с затратами и доходами | Value costs and revenue |
| communication-strategy.md | audience_situation | Аудитория и ситуация | Audience and situation |
| communication-strategy.md | barrier | Барьер понимания или выбора | Understanding or choice barrier |
| communication-strategy.md | message_proof | Ключевое сообщение и подтверждение | Key message and proof |
| communication-strategy.md | channels | Роль каналов | Role of channels |

Файлы лежат в `drafts/`. Раздел должен содержать prose, а не только heading, trace markers или placeholders. Структурный минимум — 24 буквенных символа после исключения trace markers; TODO/TBD/«Заполните/Укажите/Опишите» и аналогичные подсказки блокируют раздел. Это эвристика против пустых templates, не измерение качества анализа. Явный `[OPEN QUESTION]` с описанием неизвестного допустим; числа, которых нет в источниках, подставлять не нужно.

HTML comments, fenced/indented code и headings не считаются prose. H3+ подразделы остаются внутри текущего H2. Новый неизвестный H2 или H1 прекращает текущий раздел. Дубли обязательных разделов, незавершённые fences/comments и отсутствующие документы дают incomplete. Parser намеренно ограничен этим plain Markdown contract: произвольные локализованные/декорированные заголовки и setext headings автоматически не интерпретируются.

## Packet и gates

Ответ содержит status/line/prose_letters для разделов, issues, version и SHA-256 входных state/draft файлов. `review_hash` связывает весь canonical report со snapshot, включая raw input hashes. Комментарий или новая версия state также меняют hash. Flags semantic_alignment_verified/publication_approved false, requires_human_review true: заполненный заголовок с текстом не доказывает различимость альтернатив, соответствие выбора человеку, экономическую состоятельность или согласованность двух стратегий.

Новые strategy gates требуют одновременно прежние substantive/decision/coverage/promise checks **и** полную структуру. Validation gate проверяет её заново после integrity check generated artifacts. Успешное явное human approval сохраняет strategy_structure hash/status/version в audit event; promise_preflight reference сохраняется отдельно. Нельзя получить разрешение на публикацию одним check.

Формат workflow journal и frozen render v1/templates не менялись. Generated Markdown по-прежнему строится из authored drafts. Legacy completed approvals читаются, точный UUID replay возвращает исходное event без нового утверждения; старые receipts не переписываются. Старые MVP drafts могут дать incomplete при новом check или новом gate. Read-only validate/verify/coverage/render сами по себе не объявляются проверкой полноты R3 и не исправляют старые drafts. Исторические demo replay остаются воспроизводимыми.

Reader использует общий lock/ACTIVE guard, confined paths без symlinks/junctions и лимит 512000 bytes на каждый state/draft file. Busy/pending/corruption/over-limit не превращаются в complete. Кейс и .env не переписываются.

## Что дальше

Этот срез закрывает только структурную полноту восьми разделов. Следующий — явные определения метрик/unit/population, baseline либо план измерения, критерии, окно, guardrails/stop rule, owner/data source. Semantic consistency, полноценный correction/withdrawal lifecycle, живые IDE-проверки и независимая оценка остаются открытыми. Примеры CI — только synthetic fixtures, не продуктовые стратегии или рыночные основания.
