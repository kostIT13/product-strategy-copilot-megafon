# R2: файловая проверка обещаний

Дата: 10 ноября 2026 (Asia/Novosibirsk); время завершения — в development log. Ветка `feature/main-solution-roadmap`. Длительность отдельно не замерялась.

## Сделано

Добавлены отдельные domain checks/snapshot, application service/reader port, filesystem adapter и CLI/MCP modules. `psa promise check ID` / `psa_check_promises` проверяют commitment paragraphs авторских product/communication drafts без SQL, сети, модели или записи. Общий Markdown paragraph parser выделен из coverage без изменения прежних comment/heading/template semantics.

Preflight требует available capability, связанные active factual claims без superseding record, полные evidence arrays, current source hashes/revision events и точные quotes внутри supported locator scopes. V4 claim journal реконструируется штатным loader, проверяются event/result/completion receipt; source binding берётся из immutable source/event snapshots на момент записи claim. Legacy claim без binding блокируется, metadata задним числом не присваивается. Коррупция/лимиты не дают partial eligible packet.

Packet включает promise/capability/claim/citation context, blockers, input fingerprints и review_hash. Human/semantic review остаётся обязательным; publication/customer/workflow approval и truthfulness/semantic alignment flags false. CLI blocked status имеет exit 3. Coverage включает blockers; validate/verify и новые strategy/validation gates также их видят. Явные human gates сохраняют hash/status/version preflight в audit event. Historical UUID replay возвращает прежний receipt, не создаёт нового согласия; формат workflow journal не менялся.

README, MCP docs, основной план, roadmap, file-core и legacy inventory обновлены; добавлен контракт file-promise-check. Следующий этап R2 — нужные legacy данные/mapping/import/parity и вывод старых runtime dependencies/CI с clean-install проверкой без PostgreSQL/Alembic/Docker.

## Проверки

Полный unittest suite: **332 теста, OK (1 skipped: Windows symlink privilege unavailable)**, 322.983 s.

Targeted suite: **10 tests, OK** (финальный повтор 36.399 s). Проверены stable hash/read-only/no-approval flags, quote/locator failures, coverage/strategy gate block, reviewed-but-stale evidence, свежая замена claim/capability, A→B→A revision detection, non-fact/unlinked/missing/planned support, legacy binding missing, corrupted receipts/text/duplicate records/manual claim edits, оба human gates с audit hash, historical replay, busy/pending/bounds/malformed markers/no-promises, native PDF page и CLI/real MCP stdio parity/blocked exit code.

Первый targeted run имел одно неактуальное ожидание: тест ожидал чистый verify при сохранённой цитате после source revision. Теперь verify включает preflight через coverage и корректно блокирует устаревшую версию; ожидание исправлено, затем suite прошёл дважды (в финальном повторе добавлена проверка validation gate). Оба CI demo прошли с 0 model calls. Полный suite и итоговые checks фиксируются в development log.

## Ограничения

Проверяются отмеченные prose commitments, а не все возможные обещания естественного языка. Eligible не доказывает semantic entailment/истинность источника и не разрешает публикацию. Exact preflight quote строже whitespace-normalized verify. Review старой revision не обновляет binding; повторный анализ и новые refs требуют штатной записи, не автоматической миграции. Полный correction/withdrawal lifecycle — R3. Caps описаны в контракте; fingerprints не являются цифровой подписью или защитой от полного переписывания каталога.

БД и реальные продуктовые кейсы не читались/не менялись, данные не мигрировались; Docker/real sites/LLM/.env/dependencies не использовались/не менялись. Legacy runtime ещё существует; R2 открыт. Remote Actions и Docker gitleaks не запускались. Live R1/M8 и независимая оценка M6 отложены, не пройдены.
