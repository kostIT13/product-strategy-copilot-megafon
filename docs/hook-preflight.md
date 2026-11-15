# P3a: явный локальный preflight перед gate

Первый срез [P3](solution_plans/production-readiness.md): фиксированные read-only проверки для `before_strategy_gate` и `before_validation_gate`. Автоматическая активация, native hooks и утверждение gate не выполняются. Основной последовательный workflow сохраняется.

## Использование

Сначала подготовьте request с новым UUID, сохранив JSON **вне каталога кейса**, чтобы не изменить его snapshot:

```powershell
psa hook prepare CASE --trigger before_strategy_gate --operation UUID --projects-dir projects
psa hook check --request PATH_OUTSIDE_CASE/hook.json --projects-dir projects
```

Первый stdout — HookRequest по [контракту P0](automation-contracts.md); второй — HookResult. Подготовка связывает request с project ID, workflow version и hash state/events/существующего input snapshot. Переданные caller hashes не считаются доказательством актуальности: check повторно сверяет состояние под общим case lock до и после проверок.

Фиксированный набор без пользовательских commands/check lists:

1. `structural_integrity`: существующий `validate_project`.
2. `citations`: существующий `verify_project`; warnings отдельно не блокируют.
3. `stage_requirements`: текущий этап/mode и существующие workflow checks, включая coverage, документы стратегии/validation и их действующие ограничения.
4. `semantic_material`: существующий semantic-review prepare и его structural/numeric/evidence blockers.

Raw тексты ошибок/источников не отражаются в HookResult: выдаются фиксированные имена проверок, а подробности читаются штатными командами validate/verify/coverage и semantic prepare. Источник/результат/поле request не может добавить shell, permissions или новый trigger. Вложенный запуск блокируется context guard независимо от сброса caller поля recursion_depth.

## Результаты и границы

`passed` означает только механический preflight на конкретном snapshot. Это не semantic assessment, human approval или permission выполнить gate/эксперимент/публикацию. Отсутствие записанного human review не превращается в согласие; canonical gates продолжают самостоятельно проверять свои требования и выбранный review.

`blocked` — устаревший snapshot, изменение во время проверки либо blockers существующих проверок. `failed` — check недоступен/не может быть выполнен. CLI выводит структурированный result и завершает check с кодом 1 при blocked/failed, с 0 при passed. Невалидный request/недоступный case/основной pending workflow дают обычную ошибку без частичного result. MCP возвращает blocked/failed как HookResult; caller обязан проверять status, а не только успешность транспорта. Только passed допустим для required preflight.

`operation_id` связывает request/result, но здесь ещё **нет durable hook journal**. Повтор — новая живая проверка, не replay прежнего pass; в неизменном окружении результат совпадает. Отдельное человеческое действие и сами canonical gate checks всё равно обязательны. Snapshot не включает `.psa/workflow` по прежним правилам; задачи P2 не меняют оснований gate.

Файловый adapter разделён с application service и port. Он вызывает те же существующие проверки, не копирует правила gate и не выполняет сетевых/модельных запросов. Общий lock защищает участвующие CLI/MCP операции; ручное изменение файлов сторонней программой не становится транзакцией. Сравнение snapshot после checks обнаруживает сохраняющееся изменение, но не является sandbox или защитой от владельца файлов.

## FastMCP и оставшаяся часть P3

`psa_prepare_hook(project_id, trigger, operation_id, projects_dir)` и `psa_check_hook(request, projects_dir)` используют тот же service; оба read-only/local. Request ограничен 64 000 bytes, strict JSON отвергает duplicate keys, nonfinite values, лишние fields, неверные union tags и ненулевой recursion depth. Диагностика не отражает input values. CLI/real-stdio parity и human-gate isolation проверены на синтетических fixtures.

P3 ещё не завершён. Далее: ограниченное исполнение с реальным timeout и lifecycle/replay semantics; source-revision→revisit notification без отката committed import; release checks без публикации. `source_revision`/`release_check` пока существуют только в P0 contract и отвергаются этим adapter. Host-specific activation/permissions остаются P4; R1/M6/M8 открыты. P3a не заявляет timeout/cancel/resource enforcement или native host acceptance.
