# P7c: реестр research-инструментов

Статус 17.11.2026: schema/registry1.0.0, read-only CLI и optional FastMCP реализованы. Это описания поставляемого кода, не permissions enforcement, dispatcher, проверка текущего окружения или native activation. Реестр не открывает кейс и не требует project ID.

```powershell
psa tools list
psa tools describe current-source-search
psa tools describe public-web-fetch
```

MCP: `psa_research_tools()` возвращает все записи; `psa_research_tools(tool_id="public-web-fetch")` — одну. Обе поверхности используют `ResearchToolRegistryService`; schema и декларации находятся отдельно в `domain/research/`. Metadata собраны в Python package, поэтому CLI работает из установленного base wheel без knowledge root или optional extras. Никакого пользовательского каталога providers и загрузки модулей из полей реестра нет.

## Состав и выбор

| ID | Когда выбирать | Case write / сеть | CLI / MCP |
| --- | --- | --- | --- |
| `local-source-import` | Есть разрешённый выбранный локальный материал | Да / нет | `source add` / `psa_add_source` |
| `public-web-fetch` | Нужен явно разрешённый GET одной public static страницы | Да / public HTTP(S) | `source fetch` / `psa_fetch_source` |
| `current-source-search` | Нужны буквальные фрагменты уже импортированных current sources | Нет / нет | `source search` / `psa_search_sources` |
| `instruction-context` | Нужны stage-scoped skills/methods из выбранного instruction root | Нет / нет | `context`; отдельный MCP context tool не заявлен |
| `research-artifact-record` | Нужно сохранить IDE-authored research-plan DRAFT с UUID/version/snapshot | Да / нет | `artifact record` / `psa_record_research_artifact` |
| `project-validate` | Проверка структуры, workflow policy и generated integrity | Нет / нет | `validate` / `psa_validate` |
| `evidence-verify` | Проверка captured hashes и exact quote/locator | Нет / нет | `verify` / `psa_verify` |
| `strategy-coverage` | Проверка evidence labels в strategy paragraphs | Нет / нет | `coverage` / `psa_coverage` |

Возвращаемые `writes_case`/`network_access` описывают **сам инструмент**, а не эффект чтения реестра. Например public-web-fetch требует network permission, но чтение его описания не выполняет GET и не предоставляет permission. Выбор остаётся за IDE-агентом в пределах задачи и действующих указаний человека. При отказе policy, неподходящем формате/смысле или неизвестных правах использовать записанный fallback/показать blocker; не обходить отказ другим provider.

Каждая запись содержит descriptor_version, implementation_contract, CLI/MCP entrypoints, choose_when/exclude_when, permission_requirements, provenance, limits со scope/enforcement, limits_note, offline_fallback, evaluation_status и evidence_refs. Entry points — данные для навигации, их нельзя выполнять автоматически из registry payload. Descriptor version — версия описания, не обнаруженная версия installed library/host. Evidence refs — пути текущего checkout, не подписанные immutable source attestations; для воспроизводимого run отдельно сохранять Git revision и hashes.

## Честные границы

- `availability` и `provenance_freshness` остаются `not_checked`: discovery не проверяет установленные parsers/MCP, host support, актуальность источников или доступность сети.
- `registry_is_enforcement`, authorization_evaluated/granted, execution_started, canonical_writes, workflow_approval_granted и native_activation_allowed — false. Это discovery metadata; существующие services продолжают самостоятельно проверять state/locks/limits. Реестр не оценивает согласие человека и не заменяет gates/reviews.
- `model_api_required=false` описывает зависимости этих восьми tools, а не telemetry выполненного run. `provider_cost=null`, cost_basis=not_measured; отсутствие вызова не превращается в measured zero cost.
- Fetch time_budget/timeout помечены cooperative_deadline: это не process watchdog или гарантия времени DNS. CLI artifact input cap не выдаётся за MCP request cap.
- Для legacy validate/verify/coverage нет uniform aggregate resource cap. Пустой limits вместе с limits_note означает отсутствие такой декларации, не безлимитное разрешение и не доказательство hardening.
- Search сохраняет `literal_ignore_case_v1`, known semantic misses и source-ID порядок; [P7b candidate](retrieval-comparison.md) отклонён и в registry отсутствует. Search evaluation_status — только synthetic_kernel_baseline_only. Остальные tools — not_measured; ни один status не утверждает independent agent benefit.

Неизвестный ID/попытка передать объект вместо ID отклоняется фиксированной ошибкой, без отражения приватного ввода. В API нет action/execute/authorize/request-file/URL/path и установки другого registry root. Возвращаемый JSON не меняет shipped declarations. Native IDE support не повышается от наличия MCP tool или списка.

## Проверка и сопровождение

`test_research_tool_registry.py` проверяет чтение без file/network/process calls, refusal forged IDs/authorization, независимость возвращённого JSON, соответствие search/fetch limits коду, существование CLI routes/provenance refs, CLI без optional dependencies из другого cwd и реальную stdio parity/read-only annotations/существующие MCP names. Это технические contracts, не семантическая оценка выбора инструмента агентом. CLI/base tests не создают case; stdio использует обычный server cwd и временный sentinel для сравнения bytes, без dispatch research tools.

При изменении tool contract обновлять соответствующее описание/descriptor_version и registry_version, связанные инструкции и meaningful tests. Не добавлять более сильные permissions/limits/benefit на основании одного metadata поля. Bundle1.1.2+ доставляет навигацию через README/workflow и research skill; generated adapters пересобираются штатным sync script. Role profiles и knowledge1.0.0 не менялись.

P7c завершён в этом scope. P7d выполнен: [offline research scenarios и сверка оставшихся criteria P7](offline-research-smoke.md). Далее независимая подготовка P8a перед [P8/R5](evaluation/README.md), без запуска оценочного/native/model run. Измеренная польза всех tools и independent evaluation остаются открытыми, как P4/P5/P6/R1/M6/M8. Этот registry не закрывает весь P7.
