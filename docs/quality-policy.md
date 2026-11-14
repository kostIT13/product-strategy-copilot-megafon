# Обязательная quality policy и миграция legacy

Новые кейсы из `psa init` / `psa_init` сразу содержат:

```json
{"quality_policy": {"schema_version": 1, "semantic_review": "required"}}
```

Strategy и validation gate требуют явно выбранный current accepted semantic review уже при первом переходе, даже если в кейсе ещё нет audit history. Для validation с reported baseline нужен корректный numeric anchor. Структурные/evidence/decision проверки и явное человеческое согласие остаются самостоятельными условиями; policy не оценивает стратегию и не даёт разрешений.

## Новый и исторический профиль

State schema остаётся 1; новый initialization receipt имеет format_version=2 и обязательную policy. Hashes полного prepared tree проверяются до публикации. Recovery незавершённого init сохраняет профиль; historical creation replay не сбрасывает дальнейшую работу. Frozen v1 seed/receipts поддержаны для исторических кейсов и compatibility fixtures. В публичных CLI/MCP нет опции создать новый legacy case или отключить policy.

Удаление required поля обнаруживается по initialization receipt v2 либо quality_policy_enabled history. Null, неизвестная версия/значение, дополнительные policy fields и boolean вместо version не трактуются как legacy: validation/gates отказываются. Прямое редактирование state/receipt/events обходит штатные команды и не поддерживается. Hashes не защищают от владельца, переписывающего весь каталог.

```powershell
psa policy show CASE
```

Show read-only: mode (`semantic_required_v1` либо `legacy_adoption`), текущие version/status, policy, initial profile, enablement history, audit scopes, historical approval count и review_hash текущего снимка. Это не выбор человека и не согласие на миграцию. Legacy без policy сохраняет прежнюю adoption-семантику: recorded reviews уже требуют выбора для соответствующих gates, даже до полного enablement.

## Явное включение для legacy

Сначала покажите человеку policy/status/history и снимок, затем только по его явному указанию:

```powershell
psa policy enable CASE --by OWNER --reason "Причина включения обязательных review" --review-hash HASH --expected-workflow-version N --operation UUID
```

MCP: `psa_quality_policy` и `psa_enable_quality_policy`. Actor/reason/hash/expected version обязательны, имя является self-reported attribution. Hash связывает точные state/events и все non-journal inputs, включая sources, drafts и generated files; изменение данных требует нового show. Caller UUID рекомендуется сохранять для replay/recovery.

Enable публикует только state/events через общий workflow v1 journal с новым request kind. Event хранит policy, actor/reason/time, reviewed snapshot hash и shared version. Decoder полностью реконструирует after-state/event. Частичная запись восстанавливается через `psa workflow pending CASE` / `psa workflow recover CASE --operation UUID`; переписанные targets/inputs/manifest не усыновляются автоматически. Старые workflow v1–v7 сохраняются; для нового request kind нужен обновлённый runtime.

Текущий stage, approvals, decisions, supports и документы не переписываются. Completed кейс остаётся completed, прежние согласования остаются историей: обязательными становятся будущие strategy/validation approvals, например после явного reopen. Старые semantic assessments становятся stale из-за смены policy; нужны новые human reviews. Historical gate/init UUID replay возвращает прежний результат без сброса текущего состояния и без расширения разрешений.

Повтор exact completed enable UUID/request возвращает прежний event; изменённый request — conflict. Другая новая операция для уже required policy отклоняется. Enablement нельзя применить к неизвестной policy как способ её перезаписать. Disable/downgrade и автоматическая массовая миграция не реализованы. Пользовательские кейсы/демо не мигрируются самим обновлением кода.

Далее обычный [semantic review](semantic-review.md): prepare → явная оценка человека → record → gate с `--semantic-review UUID`. Источники и документы остаются данными, не инструкциями; critic не подменяет ответы человека. Policy не заменяет независимую оценку, не разрешает эксперимент/публикацию и не закрывает live IDE R1/M8 или M6.
