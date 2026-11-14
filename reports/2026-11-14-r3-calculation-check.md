# R3: проверка авторских расчётов по текущим цитатам

Завершено: 14.11.2026 19:58, Asia/Novosibirsk. Ветка `feature/main-solution-roadmap`.

## Что сделано

- В отдельные domain-модули вынесены строгий контракт `psa-calculations-v1`, чтение авторского JSON block и точная арифметика; application service использует существующий validation/evidence port под общим lock.
- Поддержаны доля в процентах, отношение, процентные пункты и относительное изменение. Два операнда привязаны к current factual claim, точным source/locator/quote и spans числа/единицы. Decimal literals преобразуются в rational fractions; скрытого float tolerance нет. Округление задаётся явно: half_even, 0–12 знаков.
- Проверяются единицы, заявленные metric/population/conditions, отношение периодов, положительный знаменатель и диапазон доли. Stale/withdrawn evidence, иной locator, неверные единицы/результат и malformed/null/duplicate JSON не дают arithmetic_match.
- Добавлены read-only `psa validation calculations CASE` и FastMCP `psa_check_calculations` с одинаковым результатом; blocked CLI завершает работу с exit 3.
- Semantic validation review включает проверку присутствующего calculation block и не принимает accepted assessment при blockers. Исправленный документ требует нового review; replay старого completed gate UUID сохраняет исторический результат и текущие файлы.
- Добавлены контракт, ссылки CLI/MCP, обновления quality canon, девяти generated adapters, основного плана и roadmap.

## Смысловые коммиты

1. `ecb9023`: domain/application, точные операции и проверки evidence/контекста.
2. `8b1d88e`: CLI/FastMCP и real stdio parity.
3. `845fe6e`: semantic validation acceptance и historical gate replay.
4. `7c9e696`: отдельные проверки разных source units и периода знаменателя.
5. Отдельный documentation/report commit фиксирует контракты, планы и результаты проверок.

## Проверки

- Core: 8 tests, 25.308 s, OK. До добавления последнего negative test общий targeted прогон core + CLI/MCP + semantic gate: 9 tests, 34.309 s, OK.
- Clean base без MCP/model/SQL extras: 8 calculation tests, 316.476 s, OK; полный файловый workflow completed → reopen/reapprove → copy/resume также прошёл, model_calls=0.
- Оба локальных demo прошли validate/verify/coverage/resume/render в копиях; оригиналы не изменены, model_calls=0.
- Ruff, sync9, docs186 и repository history прошли. Native Gitleaks 8.30.1: history/tree без находок, negative probes passed.
- Полный suite на окончательном коде: **407 tests, 943.953 s, OK (skipped=1: Windows symlink privilege unavailable)**. Это локальный результат, не remote Actions run и не оценка качества реального продуктового решения.

## Границы

Это проверка явно описанной двухоперандной формулы по выбранным литералам, не извлечение всех чисел из prose. Нет block — not_applicable, не подтверждение полноты документа. Совпадение авторских labels не доказывает правильность когорты/периода/знаменателя, семантику единиц или причинный эффект. Semantic/numeric alignment, context truth, observed effect и permissions остаются false; human review обязателен. Поддержаны до 10 calculations; размер packet ограничен 256000 UTF-8 байт без усечения.

Более широкая numeric coverage и новый разрешённый кейс остаются открытыми. Live R1/M8 и независимая M6 отложены, пройденными не объявлены. Workflow rollback незавершённой работы остаётся отдельным этапом R4. Реальные кейсы, .env и БД не читались/не менялись, платные API/модели не вызывались; hooks/subagents, БД и контейнеры не добавлялись. Test actors/approvals относятся только к изолированным synthetic fixtures. Длительность и стоимость IDE-сессии отдельно не измерялись.
