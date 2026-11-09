# R1: инструкции и контекст IDE-агента — 9 ноября 2026, 17:38 (Asia/Novosibirsk)

## Сделано

Создан корневой AGENTS.md с разделением режима разработки и продуктового кейса, agent/workflow.md, quality.md, safety.md и навигация. Четыре canonical skills в .agents/skills: psa-research, psa-options, psa-strategy, psa-resume. Они направляют модель к существующему файловому CLI и knowledge, требуют обязательные альтернативы/полноту стратегии/план проверки и сохраняют явный человеческий gate. Не вводятся отдельный агентный цикл, публикация или автоматические субагенты.

Добавлена read-only команда psa context ID с --projects-dir и --instructions-root. Отдельный InstructionContextService читает текущий этап и возвращает полный текст правил, выбранных skills и knowledge с ID/version/SHA-256 и общим context_hash. Повреждение состояния, missing material, escaped catalog paths и превышение лимитов не маскируются успешной пустой загрузкой. Context не пишет кейс, не исполняет модель и не делает выводов о реальной загрузке в host. Для установки вне репозитория нужен явный instruction root; standalone wheel с embedded harness не заявляется.

Реализованы scripts/sync_harness.py --write/--check и девять generated files: CLAUDE.md, QWEN.md, Cursor rule, explanatory .codex/.claude README и четыре Claude skill copies. Canon один; check обнаруживает drift и stale copies, write не перезаписывает unmanaged files и не выходит через symlink. Host-global config и MCP endpoints не меняются. SourceCraft — честный manual fallback, без выдуманного native settings формата.

Knowledge catalog/README отмечают доступный stage-scoped context; версии шести методических материалов остаются 1.0.0 и их содержимое не менялось. Подключение инструкциями не выдаётся за автоматический API prompt/RAG integration или оценку качества на реальном кейсе. Runbook docs/ide-instructions.md содержит процедуру фактической host acceptance и ссылки на первичные источники форматов.

Обновлены README, основной план/roadmap (R1 частично выполнен), CI docs job с обязательным instruction-sync, docs required files, allowlist source ZIP и MANIFEST для source assets. Скрытые auth/settings файлы не допускаются новой packaging allowlist. Target R2 без PG/Docker остаётся отдельной работой; существующие зависимости/схема/CI backend не удалялись.

## Проверено

- Все 200 unit-тестов прошли; 7 новых проверяют реальные stage-scoped contents/hashes, отсутствие записи в кейс, смену состояния/методики, копирование каталога, missing/escaped/corrupt inputs, canonical/generated drift, stale и unmanaged adapters, CLI из другого cwd и упаковочные границы.
- Четыре skills прошли bundled skill-creator quick_validate в UTF-8 режиме. Первый запуск helper использовал системную cp1251 и не прочитал часть русских текстов; повтор с -X utf8 успешен без изменения helper.
- Sync --write/--check и Ruff прошли. Source sdist собран uv в изолированном окружении, проверено присутствие всех 16 выбранных canonical/generated entry assets (методики дополнительно включаются прежним knowledge MANIFEST). Попытка build --no-isolation сначала обнаружила отсутствующий setuptools, uv build с isolation прошёл.
- Оба файловых demo прошли validate/verify/coverage/resume/render во временных копиях, model_calls=0; исходные demo не изменены. Это regression replay, не новое исследование агента.
- Форматы сверены 09.11.2026 по официальным OpenAI AGENTS/skills, Cursor rules, Claude memory/imports и Qwen memory страницам; ссылки в runbook. Использованы skill-creator и OpenAI Docs. Проверка файлов/форматов не заменяет installed-host тест.
- Docs links (137 документов), git diff, instruction-sync и forbidden-path/full-history checks прошли. Docker-based Gitleaks не запускался в этом срезе; его замена на native scanner остаётся R2.

## Открыто

R1 ещё требует нового живого IDE-native кейса и фактического обнаружения/применения инструкций/skills в hosts с записью версии, времени/стоимости и ошибок. Эти результаты не выдумывались; M6/M8 остаются открытыми. Исторические API-specific checklist вопросы применяются к файловым IDs по skill guidance; полного переписывания всех методик/сервисов не делалось. R2 безопасного переноса и вывода PG/Docker dependencies ещё не выполнен.

Реальные модельные API, PostgreSQL и Docker в этой итерации не использовались; .env/секреты/данные БД не менялись. Рабочие кейсы в Git не добавлялись. Длительность отдельно не замерялась.
