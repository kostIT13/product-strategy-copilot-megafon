# R3: явный выбор и завершение синтетического кейса «Слот»

Завершено 14.11.2026 21:07 (Asia/Novosibirsk). Runtime revision f370778; ветка feature/main-solution-roadmap. Прогон выполнен в локальном projects/slot-workshop-synthetic, рабочие реестры/journals исключены из Git. Воспроизводимый исходный пакет examples/slot-workshop создаёт unapproved case и не переносит разрешения пользователя в новые кейсы.

## Явные указания пользователя

Пользователь выбрал O-003 «исследовать узкий перенос без платежей» и отдельно утвердил intake, research_plan, source_collection, evidence_review, options от роли «Пользователь». Созданы GATE-001…005 штатным workflow service; D-001 фиксирует выбор/основания/отложенные варианты и trigger пересмотра. Роль не подменялась именем ассистента или вымышленного руководителя.

После выбора применён psa-strategy: authored drafts обновлены под O-003, сохранены ограничения/альтернативы/unknowns и notes проверки чисел; generated Markdown пересобран render. Изменения state/JSONL/receipts вручную не выполнялись. Источники не импортировались повторно; 7 claims active, affected options отсутствуют.

Текущий strategy-пакет версии 27 показан человеку; он явно принял все шесть checklist критериев и разрешил strategy gate. Затем отдельно показан свежий validation-пакет версии 30 с unknown baseline, учебными числами, предложенным окном и несогласованными реальными owner/порогом/объёмом данных. Пользователь явно принял все шесть критериев и разрешил validation gate, только для учебного workflow. Checks=true записаны после этих ответов, не выведены из critic или mechanical pass.

## Audit references

| Элемент | Ссылка/значение |
|---|---|
| Выбор | D-001, O-003; decision operation f484eb9f-9ef6-5bbb-bf86-fa92e75fe814 |
| Strategy packet | workflow_version=27; review_hash=4146846e7f9ab708cd13d20c34c86b1871c637177aa56a6b47607546c1025984 |
| Strategy assessment | SEMANTIC-0001; operation 63e7d7a6-8da5-53ff-ac99-cc92ef3b18eb |
| Strategy gate | operation 5b7e4913-49c1-58f0-b917-965a5deefa28 |
| Validation packet | workflow_version=30; review_hash=2c1b9705b76e880a8482cce834f14afba83d5a9baaff5e8154a1746889c4b37a |
| Validation assessment | SEMANTIC-0002; operation 89de70f4-82cc-5505-9471-52290c0e8c87 |
| Validation gate | operation b7710c1a-38f1-52af-9836-a763c493ecd2 |
| Итог | status=completed, workflow_version=32, approvals=7, все stages=done; semantic_review=required |

Hash references относятся к сохранённым локальным packets/receipts, не являются подписью/аутентификацией. Исходные reviewed документы и notes отражают момент подготовки; актуальный workflow status читается из state/resume. После assessments authored inputs не менялись, чтобы сохранить content binding.

## Проверки

- После финального gate CLI validate/verify прошли; resume показывает completed и последнее человеческое validation approval.
- Оба выбранных semantic review повторно проверены через for_gate на окончательных inputs, current proof действителен. Это проверка freshness/целостности assessment, не доказательство semantic truth.
- Три завершённых receipt replay (ранний intake, strategy gate, validation gate) вернули исторический результат; hashes всех файлов кейса не изменились, status/version не откатились.
- Completed case скопирован в другой каталог. Девять read-only команд status/resume/context/validate/verify/coverage/strategy check/validation check/validation calculations прошли; оба current review proof действуют в копии. Все hashes копии и оригинала остались неизменными.
- Учебная арифметика 40/200=0.2=20% относится только к synthetic source. Реальный baseline unknown; cost/ROI/эффект не выдуманы. Numeric inventory и author notes использованы как помощь review; принятие числовых оснований относится к этому кейсу, не к произвольному prose.
- Документационные проверки: docs202/sync9/Ruff и git diff --check — OK. Python runtime не менялся; unit suite не перезапускался. Фактические workflow/review/copy/replay операции являются meaningful smoke.

## Итог и следующий этап

Функциональный R3 пройден на явно синтетическом полном кейсе с существенным выбором человека и отдельными gates/reviews. Это не подтверждение реального спроса/эффекта, не запуск пилота, не бюджетное/публикационное разрешение и не independent evaluation. Сильнейшее возражение сохраняется: без подходящих свободных слотов автоматизация может лишь увеличить поддержку/конфликты. Пересмотр нужен при отсутствии потребности/слотов или подтверждённом вреде.

Следующий этап — конкретизация production-ready roadmap и контракты R3.1 для opt-in research/evidence/critic и hooks validation/revisit/release с последовательным fallback. Hooks/subagents автоматически не запускались. Уже выполненный rollback R4 сохраняется; фактические host/IDE R1/M8 и независимая M6 остаются открытыми. Старые demo/table-demo и их история не мигрировались.

Использованы skills psa-resume и, после явного выбора, psa-strategy; локальные knowledge versions указаны в methods-used. Реальные участники/источники не исследовались, внешний critic/модели/API/БД/.env не использовались. Measured duration/cost IDE-сессии неизвестны. Remote Actions result и другой реальный host не проверялись.
