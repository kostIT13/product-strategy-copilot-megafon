# Оценка текущего источника

После импорта прочитайте извлечённый материал. `psa source assessment ID S-ID` показывает текущие `workflow_version`, `content_hash` и `source_record_hash`, сам источник и записанную оценку. Для внешнего каталога добавьте `--projects-dir PATH`.

Сохранение: `psa source assess ID --input assessment.json`. JSON содержит:

| Поле | Значение |
| --- | --- |
| operation_id | Новый UUID; точный повтор возвращает прежний результат без перезаписи текущей оценки |
| source_id | Выбранный S-ID |
| expected_workflow_version | Число из inspection |
| expected_content_hash | content_hash из inspection |
| expected_source_record_hash | source_record_hash из inspection |
| assessed_by | Реальный автор записываемого суждения; attribution не аутентификация |
| author, publisher_or_owner | Строка либо явный null, если неизвестно |
| published_at | Календарная дата YYYY-MM-DD либо null; не дата обращения |
| reliability | unassessed, low, medium либо high |
| reason | Содержательное основание оценки |
| limitations | Массив ограничений оценки, допустим пустой |
| unknowns | Массив неизвестного; обязателен непустой при null metadata или unassessed |

Не выводите владельца из имени папки или hostname. У новых импортов владелец и дата публикации неизвестны; это не меняет URL/path и provenance приобретения. Исторические receipts воспроизводят прежнюю политику metadata без повторного чтения или fetch.

Оценка — recorded_assessment, independently_verified=false. Она не доказывает истинность материала, не заменяет точную цитату, сравнение независимых оснований и человеческий gate. Высокая reliability также остаётся суждением автора. Технические ограничения extraction сохраняются отдельно от limitations оценки; accessed_at не меняется.

Запись привязана к текущим bytes и записи реестра; stale version/hash, повреждённый текст и withdrawn source отклоняются. Новый импорт, даже того же текста, сбрасывает оценку и записывает assessment_invalidated; предыдущая оценка остаётся в event/receipt history. Повтор старого UUID не восстанавливает старую оценку поверх текущего состояния. После изменения metadata заново выполните render/validate/verify/coverage и актуальные review по необходимости.

Optional FastMCP: `psa_source_assessment` читает, `psa_assess_source` принимает project_id, request с теми же полями и projects_dir. CLI JSON ограничен 16384 bytes; поля модели ограничены отдельно. Операция не вызывает сеть, модели, роли, hooks или gates.

Workflow journal format v8 хранит before/after реестра и детерминированно проверяемый результат. При незавершённой записи используйте существующие pending/recovery команды по выбранному UUID; не исправляйте state/events/registry вручную. Совместимость старых форматов сохранена. Технический stdio smoke не подтверждает native IDE acceptance.
