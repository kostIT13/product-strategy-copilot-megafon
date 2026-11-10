# Качество результата

Сохраняй trace: тезис → claim → source revision/locator/точная цитата. Разделяй fact, interpretation, hypothesis, forecast и synthetic. Используй [каталог knowledge](../knowledge/catalog.json) по задаче; методика не доказывает потребность или эффект. В drafts отмечай тезисы существующим `[C-ID]` либо `[HYPOTHESIS]`, `[COMMITMENT]`, `[OPEN QUESTION]` согласно [coverage](../docs/coverage.md). Метка не исправляет ложный смысл.

Отзыв claim выполняй `psa claim withdraw ID C-ID --by PERSON --reason REASON` только по явному указанию человека. Затем читай `psa claim impact ID`: effective inactive claims не используются как актуальные основания, зависимые capabilities/options/decisions требуют review. Исходные записи и старые approvals не переписываются; текущий выбор человека не меняй автоматически. Новый render показывает effective evidence и audit history; replay старого render не является новой генерацией. [Контракт](../docs/claim-withdrawal.md).

Минимум три разных варианта: status_quo, stop, change. Для каждого — польза, затраты, риски, сильное возражение, допущение и проверка. Если данных мало, вариант формулируй как ограниченную гипотезу с пробелами, не выдумывай доказательства.

Продуктовая стратегия: аудитория/задача, альтернативы, выбранное направление и отказы, ценность, затраты/доходы как факты или явные допущения. Коммуникационная: аудитория/ситуация, барьер понимания/выбора, сообщение и подтверждение обещания продуктом, роль каналов. Проверяй смысл ограничений available/planned/unavailable, а не только ID capability.

Эксперимент: ожидаемое изменение, определение метрики/единицы/сегмент, baseline или план её получения, сравнение/критерий, окно наблюдения, защитные показатели, правило остановки и ответственный. Неизвестное значение маркируй и назначай способ/срок измерения. Синтетический респондент даёт гипотезы, не оценку спроса.

Перед новым strategy/validation gate выполни `psa strategy check ID`: обязательные разделы обеих стратегий должны быть заполнены. Это структурная проверка, не подтверждение смысла, согласованности или истинности; coverage/verify/promise preflight остаются отдельными проверками.

Перед новым validation gate выполни `psa validation check ID`. В authored drafts/validation-plan.md нужен один psa-validation-v1 JSON block: metric definition/unit/population/data source, baseline reported с current factual claim либо unknown/null с reason/measurement owner/deadline, comparison, success criterion, observation window, guardrails/stop rules и owner/decision rule. Это план, не результат эксперимента; numeric alignment и разрешение эксперимента не выводятся из успешного check. Формат и пример — [контракт](../docs/validation-plan-contract.md).

Явное решение человека и его смысл важнее положительного critic verdict. Перед окончанием сообщи сильнейшее возражение, неопределённости, условие пересмотра, время/расходы и ошибки/помощь человека. Автотесты схем/цитат не являются независимой оценкой стратегии.
