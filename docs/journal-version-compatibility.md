# P5c: совместимость журналов и правила обновления/отката

Срез от 16.11.2026 дополняет [P5a recovery](host-config-integrity.md) и [P5b directory boundaries](journal-directory-boundaries.md). Текущие namespace и published record schemas остаются v1. Новая схема и конвертер между форматами не вводятся.

## Реализованная проверка

До поиска записи в v1 store проверяет родительский namespace через bounded scan с confinement. Отсутствующий журнал допустим. Если родитель существует, разрешены только известные каталоги с точным каноническим именем. Неизвестный sibling (в том числе v0/v2, файл или V1) вызывает фиксированную ошибку без его имени/содержимого. Одновременные v1/v2 тоже блокируются: наличие доступного v1 не разрешает игнорировать остальную историю.

| Канал | Проверяемый namespace |
|---|---|
| Tasks/results/reviews | CASE/.psa/workflow/subagents/v1 |
| Hook runs | CASE/.psa/workflow/hooks/v1 |
| Host observations | ROOT/.psa/host-acceptance/v1 |
| Host reviews | ROOT/.psa/host-acceptance/reviews/v1 |
| Config operations | ROOT/.psa/host-config/v1 |

В host-acceptance рядом с v1 разрешён известный каталог reviews. Review store дополнительно проверяет его собственный version namespace; observation store не декодирует независимый review channel. Область проверки ограничена перечисленными журналами, а не всеми папками проекта.

Проверка стоит на общем пути доступа: pending/read/publish/recover используют ту же границу. Config plan/apply/replay/show/audit/recover не обходят её. Даже исторический config replay отказывает при несовместимом namespace: downgrade не получает скрытого разрешения на работу с более новой историей. CLI завершает операцию ошибкой без частичного JSON; FastMCP возвращает прежний безопасный ToolError. Служебный lock может создаваться при проверке, journal/config bytes не меняются.

Namespace не заменяет record-schema/hash/identity validators. Они продолжают проверять прочитанные записи. Pending не стал полным аудитом содержимого всех final records; config audit проверяет собственную историю. Корректный namespace сам по себе не означает целостность записей, native support или человеческое согласование.

## Обновление с совместимым v1

1. Остановить участвующие writers и сохранить согласованную приватную копию workspace/кейсов вместе с игнорируемыми журналами, config, staging и authored материалами. Git checkout и release ZIP не заменяют этот backup.
2. Сохранить идентификатор версии кода/зависимостей и hashes backup. Не складывать приватные данные в репозиторий или release.
3. Проверить новую версию кода на отдельной копии: pending, config-audit и нужные read/show команды. Валидный pending intent восстанавливать только явно по [runbook](host-config-integrity.md), без повторного запуска действия/модели.
4. Сравнить receipts/bytes и проверить фактический workflow, прежде чем переходить к рабочей копии. Наличие unit tests не удостоверяет native IDE.

Эта реализация не меняет bytes завершённых v1 записей. Проверены прежние replay/recovery paths и совместимая копия config journal с тем же receipt/applied_at; это не испытание всех исторических бинарных версий пакета.

## Неизвестный формат и rollback

При unsupported journal namespace сохранить исходную копию и использовать код, который явно поддерживает этот формат, либо отдельную согласованную копию, сделанную до обновления. Не переименовывать v2 в v1, не удалять неизвестные записи для обхода проверки, не исправлять hashes/state вручную и не объединять части разных backups. Ошибка не запускает автоматический downgrade/restore.

Для rollback сначала проверить прежний код на соответствующей полной backup-копии. Не направлять старый binary на уже обновлённый рабочий каталог. Между созданием backup и rollback могут появиться новые данные: их сохранение/перенос требует отдельного явного разбора. Совместимая копия в regression возвращает прежний receipt без изменения config; исходный каталог с неизвестным namespace остаётся нетронутым.

Реальная cross-schema migration потребует конкретной целевой схемы, mapping IDs/fields, отдельного migration command, dry-run, сохранения provenance/human reviews и испытания crash/rollback. Сейчас такого конвертера нет. Проверка действует в этой версии кода; она не добавляет защиту старым бинарникам задним числом. Внешняя конкурентная подмена путей и power-loss/NAS гарантии не заявлены.

P5 остаётся частичным. [P5d privacy/injection diagnostics](automation-privacy.md) реализован; далее P5e dependency/artifact integrity и сверка оставшихся рисков перед P6. Native enable/acceptance P4 и R1/M6/M8 остаются открытыми.
