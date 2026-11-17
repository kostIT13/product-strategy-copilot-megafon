# P7d: offline research-path smoke и сверка P7

Статус 17.11.2026: фиксированный synthetic smoke реализован и включён в `demo.yml`. Он проверяет существующий file-based путь, не создаёт постоянного продуктового кейса и не ведёт собственный агентный цикл.

```powershell
python -m scripts.ci.research_smoke
python -m scripts.ci.research_smoke --report .venv-ci/research-report.json
python -m unittest discover -s tests -p test_research_smoke.py -v
```

Runner не принимает project ID/projects-dir или произвольный input source. Единственный вход — [собственный synthetic fixture](../evals/research/offline-scenario.json), ограниченный 16 KiB; [протокол](../evals/research/offline-protocol.md) зафиксирован до реализации. `--report` задаёт только явно выбранный путь выходного отчёта. Все case writes выполняются внутри собственного TemporaryDirectory, который очищается после прогона.

## Что действительно проверяется

Fixed test code читает восемь [registry](research-tool-registry.md) описаний и явно вызывает семь существующих инструментов. Public-web-fetch только описывается; заранее разрешённая synthetic local copy используется как offline fallback. Registry не выдаёт permissions и не выбирает/исполняет код по своим полям. Guard запрещает DNS/socket/process dispatch; реальные provider, HTTP и роли не вызываются.

Временный case остаётся на intake. Runner читает stage context, импортирует TXT, заменяет его новой ревизией, ищет current/obsolete/missing markers и сохраняет одну точную цитату в synthetic claim. Два коротких authored paragraphs проходят render/validate/verify и nonempty coverage. Research-plan записывается как DRAFT с snapshot/version/UUID, immediate exact replay сохраняет bytes. Ни одна из этих операций не утверждает gate, decision или semantic review.

Все read/check операции сравнивают case bytes до/после. Source instruction находится только как quote; status/stages/approvals и decision log сравниваются с начальными. Bad query/limit дают refusal. Собственный captured text временно повреждается: search отклоняет hash mismatch, verify сообщает ошибку; fixture bytes восстанавливаются в finally и повторно проверяются. Этот test-only restore нельзя переносить на пользовательский case или использовать вместо штатного recovery.

В конце явный test-only withdrawal исключает source из search, оставляет claim history byte-identical и делает coverage ссылающегося claim невалидным. Поэтому `ok=true` у smoke одновременно с `final_case_ready=false` — ожидаемый результат: проверена работа блокера, а не готовность стратегии. Temporary actor используется только writer fixture, не как согласие реального человека.

## Отчёт и отказ

JSON содержит fixture content hash, registry/bundle/descriptor versions, tool IDs, fixed checks и timing всего synthetic run вместе с cleanup. Source/role text, local paths и operation UUID не публикуются. Cost/human time=null, independent_review=false; выбор tools сделан фиксированным test scenario, не агентом. Timing не является SLA, а наличие quote не доказывает relevance/truth/effect.

Ошибка возвращает `ok=false` и exit1; unexpected filesystem/service ошибки санитизируются. Partial success не становится green report. Fault-injection tests дополнительно проверяют forged quote, fake registry authorization, attempted DNS, read-side write, fixture bounds/schema и nonzero/sanitized CLI report. CI использует base install без optional MCP/model/parser extras и показывает оба demo/research JSON в job summary. Эти JSON являются результатом текущего запуска, не historical authorization.

## Сверка оставшихся criteria P7

| Критерий | Подтверждено | Что остаётся открытым |
| --- | --- | --- |
| Registry permissions/provenance/version/cost/limits | P7c declarations, known/unknown разделены, typed schema и read-only discovery | Не runtime permission broker или independently verified usage/cost |
| Existing tools / exclusion criteria | 8 описаний; P7b candidate отклонён при precision loss, default literal сохранён | Measured benefit каждого инструмента на независимой задаче отсутствует |
| Offline degradation / evidence integrity | P7d local copy/current revision/quote/corruption/withdrawal/refusal, synthetic technical checks | Public-web-fetch здесь не выполняется; это не live website/real-product acceptance |
| Retrieval eval до расширения | P7a baseline, P7b frozen synthetic comparison и документированный negative decision | Малый набор известен автору, не independent semantic benchmark; RAG/provider не разрешён результатом |
| Agent/knowledge adaptation | Context доставляет actual stage material, rules не становятся facts | Реальная загрузка IDE, применение методик, качество, human effort и переносимость требуют отдельной оценки |

P7a–P7d локальные срезы реализованы, **весь P7 не закрыт** из-за отсутствия измеренной independent пользы. Следующая независимая подготовка P8a — равноусловный sequential baseline и opt-in automation evaluation protocol/neutral packets, с открытыми prerequisites P4–P6. Это подготовка, не новый model/native run или завершение M6. [P8/R5 протокол](evaluation/README.md), live R1/M8 и native P4 остаются отдельной приёмкой. Пользовательские кейсы, gates, решения и private IDE config этот smoke не трогает.
