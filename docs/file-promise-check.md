# Проверка обещаний в файловом psa

```powershell
psa promise check CASE
psa coverage CASE
psa verify CASE
```

Файловый MCP предоставляет read-only `psa_check_promises`. Общие FilePromiseService/reader/domain checks работают без PostgreSQL, LLM, сети и новой записи. CLI выводит JSON; exit 0 — `eligible_for_human_review` или `no_promises`, exit 3 — структурная блокировка, ошибки чтения/формата завершают команду ошибкой. Положительный результат не разрешает публикацию, customer promises или workflow gate.

## Откуда берётся проверяемое обещание

Проверяются prose paragraphs в `drafts/product-strategy.md` и `drafts/communication-strategy.md` с `[COMMITMENT: CAP-001]`. Используются те же paragraph/comment/heading/template semantics, что у coverage. Некорректный commitment marker вызывает ошибку. Сканер не распознаёт все возможные обещания в естественном языке: отсутствие marker не доказывает отсутствие обещаний, а `no_promises` не является одобрением.

Если paragraph явно перечисляет `[C-ID]`, проверяются эти claims для каждой указанной capability; иначе используются её claim_ids. Нужно 1–6 supporting claims на capability, каждый должен быть связан с ней. Допускается до 20 paragraphs, трёх capabilities на paragraph, 50 distinct claims и 4000 символов на paragraph. Это authored support selection, не выбор доказательств моделью.

## Что блокирует

- Capability отсутствует или не `available`.
- Claim отсутствует, не `active fact`, имеет замену через `supersedes`, не связан с capability или имеет неполные evidence arrays.
- Нельзя восстановить immutable запись claim и версии источников на момент записи. Legacy claim без v4 creation/v5 correction journal binding блокируется как `claim_evidence_snapshot_missing`; согласие или binding ему автоматически не присваивается.
- Current claim изменён относительно journal result; receipt/manifest/event не совпадают или повреждены.
- Current source недоступен, имеет неканонический путь/status/format, неверный hash или невалидный UTF-8. Используется общий bounded current-source snapshot, включая проверку остальных источников корпуса.
- Content hash или последний source revision event отличается от снимка при записи claim. Даже возврат текста A → B → A не восстанавливает прежнюю актуальность.
- Quote отсутствует **точно внутри locator scope**. Поддержаны paragraph/p/line, lines range и native PDF page/XLSX cell. Неподдержанный locator блокируется без глобального поиска. Quote ограничена 500 символами; whitespace normalization прежнего verify не заменяет строгую preflight проверку.

Ручной revision review не переписывает proof binding старого claim. После реального повторного анализа и указания человека используйте [claim correct](claim-correction.md), затем обновите capability/support и авторский draft с актуальными refs. Новый v5 proof связывается с текущими источниками. Не делайте это автоматически ради зелёной проверки. Withdrawal/correction реализованы; [completed review/reopen](workflow-reopen.md) реализован; semantic consistency остаётся R3.

## Packet, gate и восстановление

Packet содержит точный paragraph/path/line, capability name/status, claim text/type/status, citations/current hashes, blockers и fingerprints входных файлов/claim manifests. `review_hash` — SHA-256 канонического packet; он меняется при изменении draft, state, реестров, evidence или proof receipts. Это проверка целостности снимка, не цифровая подпись и не защита от лица, способного переписать весь каталог и пересчитать hashes.

Flags `semantic_alignment_verified`, `source_truthfulness_verified`, `publication_approved`, `customer_promises_approved`, `workflow_approval_granted` и `durable_approval` остаются false; требуется человеческая проверка соответствия конкретного обещания, аудитории, условий, сроков и ограничений реальной capability/evidence.

Coverage включает структурные blockers, поэтому они также видны в validate/verify и блокируют новые strategy/validation gates. Явный gate с человеком сохраняет review_hash/status/version в своём audit event. Он не становится публикационным разрешением. Общий workflow journal и recovery не меняют формат; historical completed UUID replay возвращает прежнее approval event без повторной оценки текущего текста и без нового одобрения. Старые gate receipts не переписываются.

Reader работает под общим case lock и ACTIVE guard; read-only packet ничего не исправляет и не снимает review. Действуют source-search limits (500 sources, 10 MiB/source, 32 MiB corpus), 512000 bytes на metadata/draft file, 1000 records на ledger/event input, 32 MiB суммарно прочитанных claim bundles и 128000 символов на packet. Over-limit/corrupt inputs не дают частичного eligible результата.

## Отличия от legacy

Старый `psa-main promise check --input JSON` использует UUID/DB snapshots и отдельные кандидаты. Файловый путь проверяет authored draft markers и строковые IDs, использует v4 claim snapshots и native locators; полная идентичность API не заявляется. Legacy import обязан сохранить старые evidence/approvals как историю, а не создать новое согласие или задним числом связать claim с нынешним источником. R2 runtime выведен после подтверждения отсутствия нужных PG-данных; [решение](legacy-retirement.md). Generalized importer не реализовывался.


[Source withdrawal](source-withdrawal.md) даёт dependent claim blocker claim_source_withdrawn; citation snapshot не возвращает withdrawn source, исходные records/bodies сохраняются для аудита.
