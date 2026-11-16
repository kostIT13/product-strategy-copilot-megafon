# P5e: целостность зависимостей и артефактов

Срез от 16.11.2026 продолжает [distribution runbook](distribution.md). Локальные проверки выполнены на Windows/Python3.12; remote Actions success и релизная публикация не заявляются.

## Frozen graph и build backend

Runtime/extras остаются в uv.lock. Перед сборкой package и перед установкой из распакованного архива verify вызывают `uv lock --check --offline`: stale graph не регенерируется автоматически. Ошибка блокирует build/install; до build preflight output directory не создаётся. Требуется uv0.11.30 из pyproject; несовпадение инструмента или недоступный offline resolution также является отказом, а не разрешением обновить lock.

Ранее build-system использовал setuptools>=68 вне runtime lock. Теперь build-system и отдельная dependency-group build совпадают: setuptools==82.0.1. Выбрана уже использовавшаяся закэшированная версия; обновление прочих пакетов не выполнялось. В lock добавлены setuptools и SHA256 его wheel/sdist. Build-группа не становится runtime dependency и не включается в обычный base sync.

Release helper проверяет exact backend/build-group policy, экспортирует временные hash constraints через `uv export --frozen --offline --only-group build --no-emit-project` и передаёт их в isolated `uv build --require-hashes`. Неверные hashes backend проверены реальным offline build: wheel/sdist не появляются.

Verifier устанавливает каждый локальный wheel/sdist через временный requirement с проверяемым SHA256, `--require-hashes`, `--no-deps` и теми же build constraints. Base dependencies предварительно устанавливаются frozen sync из lock; установка проекта не должна незаметно изменить этот graph. Для sdist isolated build backend также ограничен lock hashes. Переход на другой backend/новые build requirements требует явного изменения policy, lock и тестов.

## Общий artifact checker

Install-verifier использует общий bounded inspect_release до extraction/install: ZIP/manifest/allowlist/hashes и внешние четыре assets/SHA256SUMS. Это тот же механизм, что [read-only release hook](release-hooks.md); сам verifier дополнительно устанавливает код и запускает smoke, поэтому не является read-only checker.

Удалён отдельный unbounded checksum pass. Слишком большой checksum sidecar или изменённый external wheel блокируют установку до subprocess install. Упакованный pyproject/lock дополнительно проверяются перед sync/pip: правильные hashes архива не делают stale dependency graph совместимым. Offline hook по-прежнему не запускает uv, установку или package code.

## Проверенный локальный путь

```text
uv lock --check --offline
python -m scripts.release.package --output dist/p5e-check
python -m scripts.release.verify dist/p5e-check/product-strategy-agent-0.1.0.zip
```

При разработке использовать Python окружения проекта. Для релизного кандидата сохраняется `--require-clean --tag vX.Y.Z` и процедура [distribution](distribution.md). В этой итерации собран development snapshot с dirty=true; это не архив чистого итогового commit и не комплект сдачи. Assets локальные/ignored; теги, загрузка и публикация не выполнялись.

Реальные wheel и sdist установлены по очереди в отдельное base environment. Импорт проверен из site-packages вне исходников; doctor/help, demo/table-demo replay и completed/copy/resume/reopen/reapprove smoke прошли с model_calls=0 и sql_dependencies=false. Установка может потребовать сеть/uv cache для получения locked artifacts; offline preflight не обещает наличие всех wheels на чистой машине. Побайтовая воспроизводимость разных сборок и подпись автора не заявляются.

## Сверка оставшихся границ P5 перед P6

| Область | Локальный результат | Осталось / зависимость |
|---|---|---|
| Journal crash/copy recovery | P5a и прежние task/hook/host recovery tests | Power-loss/NAS, external editor race и OS sandbox не удостоверены |
| Path/resource bounds | P5b bounded enumeration, confinement и реальные Windows junction negatives | Другие ОС/файловые системы подтверждаются отдельно |
| Compatibility/rollback | P5c namespace guard, compatible copy replay, runbook | Новый cross-schema converter только при определённой целевой схеме |
| Privacy/injection | P5d runtime error sanitization и selected-material corpus | Semantic LLM/native behavior требует отдельной оценки, не выводится из unit tests |
| Dependencies/artifacts | P5e frozen freshness, hash-constrained backend, общий checker и реальная установка | Signed/public release и чистый финальный bundle относятся к P9/R6 |
| Host paths/native activation | Disabled-only локальный lifecycle проверен | P4 live enable/acceptance отложен; R1/M8 открыты |

Локальные P5a–P5e срезы выполнены; весь P5/production readiness не закрыт, host-зависимые и независимые приёмки остаются открытыми. Можно продолжить независимый P6a: read-only диагностика automation operations/versions и понятные outcomes без private texts. Usage/cost должны отличать measured/estimated/unknown; новых моделей/dispatch это не разрешает. M6 остаётся отдельной независимой оценкой.


[P6a operation diagnostics](operation-diagnostics.md) реализован независимо от отложенной native приёмки: text-free task/result/review/hook metadata и unknown/self-reported usage. Далее P6b summaries/resume guidance; весь P6 и остающиеся P4/P5 приёмки не закрыты.
