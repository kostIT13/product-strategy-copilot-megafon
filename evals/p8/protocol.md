# P8a / R5: пререгистрация сравнения IDE workflow

Статус: preparation only. Сценарий синтетический; внешние/модельные/native прогоны, передачи оценщику и human gates не разрешены этим файлом. P4–P6 и live R1/M8 остаются открытыми. Package preparation не повышает native support и не закрывает M6.

## Два новых условия, отдельно от исторического M6

Sequential: тот же IDE/model, AGENTS/skills/knowledge и файловый CLI/MCP workflow, основные required checks и действительные human gates, без role dispatch и hook runs. Automation: те же входы и обязательные checks, плюс заранее выбранные и отдельно разрешённые research/evidence/critic handoffs и fixed hook checks. Нельзя убрать проверки из baseline ради преимущества automation. Manual journal capture нельзя записывать как native dispatch; это отдельное exploratory condition при явной смене протокола.

В обоих условиях разрешены только общие исходные материалы и одинаковый budget. Ответ другого условия, completed strategies/decisions и owner key агенту не показывать. Использовать свежие контексты, зафиксировать одинаковые IDE/model/version/settings, code/harness/input hashes, работу из одной и той же исходной case copy и знакомство оператора с задачей. Для старта budget/time/token/cost caps должны быть заполнены до первого запуска; null означает неизвестно, не unlimited и не разрешение расходов.

Условия требуют одинакового product choice для фазы стратегии, но такой выбор должен реально дать человек: протокол его не выдумывает. До действительного выбора сравнивать только brief/research/evidence/options. Ожидание gate/choice записывать отдельно; неполный запуск не оценивать как завершённую стратегию. Ошибки, refusals, retries, interruptions, ручную помощь и отсутствие данных сохранять, не выбрасывать неудобные пары.

## Что подготовить до первого run

Заполнить owner record: scope automation и allowlisted actions/host acceptance evidence; operator authorization отдельно от budget; preregistered order; одинаковые time/token/provider-cost caps; код/версии; одинаковые source revisions; критерий допуска/исключения. Открытые prerequisites не помечать passed без actual evidence. Для независимого reviewer нужны действительное согласие/разрешение передачи и свежий контекст без условий/owner key. Если нет этих условий, сборка пакета остаётся preparation_only.

CLI подготовки не выполняет эту процедуру за владельца: создаёт новые файлы с null measurements и pending readiness. `--swap-labels` меняет A/B assignment; это явная детерминированная перестановка, не рандомизация. Сам label swap или повторение известной задачи не дают independent replication/counterbalancing; для нескольких пар нужны заранее выбранные разные задачи и раскрытие learning/order effects.

## Review и ограничения слепоты

Передавать только `reviewer/`, после появления actual outputs A/B и фиксации их hashes. В preparation package outputs отсутствуют; readiness=false. `operator/`, root manifest и полный repository с defaults не передавать оценщику. Neutral labels не гарантируют слепоту: стиль/trace IDs/знакомство с кодом могут раскрыть условие. Сначала scores с примерами, затем guesses/confidence/clues и exposure deviations. Owner key раскрывается после фиксации scoring.

Рубрика прежняя, по 0–2 (max14), но старые exploratory11/14 и14/14 не являются результатами нового сравнения: основания; факты/гипотезы/синтетика; альтернативы; контраргументы/пересмотр; согласованность стратегии; validation; resume/provenance. Отсутствующий из-за незавершённой фазы criterion остаётся null с reason, а не выдуманной оценкой. Технические validate/verify/coverage и correctness цитаты фиксируются отдельно от semantic quality.

По каждой паре отдельно записать model elapsed, human active/wait time, tokens, cost/currency/basis/source, help/retries/errors и harm (fabricated evidence, unsafe promise, unauthorized action, loss of human choice). Unknown остаётся null; записанное measured/estimated без независимого provenance не объявлять verified. Нельзя суммировать неизвестные расходы как нули. Actual runtime cancel/budget enforcement не выводить из planned cap.

Один известный synthetic pair даёт exploratory observation, не обобщаемый эффект. Публиковать paired differences вместе с harms/limitations и всеми deviations, без автоматического winner. Independent review и достаточное число заранее согласованных разных задач обязательны для claims о пользе; снижение cost/time нельзя утверждать при missing measurements. Никакой template/schema/CI pass не закрывает independent M6/P8 или разрешает production adoption.
