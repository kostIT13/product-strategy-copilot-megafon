# Работа с файловым кейсом

Все примеры выполняются из репозитория с установленным пакетом (`python -m pip install -e .`). `ID` — безопасный project ID, не полный путь. Для внешнего каталога у существующих команд есть `--projects-dir PATH`. У context дополнительно есть `--instructions-root REPO`.

| Этап | Действие и сохраняемый результат |
| --- | --- |
| intake | В 01_brief.md: вопрос решения, критерии успеха, владелец/срок, ограничения и доступные данные. Задавай вопросы, способные изменить следующий шаг |
| research_plan | В 02_research-plan.md: вопросы, влияние на выбор, источники/методы, достаточность и лимиты. Показать план человеку |
| source_collection | `psa source add ID FILE` или явный `psa source fetch ID URL`; `psa source list ID`; прочитать извлечённый текст, сохранить происхождение/ограничения; `psa source assessment ID S-ID` и `psa source assess ID --input JSON` для [оценки текущего источника](../docs/source-assessment.md) |
| evidence_review | `psa claim add ID --type fact --text TEXT --source S-ID --locator LOCATOR --quote EXACT_QUOTE`; для неизвестного `psa gap add ID --question TEXT --priority high`; fact не используется без проверяемой цитаты |
| options | `psa option add ID --name NAME --role status_quo --description TEXT`; аналогично stop и change. Сравнить стоимость, пользу, риск, возражение, допущение и проверку |
| strategy | После указания человека `psa decision add ID --option NAME --option-id O-ID --owner OWNER --rationale TEXT --revisit-when TRIGGER`; затем `psa render ID` создаёт недостающие author drafts, их нужно содержательно заполнить |
| validation | Заполнить drafts/validation-plan.md; validate/verify/coverage, render и review читаемых результатов |
| completed | Показать решение, основание, ограничения и условие пересмотра; не начинать новое исследование без задачи |

Перед переходом показать человеку результат и команду `psa gate approve ID --stage STAGE --by OWNER --reason TEXT`; выполнять её только по его явной инструкции. Текущий CLI требует gates на каждом этапе; не обходить это ручной правкой state. Не превращать обновлённый целевой план в обещание уже готового свободного перехода.

Авторские стратегии: drafts/product-strategy.md, drafts/communication-strategy.md, drafts/validation-plan.md. После редактирования: `psa render ID`, `psa validate ID`, `psa verify ID`, `psa coverage ID`. Generated файлы не редактировать, флаги discard/adopt не использовать для скрытого обхода integrity.

Critic: `psa critic-pack ID` подготавливает review, не запускает модель. Для явной передачи research/evidence/critic используй [automation](automation.md): prepare/register, bound result и review основным агентом не заменяют выбор человека. Не делегируй автоматически по этапу.

По согласованной задаче current preflight и bounded hook run доступны отдельно от gate; source notice показывает revisit, release check проверяет integrity без публикации. Прочитай соответствующий [runbook](automation.md), проверь historical/freshness/required_check_passed. Stored pass и actor attribution не подтверждают текущее согласование.

Для разбора UUID используй diagnostics operation/summary, для provenance ledger — diagnostics usage; полные команды в [automation](automation.md). Summary не описывает весь кейс, guidance не разрешает mutating действия. Для legacy агрегатов остаётся `psa usage report ID`; запись доступных данных через `psa usage add` не выполняет модель. Unknown tokens/cost не подменять нулём; measured/estimated — записанная декларация, пока отсутствует независимая проверка.

При паузе сохранить разрешённые author drafts, показать текущий этап/следующий шаг, незакрытые вопросы и ошибки. Не повторять paid/fetch/import действия только потому, что чат новый. Если входы изменились — использовать resume skill и revisit. Прерванные journal operations требуют pending и явного recover точного UUID; не исправлять state/events вручную.

Если требуется вернуться к более раннему этапу активной работы, показать workflow review и дождаться явного указания человека на `psa workflow rollback`; для completed используется reopen. Материалы и прежние approvals сохраняются, затронутые gates/решение/reviews проходят заново. [Контракт возврата](../docs/workflow-rollback.md).

Перед выбором research tool при неизвестных limits/permissions можно прочитать `psa tools describe TOOL-ID` из [реестра](../docs/research-tool-registry.md). Выбирай существующий инструмент по задаче и действующим разрешениям; metadata не запускают инструмент, не выдают permission и не подтверждают readiness. Fetch требует разрешённого сетевого сценария, при отказе используй разрешённый offline fallback или покажи blocker.
