# P3d: офлайн release checks без публикации

Явный `release_check` hook проверяет существующий локальный дистрибутив. Сборка, установка зависимостей, исполнение кода из архива, Git tags, draft и публикация не запускаются. Это отдельная статическая проверка, не подтверждение всей готовности релиза.

## Команды

Сначала соберите артефакты по [инструкции дистрибутива](distribution.md), для release — из чистого commit с `--require-clean`. Затем:

```powershell
psa hook prepare-release --archive dist/release/product-strategy-agent-0.1.0.zip --operation UUID
psa hook check-release --archive dist/release/product-strategy-agent-0.1.0.zip --request REQUEST.json --timeout 30
```

Prepare stdout сохраняется в REQUEST.json. Archive path — явная конфигурация CLI/MCP caller, он не принимается внутри недоверенного HookRequest. Request содержит только operation UUID, release_check и SHA-256 **сырых bytes manifest**, без команд, разрешений или URI для загрузки. Prepare читает/проверяет локальные assets, не создаёт journal и не публикует их.

Check выполняется фиксированным Python worker с timeout 1–120 секунд (default30), самостоятельным watchdog и общей с case worker границей bounded output/schema/binding. Shell/модели/сеть не используются. CLI возвращает 0 только при passed; blocked/failed возвращаются как JSON с кодом 1. MCP caller проверяет status, а не успешность транспорта.

## Что проверяется

- ZIP до 128 MiB, до 5000 members и до 128 MiB суммарного распакованного содержимого. Никакой распаковки или импорта packaged code внутри hook.
- Один ожидаемый root, безопасные POSIX paths; отказ от traversal, symlinks, encrypted members, duplicate/case-colliding имён и непереносимых Windows имён.
- Strict manifest: version/commit/dirty/files, duplicate keys запрещены, hashes и состав каждого файла совпадают. Обязательные файлы/allowlist общие со сборщиком; .env, private projects и скрытые credential/runtime paths не допускаются политикой путей.
- Ровно один wheel и один sdist; четыре внешних asset в SHA256SUMS. External manifest/wheel/sdist побайтово совпадают с архивом; hashes проверяются. Поля checksums не могут выбирать произвольный внешний файл.
- Manifest соответствует request и содержит dirty=false. Изменённый manifest требует нового request; повреждённый архив или external asset блокируется и при повторе прежнего UUID.

Allowlist/required files вынесены в domain/release_policy.py. Bounded checker установлен вместе с Python-пакетом и доступен без scripts/ в cwd. Существующий scripts.release.verify использует тот же checked_archive перед распаковкой, затем отдельно выполняет прежние install/demo checks. Правила проверки путей не дублируются между hook и verifier.

## Границы pass, replay и доверия

Passed означает статическую целостность прочитанных bytes и заявленный в manifest dirty=false. Это не подпись автора, не проверка доступности commit в remote, не secret-content scan и не доказательство installability или качества стратегий. Self-consistent поддельный manifest не становится доверенным благодаря hash. Используйте доверенный builder/commit и отдельные CI/secrets/install проверки.

Release checks read-only и **stateless/live**: каждый вызов повторно читает/проверяет assets, старый pass не кешируется. Durable journal/recovery P3b относится к case triggers; `hook run` для release request намеренно не используется. Изменение файлов после проверки не разрешает публикацию; дальнейший release процесс отдельно должен связать публикуемые bytes с проверенным артефактом. Hook не даёт разрешения на tag/draft/publish.

Диагностика фиксированная, без raw архивных текстов/output worker. Повреждённые/недоступные inputs дают blocked/failed либо ошибку подготовки. Проверки ограничены bytes и wall time, но не являются общим CPU/memory/OS sandbox; prepare синхронный и process timeout относится к check. История/рабочие кейсы/БД не меняются.

## FastMCP и текущий этап

Read-only tools: `psa_prepare_release_hook(archive, operation_id)` и `psa_check_release_hook(request, archive, timeout_seconds)`. CLI/real-stdio parity, recheck после tampering/stale manifest, timeout и отсутствие выполнения packaged code проверяются на инертных синтетических архивах. Дополнительно выполнена реальная локальная clean-commit сборка и статический hook; точные hashes/commit в [отчёте](../reports/2026-11-15-r31-release-hooks.md).

Локальные явные механизмы P3a–P3d реализованы. Native host activation, полный lifecycle host adapters и проверка их capabilities относятся к P4. Общий этап R3.1, реальные R1/M8 и независимая оценка M6 этим не закрываются. Последовательный IDE/CLI путь остаётся доступным.
