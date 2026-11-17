# P5d: приватность diagnostics и границы недоверенных материалов

Срез от 16.11.2026 дополняет [handoffs](subagent-handoffs.md), [task journal](subagent-journal.md) и [namespace compatibility](journal-version-compatibility.md). Новые permissions, автоматический dispatch и вызовы моделей не добавлены.

## Изменённая диагностика

CLI-команды host/hook/subagent раньше передавали текст OSError в SystemExit: ошибка открытия request могла раскрыть приватный абсолютный путь. Общий interface formatter теперь выдаёт фиксированные сообщения для runtime/model/encoding ошибок. CLI подавляет цепочку исходного исключения при выводе automation ошибки.

| Ошибка, достигшая boundary | Ответ |
|---|---|
| OSError | automation I/O unavailable; check local paths, permissions and pending operations |
| UnicodeError | automation text encoding invalid; expected UTF-8 input |
| Pydantic ValidationError | automation schema invalid; inspect local request, catalog and journal integrity |
| Обычный domain ValueError | Сохраняется авторский отказ, например stale binding или unsupported namespace |

Subagent prepare/journal MCP используют тот же formatter для ValueError, включая необработанные ValidationError/UnicodeError. Их существующие фиксированные I/O ошибки сохранены. Host/hook MCP уже возвращали фиксированные ToolError и не требуют замены. CLI возвращает ошибку без частичного JSON; отсутствие подробного пути в сообщении не означает автоматическую починку или повтор операции.

Повреждённый role catalog **уже** очищался в HandoffService через validation_message; regression сохраняет этот safe refusal, а не объявляет новую исправленную утечку. Новый fallback защищает model errors, которые действительно доходят до interface. Передавать произвольные тексты внешних исключений как обычный domain ValueError нельзя: эта ветка предназначена для авторских диагностик.

## Негативный корпус

Проверены реальные CLI stderr для трёх automation groups с отсутствующим request под приватным canary-путём: непустой exit code, пустой stdout, без пути/canary/traceback. In-process CLI также проверяет malformed catalog и неверный UTF-8 role guidance. Реальный FastMCP stdio проверяет prepare/register при malformed catalog и prepare при invalid UTF-8: без input_value/private canary, без записи в кейс.

Выбранные authored материалы проверены с тремя payloads: псевдо SYSTEM с требованием утвердить gates, JSON с shell/network permissions и псевдо system markup с требованием прочитать .env/активировать hooks. Их bytes остаются в task.inputs; canonical role instructions остаются отдельными и неизменными. Requested goal не заменяется payload, execution_started/canonical_writes остаются false, bytes кейса не меняются. Существующие handoff/contract tests дополнительно проверяют запрещённые permissions и snapshot/result binding.

Это проверка программного разделения данных и полномочий. Модель в корпусе не вызывалась; устойчивость конкретной LLM к semantic prompt injection и native IDE acceptance этим не доказаны. При разрешённой передаче handoff выбранный текст может содержать чувствительные данные: success packet намеренно возвращает выбранные материалы, а не автоматически редактирует их.

## Область действия

Изменение касается runtime error rendering указанных automation interfaces. Оно не является глобальным scrubber всех CLI-команд, argparse diagnostics, success packets, пользовательских actor/reason полей, сторонних журналов или stack traces debugger. Secret scanning репозитория и permissions/human gates сохраняют отдельную роль. Действительные роли/permissions не выводятся из строки SYSTEM или чужого approved_by.

P5 частичный. [P5e dependency/artifact integrity](dependency-artifact-integrity.md) и сверка рисков выполнены; далее независимый P6a diagnostics. Новая cross-schema migration по-прежнему требует целевой схемы. Native enable/acceptance P4 и R1/M6/M8 остаются открытыми.
