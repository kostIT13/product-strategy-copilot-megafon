# Отзыв claim и effective evidence

Только по явному указанию человека:

```powershell
psa claim withdraw CASE C-001 --by OWNER --reason "Основание отзыва" --operation UUID --expected-workflow-version N
psa claim impact CASE
```

MCP: `psa_withdraw_claim` и read-only `psa_claim_impact`. Actor/reason обязательны; имя — self-reported attribution, не authentication или доказательство согласия. Critic verdict не является разрешением на отзыв.

## Канон и статусы

ClaimWithdrawal публикует state/events через общий workflow v1 journal: caller UUID, expected version, ACTIVE/completion, explicit pending/recover. Claims, sources, capabilities, options, decisions и approvals не переписываются. Event сохраняет original claim snapshot/hash, actor/reason/time и impact на момент отзыва. Изменение исходной строки после отзыва даёт integrity error.

Effective status вычисляется из raw records, исторических supersedes и claim_withdrawn events. Исходный status: active в старой строке описывает её запись, а не последующую eligibility. Отозванный или superseded claim не является текущим основанием. Отзыв replacement не оживляет прежний claim. Циклы/некорректные refs/повторные events отклоняются.

Withdrawal применим к effective active claim с явным raw active status. Другой UUID для неактивного ID даёт ошибку; тот же завершённый UUID возвращает первоначальный event без дублирования и сброса позднейших writes. Изменённый request/version не считаются тем же replay.

## Зависимости и новый выбор

Impact показывает inactive IDs, affected options/capabilities/decisions и связанные через contradicts claims. Для decisions учитываются прямые refs, selected option и rejected alternatives по ID/имени. Это структурные связи, не NLP-анализ всех смысловых зависимостей. Needs_review — derived status: человеческий выбор и доступность продукта автоматически не меняются.

Текущее решение — последняя запись decision-log, как в прежнем renderer. Оно может требовать review даже при свежих refs в draft. Новый strategy/validation gate не использует его автоматически: нужны пересмотренные основания/options и новое явное решение человека. Исторические decisions остаются в impact после новой записи, но не блокируют gate как текущие. Не записывайте новое решение только ради зелёного check.

Новые supporting links capabilities/options/decisions не принимают inactive claims; выбранные/отвергнутые options с такими основаниями требуют review. Historical ledger replay возвращает прежний результат. Evidence-review gate требует хотя бы один active claim; options gate считает варианты без inactive supporting claims. Promises и reported baseline блокируются общим effective claim check.

Coverage блокирует inactive C-ID в prose. Verify проверяет текущие claims; неактивная история не выдаётся за действующие цитаты. Схема/refs исторических строк и integrity source files по-прежнему проверяются. Источник не удаляется/не отзывается: поиск текста доступен для нового анализа. Critic-pack исключает inactive claim statements из актуальных оснований и показывает lifecycle audit.

CLI status/resume показывает inactive history и необходимость review текущего решения. Completed workflow остаётся историческим фактом; automatic reopen/переутверждения нет.

## Renderer v2

Новые render generations: active claims в основном evidence view, inactive IDs/statuses в audit, предупреждения о dependent options/decision и needs_review для affected capabilities в generated view. Raw capability records и authored drafts не меняются.

Frozen render_documents_v1 сохранён. Старые v3 receipts без builder_version реконструируются прежним builder; новые сохраняют builder_version: 2. CLI/MCP auto intent при replay сравнивает business request без внутреннего выбора builder, поэтому старые и новые UUID работают. Явный новый render v1 запрещён; новым receipts нужен обновлённый runtime. Withdrawal использует workflow v1; отдельная correction-команда добавляет v5.

Replay старого render не является новой генерацией. После withdrawal/correction новый validation gate требует render v2 с version позже последнего такого события; adoption этого не заменяет. Integrity/discard/manual-edit правила остаются. Это не общая гарантия semantic freshness произвольных изменений drafts.

## Recovery и границы

При сбое: psa workflow pending CASE, затем recover точного UUID. Recovery проверяет before/after state/events и остальные inputs. Partial preparation/conflict/tampering не ремонтируются молча. Проверены реальные остановки до ACTIVE, после ACTIVE/state/events/receipt и завершения, перенос каталога и сохранение позднейших writes.

Withdrawal и общая effective projection реализованы. Исторический claim add --supersedes поддержан; отдельная [audited correction](claim-correction.md) с actor/reason и current evidence binding реализована через workflow v5. [Явный completed review/reopen](workflow-reopen.md) реализован. [Source withdrawal](source-withdrawal.md) реализован; semantic/numeric consistency остаётся следующей задачей R3. Production readiness, live IDE и независимая оценка не подтверждаются этой механической проверкой.
