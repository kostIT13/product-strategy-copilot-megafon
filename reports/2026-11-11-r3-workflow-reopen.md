# R3: явный review и reopening завершённого workflow

Завершено: 11.11.2026 00:55 (Asia/Novosibirsk). Ветка `feature/main-solution-roadmap`. Timestamp завершения и итоговые результаты — в development-log.md; длительность итерации отдельно не замерялась.

## Сделано

Добавлены отдельные typed domain command/planner, application service/port и filesystem decision-proof reader. CLI `psa workflow review/reopen` и FastMCP `psa_review_workflow` / `psa_reopen_workflow` используют один service. Read-only packet показывает stages/history/claim impact и hash точных state/events/non-journal inputs. Автор, причина, выбранный этап, review hash и expected version обязательны для reopen; политика требует явного указания человека. Старые approvals и продуктовые решения не переписываются.

Reopen разрешён только для completed workflow с согласованным stages=done. Выбранный этап становится in_progress, последующие not_started; предыдущие done сохраняются. State/event получают reopen history с actor/reason/time, invalidated stages, historical approval IDs и snapshot hash. Generic workflow v1 journal/ACTIVE/receipt/recovery поддерживает новый request kind с полным deterministic reconstruction after-state/event; v1–v5 исторические bundles сохранены. Exact UUID replay возвращает прежний event без сброса позднейших writes.

Новые gates проходят выбранный и последующие этапы заново. Возврат к strategy или раньше требует нового явного человеческого decision, подтверждённого immutable journal result/COMMITTED receipt после reopen. Обнаружено существующее поведение frozen v4: decision event record_id может содержать option_id из-за порядка выбора поля. Новый reader проверяет actual reconstructed result, прежний builder и receipts не изменены. Unjournaled modification решения не принимается. Возврат только к validation не требует нового выбора при актуальных основаниях; existing inactive-evidence и semantic review requirements сохраняются. Любой новый validation gate после reopen требует свежий render v2.

CLI resume/MCP status показывают reopen history. Base smoke теперь проходит completed → review → reopen → новое решение → повторные gates → completed → copy/resume в чистом окружении без SQL/model/MCP extras. Обновлены README, MCP/recovery/lifecycle docs, quality canon, 9 generated adapters и оба плана.

## Проверки и исправления

Targeted suite проверяет read-only review, сохранение всех прочих bytes/choices/approvals, сброс выбранного suffix, запрет пропуска gates, новое journal-backed решение, отказ после подмены решения, свежий render, повторное reopen/recomplete, hash/version/actor/busy/conflicts и неконсистентный completed state. Проверены rehashed bundle tampering, CLI/реальный FastMCP stdio parity, реальные остановки отдельного процесса на preparation/ACTIVE/state/events/receipt/completion с переносом каталога/recover и позднейшими записями.

Первый прогон выявил неправильный вызов main(argv) и отсутствие option_id в тестовом fixture; исправлены тесты. Следующий выявил неверное предположение о v4 record_id; guard заменён на reconstructed result/receipt. Затем исправлено имя project_dir в reader для контракта shared-lock decorator. Clean-base полный сценарий и оба demo уже прошли; model calls=0. Итог: полный unittest suite — 360 tests за 463.366 s, OK (1 skipped: Windows symlink privilege unavailable). Финальный targeted suite — 6 tests за 54.755 s, OK. Ruff/formatting, sync 9 adapters, docs 176 documents, repository-history и diff checks прошли. Native Gitleaks 8.30.1 history/tree/negative probes — без находок.

## Границы и следующий шаг

Reopen не является новым одобрением стратегии/эксперимента/публикации; автор — self-reported attribution. Review hash подтверждает выбранный снимок, не смысл и не защиту от владельца, переписывающего весь каталог. Возврат незавершённого workflow назад ещё не реализован. Source withdrawal и semantic/numeric alignment остаются следующими задачами R3. Отложенные live R1/M8 и независимая M6 не закрыты; production-ready roadmap будет отдельно расширен после R3, hooks/subagents автоматически не включались.

Реальные пользовательские кейсы, .env и БД не читались/не менялись; моделей и платных API не вызывали. БД/контейнеры и второй agent loop не добавлялись. Все проверки выполнялись на синтетических временных данных и копиях разрешённых demo; стоимость/длительность IDE-сессии не измерялись.
