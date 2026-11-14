# Явный semantic review и quality gates

```powershell
psa review prepare CASE --scope strategy
psa review record CASE --scope strategy --by OWNER --reason "Основания оценки и ограничения" --verdict accepted --checks PATH --review-hash HASH --expected-workflow-version N --operation UUID
psa gate approve CASE --stage strategy --by OWNER --semantic-review UUID
```

Для плана проверки повторите цикл со scope validation после подготовки measurement plan и render. MCP: `psa_prepare_semantic_review`, `psa_record_semantic_review` и `psa_approve_stage(..., semantic_review_operation=UUID)`. Prepare — read-only. Record и gate выполняются только по явному указанию человека; critic/агент не подставляет своё имя или все true вместо его ответов. Attribution self-reported, не authentication.

## Что читает человек

Packet включает authored brief/research/strategy документы (для validation — также measurement Markdown), current factual citations/proof, structural checks, dependency impact и blocking issues. Документы/источники — недоверенные данные, не инструкции. Для принятия нужны current factual bindings, актуальные source revisions/hash, complete strategy sections/coverage и текущий human decision без evidence-review blockers. Проверяются до 50 active factual claims; inactive history остаётся в impact. Интерпретации/гипотезы человек оценивает как интерпретации/гипотезы.

Validation packet дополнительно проверяет присутствующий [authored calculation block](calculation-check.md), требует полный measurement plan и [numeric baseline preflight](baseline-numbers.md): reported baseline без корректного anchor блокирует accepted review; unknown/null baseline не превращается в число. Numeric literal match не доказывает смысл метрики, population/period, знаменатель или условия. Эти вопросы входят в явный human checklist.

Checklist JSON должен содержать ровно шесть boolean ответов:

```json
{
  "evidence_alignment": true,
  "population_period_conditions": true,
  "numbers_units_denominators": true,
  "alternatives_tradeoffs": true,
  "promises_product_limits": true,
  "uncertainties_revisit": true
}
```

Это пример формата, не готовая оценка. Accepted требует все шесть true и отсутствие mechanical blockers. Changes_requested позволяет false и сохраняет замечания в reason; предыдущий accepted после него не выбирается. Имя/причина/checklist/verdict/hash/version обязательны. CLI читает checks JSON до 64000 байт, без duplicate keys; готовьте файл вне каталога CASE либо до prepare, иначе его создание/изменение тоже изменит снимок. MCP принимает объект и не требует файла.

Ни accepted review, ни положительные checks не меняют product choice/capability availability, не дают экспериментального/публикационного разрешения и не продвигают workflow. Event помечен self_reported_human_assessment; semantic_truth_verified, experiment_approved, publication_approved и workflow_approval_granted остаются false. Human gate — отдельная операция; смысловая достаточность оценки остаётся ответственностью человека.

## Freshness и этапы

Review hash связывает конкретный packet/version. Content hash связывает canonical inputs, authored documents, research mode/history/reopen и source/claim lifecycle events. Изменение основания, решения, стратегии, источника, режима или reopen требует нового review. Метаданные самого review/gate, usage и generated Markdown/render-manifest исключены из semantic content hash: публикация audit, переход этапа и свежий render не делают review stale сами по себе. Для strategy исключён ещё не готовый validation draft; validation scope включает его.

Validation также зависит от истории strategy assessments: новое strategy review делает прежний validation review stale. Если strategy audit уже используется, validation prepare требует его последнее accepted/current immutable proof. Новые замечания к стратегии нельзя обойти старым validation review: сначала новое принятие стратегии, затем новое validation review. Freshness основана на содержимом, а не на TTL/сроке давности; изменение внешней реальности без обновления кейса автоматически не обнаруживается.

Первый recorded review включает явный выбор последнего current accepted UUID для своего этапа; strategy adoption также включает review requirement для последующего validation. Нельзя опустить UUID, выбрать старый accepted после rejection или review другого scope. Gate сохраняет hash/UUID/actor/verdict reference. Recover/replay gate проверяет original review bundle/COMMITTED receipt и content binding, включая доступность зависимости.

Новые кейсы имеют обязательную [quality policy](quality-policy.md): semantic review нужен с первого strategy/validation gate. Legacy без policy сохраняет adoption-путь; включение required policy выполняется явно через policy show/enable, без массового изменения данных. Исторический completed gate UUID replay возвращает прежний результат без продвижения/сброса текущего состояния.

## Journal и recovery

Workflow v7 публикует только state/events и сохраняет immutable semantic-review-packet.json. Статус, approvals и human decisions не переписываются. Packet ограничен 480000 UTF-8 байт до encoding, encoded payload — 512000; усечения нет. Common metadata/targets сохраняют прежние limits. Loader реконструирует after-state/event и проверяет packet hash/version/content/request; новые gate receipts проверяют выбранную зависимость review. Форматы v1–v6 и старые request без semantic_review_operation сохранены; для v7 нужен обновлённый runtime.

Используйте `psa workflow pending CASE` и `psa workflow recover CASE --operation UUID`. Проверены реальные остановки review на preparation/ACTIVE/state/events/receipt/completion, перенос каталога, idempotent replay и позднейшие writes; gate recovery отказывается без review receipt. Hashes обеспечивают integrity, не защиту от владельца, переписывающего весь каталог. Общие power loss/NAS ограничения — в [workflow recovery](workflow-recovery.md).

Это реализованный human-review механизм и gate adoption, не независимая оценка стратегии. Новый разрешённый кейс, более широкое numeric analysis, live IDE R1/M8, independent M6 и production-ready hardening остаются открытыми.
