# Утверждение стратегии для внутреннего использования

Этот срез принимает сохранённый `strategy_plan` run существующего опционального API-инструмента. Приём черновиков непосредственно от IDE-агента без нашего LLM-клиента ещё предстоит подключить в этапе 6; эта реализация не объявляет такой путь готовым.

После decision-bound `strategy_plan` человек может принять конкретный черновик для внутреннего review и экспортировать его. Нужна миграция `0017_strategy_approvals`: `alembic upgrade head`. Это отдельная запись, а не изменение исходного запуска, канонического решения или workflow gate.

## Порядок работы

1. Получить успешный strategy run по [сохранённому выбору](strategy-plan.md).
2. Выполнить [связанный critic](agent-critic.md) именно этого strategy run. Его verdict остаётся рекомендацией, даже если все разделы поддержаны источниками.
3. Прочитать весь preview: стратегию, коммуникационные гипотезы, эксперименты, пробелы, оговорки, источники, critic и человеческое решение.
4. Только по явной инструкции человека заполнить команду и сохранить утверждение. Замечания/неопределённость critic требуют отдельного человеческого `critic_resolution`; поле не превращает гипотезу в факт.
5. Экспортировать внутренние артефакты. Экспорт повторно проверяет актуальность источников и неизменность рассмотренных данных.

```powershell
psa-main strategy preview-approval PROJECT STRATEGY_RUN_UUID CRITIC_RUN_UUID
psa-main strategy approve PROJECT --input approval.json
psa-main strategy approval PROJECT STRATEGY_RUN_UUID
psa-main strategy export PROJECT STRATEGY_RUN_UUID
```

Формат локального `approval.json` (UUID и hash берутся из preview, здесь placeholders):

```json
{
  "strategy_run_id": "STRATEGY_RUN_UUID",
  "critic_run_id": "CRITIC_RUN_UUID",
  "preview_hash": "SHA256_FROM_PREVIEW",
  "owner": "Ответственный человек",
  "review_note": "Проверены источники, предположения, риски и план проверки",
  "critic_resolution": "Использовать только для внутреннего эксперимента; спрос ещё предстоит проверить",
  "scope": "internal_review",
  "confirmed": true
}
```

`critic_resolution` можно опустить только при verdict `supported`. Не выводить согласие из ответа модели: `confirmed` — строгий boolean и должен соответствовать реальной инструкции человека. Owner — заявленное имя, без проверки личности/RBAC. MCP-аннотации также не являются авторизацией.

## Что сохраняется и проверяется

Отдельные domain command, application service/port и PostgreSQL adapter сохраняют один receipt на project/strategy run. Snapshot включает проверенный draft, critic, контекст принятого решения/выбора, версии источников и fingerprints. Перед записью транзакция блокирует project и рассмотренные записи, заново сверяет runs, selection, strategy input, решение/вариант/их связи и источники. Изменение после preview отклоняет всю запись. Повтор той же команды, включая конкурентный, возвращает тот же receipt; другая команда для этого run отклоняется.

`insufficient_evidence`, неверно связанный critic, чужой project, устаревшие источники и изменённые основания не принимаются. Исторический receipt остаётся читаемым при устаревании и повторяется без новой записи; это не разрешение на новый экспорт. Для обновлённых оснований нужен новый рассмотренный strategy run. Отзыв/замена утверждения и полноценный revisit пока не реализованы.

## Экспорт

Команда возвращает UTF-8 JSON envelope в stdout. Поле `files` содержит имена, текст `content` и SHA-256 байтов UTF-8 для `strategy.md`, `communication.md`, `experiments.md`, `review.json`. Клиент может сохранить их локально; CLI/MCP сам не пишет файлы по произвольному пути и не отправляет их наружу. Markdown сохраняет структурированные разделы как отступленный JSON, чтобы недоверенный текст источников не интерпретировался как HTML или Markdown-разметка. `review.json` содержит полный receipt и источники для аудита. Это внутренний пакет, не обезличенная публичная выгрузка.

Экспорт детерминирован для одного receipt и неизменных оснований. Hash проверяет целостность содержимого, не является подписью автора. Актуальность проверяется на момент чтения; выданный файл не обновляется и не отзывается автоматически при последующем изменении источников.

Везде сохраняются `scope=internal_review`, `publication_approved=false`, `customer_promises_approved=false`, `workflow_approval_granted=false`. Коммуникации остаются `hypothesis/open_question`. Проверка внешних обещаний по capability registry и разрешение публикации ещё не реализованы в этом срезе; утверждение их не обходит. Нет автоматических claims/capabilities/решений, вызова модели или отправки сообщения.

## MCP и проверки

Main FastMCP содержит 19 tools с учётом отдельного promise preflight. Новые: `psa_main_preview_strategy_approval`, `psa_main_approve_strategy`, `psa_main_get_strategy_approval`, `psa_main_export_strategy`. Только approve записывает receipt, он идемпотентен. Остальные read-only, все четыре без модели. Используется тот же application service, что в CLI.

```powershell
python -m unittest discover -s tests
python scripts/smoke_strategy_plan.py
```

Strategy smoke также проверяет approval/export: PostgreSQL concurrency, rollback при изменении решения/critic/input/source после preview, project-bound FK, CLI и настоящий stdio, stale export и исторический replay. Ответы модели синтетические через MockTransport; API-ключи и живая модель не нужны. Синтетические проекты остаются в локальной development-БД.
