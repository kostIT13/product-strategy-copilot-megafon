# P8a — protocol и neutral preparation для парного IDE-сравнения

17.11.2026 21:29 (Asia/Novosibirsk, UTC+7).

## Сделано

Зафиксированы собственный synthetic scenario «Тетрадь» и protocol (`99c7d2c`) для sequential IDE/file workflow и такого же workflow с отдельно разрешённой automation. Исторические MVP chat/CLI scores не перенесены в новый эксперимент. Общие inputs/checks/model/settings/caps и actual human gates должны совпадать; до человеческого выбора сравниваются только brief/research/evidence/options.

Добавлен offline preparation builder: pure schema/payload и отдельный filesystem/CLI (`800a6ef`), затем уточнено различие missing evidence=0 в завершённом scope и null для непроведённого review/незавершённой фазы (`72614da`). Новый каталог содержит operator-only conditions/owner key/run-record и отдельный reviewer brief/sources/rubric/templates. Hashes связывают записанные bytes, но не являются подписью или разрешением передачи. Outputs A/B отсутствуют, scores/actual measurements=null, prerequisites not_verified, authorization/review_ready=false. Label swap детерминированный, не рандомизация; reviewer files при перестановке byte-identical, гарантированная слепота не заявлена.

Конкретный пакет собран base CLI в ignored `.venv-ci/p8-preparation-85272dd8c9`; все10 payload hashes проверены, root manifest записан последним. [Metadata фактической подготовки](2026-11-17-p8a-preparation-check.json): code72614da/dirty=true (готовящиеся docs/reports), preparation_only, experiment_started/outputs_received/review_ready/authorization=false, model/external requests0. Owner/reviewer payload не коммитились как результаты и никому не передавались. User cases, decisions/gates, роли, native config и модель не использовались. Canonical instructions/skills/bundle1.1.3 не менялись.

Builder отказывает на существующий target, link/invalid parent, output внутри saved case, duplicate/traversal material keys, non-synthetic/forged authorization inputs и resource overflow. Inputs16KiB каждый, payload16 files/128KiB плюс bounded manifest. Ошибка сохраняет partial directory без completed manifest; automatic delete/resume/overwrite нет. Это local preparation tooling, не универсальный filesystem sandbox.

## Проверки

- Dev9 tests OK,1.611s; итоговый clean-base повтор9 OK,1.748s, без optional extras. Hash binding, blank outputs/scores/cost, no network/process dispatch, neutral label separation, file bounds, saved-case/overwrite/link refusal, malformed inputs, partial failure и sanitized nonzero CLI проверены. Число различных tests9, base repeat не удваивает его.
- Actual base CLI preparation/hash audit OK:10 payload files плюс root manifest. Это не run/scoring/independent review и не measured benefit.
- CI YAML parsed: Ubuntu unit rows15min, Windows25min; full unittest command сохранён. Ruff/harness sync9/docs262/diff/native Gitleaks history/tree/negative probes OK для итогового export.

## Дополнительный CI fix по actual annotation

При проверке [P7d CI](https://github.com/kostIT13/product-strategy-copilot-megafon/actions/runs/44100221993) Ubuntu/docs/secrets/base прошли, Windows был **cancelled**: started14:10:35Z/completed14:25:43Z, annotation `The job has exceeded the maximum execution time of 15m0s`. Это не assertion failure и не green Windows suite. [P7d demo](https://github.com/kostIT13/product-strategy-copilot-megafon/actions/runs/44100222145) прошёл.

Отдельный commit `4232419` задаёт Windows job timeout25min с headroom для setup/host variation (локальный full ранее занимал18.2min), Ubuntu остаётся15min. Tests, собственные test deadlines/guards, required checks и model/network policy не сокращены. Новая matrix после push ещё требует проверки; старый timeout run не переименован в success. Full suite и release локально повторно не запускались.

## Что дальше

[P8a runbook](../docs/evaluation/paired-ide-preparation.md). Далее P8b — заполнить и проверить реальные host/model/settings, prerequisites, action scope/authorization, common caps/order/hashes и действительный human choice для strategy phase. Подготовка пакета не даёт этих разрешений. Передача reviewer требует отдельного разрешения и actual outputs/hashes. P7 measured benefit, independent M6/P8 и live R1/M8/P4–P6 остаются открытыми. Итоговый docs commit фиксирует актуальные планы и этот отчёт.
