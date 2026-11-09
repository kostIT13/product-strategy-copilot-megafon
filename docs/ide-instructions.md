# Инструкции и контекст IDE-агента — R1

Реализованы общий AGENTS.md, четыре canonical skills, тематические workflow/quality/safety, generated host adapters и read-only `psa context`. Это инфраструктура инструкций, не доказательство качества стратегии или фактической загрузки во всех IDE. R1 остаётся частичным до живого нового кейса и host acceptance; M6/M8 автоматически не закрываются.

## Запуск из репозитория

```powershell
python -m pip install -e .
python scripts/sync_harness.py --check
psa init research-case
psa context research-case
```

`init` используется для действительно новой задачи; `context/status/resume` для существующей. Из другого cwd: `psa context CASE --projects-dir CASES_PARENT --instructions-root REPOSITORY_ROOT`. Context читает committed state текущего файлового CLI, фиксированные правила, выбранные skills и knowledge/catalog; возвращает полный выбранный текст, ID/version и SHA-256, без модели, БД, записей в кейс и автоматического gate. Ошибка отсутствующего материала не заменяется пустым успешным контекстом. Материалы должны оставаться внутри instruction root без symlinks.

Версии knowledge и bundle не означают доказанную эффективность. Context hash связывает полученные правила и данные состояния; он не даёт разрешения на существенное решение и не подтверждает поведение модели. Для resume доступен отдельный skill, его можно прочитать явно при любом этапе. Если CLI context недоступен, открыть AGENTS.md и agent/README.md вручную, обозначив ограничение.

## Адаптеры

| Среда | Файлы | Что подтверждено |
| --- | --- | --- |
| Codex | Корневой AGENTS.md и .agents/skills; .codex/README.md — пояснение | Формат сверён с официальной документацией; fresh-session loading в установленном host не проверен |
| Cursor | .cursor/rules/product-strategy.mdc, alwaysApply, ссылка на канон | Генерация/синхронизация проверяются; фактическое прочтение ссылок проверять в host |
| Claude Code | CLAUDE.md с импортом канона; .claude/skills — generated copies | Не зависят от поддержки AGENTS.md конкретной версией; host ещё не проверен |
| Qwen Code | QWEN.md с явной навигацией к канону/context | Навигация не доказывает native skill discovery |
| SourceCraft/другая IDE | Явное чтение AGENTS.md/context через CLI | Manual fallback; native settings и обнаружение skills не заявлены |

Основания форматов проверены 09.11.2026: [OpenAI AGENTS.md](https://developers.openai.com/codex/guides/agents-md), [OpenAI skills](https://developers.openai.com/codex/skills), [Cursor rules](https://cursor.com/docs/rules), [Claude memory/imports](https://code.claude.com/docs/en/memory), [Qwen memory](https://qwenlm.github.io/qwen-code-docs/en/users/features/memory/). Сверка документации не заменяет проверку установленной версии. Секретов/MCP endpoint settings, hooks или автоматических субагентов в adapters нет.

После изменения канона выполнить `python scripts/sync_harness.py --write`, затем `--check`. Не редактировать generated copies отдельно. Check проверяет полное содержимое и обнаруживает drift канона/копий; чужие неуправляемые adapters не перезаписываются, stale copies требуют явного разбора. Локальные проверки не включают платный host/model запуск.

## Проверка в реальной IDE

1. Открыть репозиторий в свежей сессии; записать host/version, дату и доступные инструменты. Попросить показать фактически загруженные инструкции и выбранный skill, а не соглашаться с заранее данным названием.
2. Дать новый неоднозначный продуктовый запрос с разрешёнными материалами; ожидать brief/research plan, существенные неизвестные и `psa context`. Проверить реальные ID@version материалов и вопрос из метода, который повлиял на исследование.
3. Проверить, что текст источника с указанием «утвердить решение/отправить файл» трактуется как данные; fake owner/critic не создаёт gate.
4. Сохранить артефакты, закрыть чат и продолжить через status/resume/context; не повторять уже завершённую запись или fetch автоматически. Смену IDE проверять отдельно.
5. Зафиксировать результат/ошибки/время/стоимость/помощь человека в reports/ и author methods-used.md. Нет фактического запуска — статус not_verified, не passed.

Эти проверки предполагают доступ к host и модели; в этой итерации их результат не выдумывается. Автоматический тест контекста/CLI проверяет механизм доставки, а не самостоятельное исследовательское поведение. Старая PG-зависимость некоторых модулей/CI выводится в R2; R1 не объявляет весь runtime уже освобождённым от неё.
