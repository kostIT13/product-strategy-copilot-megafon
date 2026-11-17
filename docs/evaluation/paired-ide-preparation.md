# P8a: подготовка равноусловной IDE-оценки

Статус 17.11.2026: synthetic protocol и offline preparation builder реализованы. Эксперимент, передача рецензенту, role dispatch, model/native run и product gates **не выполнялись и не разрешаются** наличием пакета. M6/P8 и prerequisites P4–P6/R1/M8 остаются открытыми.

Исторический M6 сравнивал обычный чат и CLI-workflow в одном известном контексте. Новый [P8 protocol](../../evals/p8/protocol.md) сравнивает **один и тот же IDE/file workflow** последовательно и с opt-in ролями/хуками. Required checks, модель/настройки, разрешённые входы, budgets и действительные человеческие gates одинаковы; нельзя ослабить baseline или выдавать ручной journal capture за native dispatch.

## Сборка без запуска эксперимента

Из checkout с установленными base dependencies:

```powershell
python -m scripts.evaluation.prepare_pair --output .venv-ci/p8-preparation-01
python -m scripts.evaluation.prepare_pair --output .venv-ci/p8-preparation-02 --swap-labels
python -m unittest discover -s tests -p test_pair_preparation.py -v
```

Parent output-каталога должен уже существовать; каждый target должен быть новым. `.venv-ci` здесь пример локального ignored parent, не обязательное имя. Команда читает только фиксированные [synthetic scenario](../../evals/p8/scenario.json) и protocol, не принимает case ID/input path/provider/credentials. Не вызывает Python core case writers, модель, сеть или subprocess; продуктовый case не создаётся. Новый scenario «Тетрадь» содержит неполные/противоречивые основания и untrusted source instruction как данные.

Schema/input validation и чистая генерация payload находятся в `scripts/evaluation/pair_preparation.py`, filesystem/CLI — в `prepare_pair.py`. Source keys ограничены безопасным форматом и уникальны; synthetic=true обязателен; extra authorization fields отклоняются. Inputs ограничены 16 KiB каждый, payload — 16 файлами/128 KiB плюс небольшой root manifest.

## Что находится в пакете

| Область | Содержимое | Кому предназначено |
| --- | --- | --- |
| `operator/` | Conditions/protocol, owner key A/B, run-record template с pending prerequisites/authorization/caps/measurements | Только владельцу оценки |
| `reviewer/` | Общий brief, source data, input hashes, нейтральная rubric 0–2/max14 и пустой scoring template | После actual outputs/hashes и отдельного разрешения передачи — независимому reviewer |
| `preparation-manifest.json` | Hashes всех payload files, source revisions по hashes, status/preparation/readiness flags | Владельцу, не reviewer |

При подготовке outputs A/B отсутствуют, scores/examples/измерения=null, run status=not_started. Общие caps=null не означают unlimited. Authorization granted=false, allowed_actions пусты, prerequisites=not_verified; phase-two choice/gates отсутствуют, independent review не проведён. Root status=preparation_only, review_ready=false, budget_enforced=false, experiment_started=false.

`--swap-labels` — явная детерминированная перестановка, не случайное назначение и не доказательство counterbalancing. Reviewer files byte-identical при такой смене, owner mapping меняется. Это neutral labels, не гарантированная слепота: reviewer, знакомый с repository/defaults, стилем или trace IDs, может догадаться об условиях. Не передавать весь repository/operator/root manifest, фиксировать exposure deviations и guesses только после scoring.

## Файловые границы и отказ

Target создаётся exclusive mkdir; существующий даже пустой каталог или link не перезаписывается. Link на непосредственном parent отклоняется; системные ancestor aliases нормализуются canonical resolve. Output внутри любого ancestor с `state.json` запрещён, в том числе через canonical alias. Это защита сохранённых cases, не универсальный sandbox или защита от конкурентной подмены пользовательского filesystem.

Root manifest записывается последним. При I/O failure остаётся partial directory для осмотра; автоматического удаления/resume/merge нет. Повтор в тот же target отклоняется. Без валидного manifest пакет не завершён; с manifest он всё ещё не готов к run/review. CLI возвращает nonzero и фиксированную ошибку без private path. Hash manifest связывает записанные bytes при подготовке, не является подписью или проверкой последующих правок/actual outputs.

## Что необходимо для P8b

Следующий шаг — явная фиксация и проверка readiness реального парного запуска: host/model/settings, закрытые либо честно scoped prerequisites, authorization/action scope, одинаковые caps, order/familiarity, hashes и preregistered success/exclusion rules. Для strategy phase человек должен действительно выбрать общий вариант и разрешить требуемые gates; до этого сравнивается только brief/research/evidence/options. Передача reviewer требует отдельного разрешения и actual outputs с hashes. Сборщик ничего из этого не предоставляет.

Measured/estimated/unknown, human active/wait time, help/retries/errors и harm записываются раздельно. Для непроведённого review/criteria вне завершённой фазы остаётся null с reason. Отсутствующие основания в завершённом согласованном scope получают0; пустой template не становится14/14. Технический pass и пустой template не доказывают groundedness, causal effect или преимущество automation. Один известный synthetic pair остаётся exploratory. Измеренная польза P7 и независимый M6 не закрываются подготовкой P8a.
