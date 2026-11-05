# Агент продуктовой стратегии

Переносимый CLI и набор файловых артефактов для подготовки проверяемых продуктовых и коммуникационных стратегий. Текущий MVP развивается по пунктам в [едином плане](docs/solution_plans/plan-main.md).

## CLI

Требуется Python 3.11 или новее. Из корня репозитория установите пакет в editable-режиме и используйте команду `psa`:

```powershell
python -m pip install -e .
psa --help
psa init demo-retention
psa status demo-retention
psa next demo-retention
psa resume demo-retention
```

`init` создаёт папку `projects/<project-id>` с версионируемым `state.json`, шаблоном брифа и пустыми журналами. Исходные материалы в `projects/*/sources/` исключены из Git по умолчанию.

Пока состояние изменяется только при создании проекта. Команды `status`, `next` и `resume` читают сохранённое состояние; следующие этапы MVP добавят управляемые переходы и артефакты.

### Импорт источников

```powershell
psa source add demo-retention .\notes.md
psa source fetch demo-retention https://example.org/research
psa source list demo-retention
```

Поддерживаются текст, Markdown, CSV, JSON и HTML файлы, а также HTML/text веб-страницы до 10 MiB. Для каждой записи сохраняются URI или локальный путь, тип, время загрузки, locator, SHA-256 извлечённого текста и путь к локальной копии. Повторный импорт того же пути или URL обновляет запись. Веб-запрос выполняется только явной командой `source fetch`.

### Утверждения, пробелы и решения

```powershell
psa claim add demo-retention --type fact --text "..." --source S-0123456789AB --locator "paragraph:4" --quote "Точный текст выдержки" --confidence medium
psa gap add demo-retention --question "..." --why-it-matters "..." --method "..." --priority high
psa decision add demo-retention --option "Пилот на одном сегменте" --owner "Владелец решения" --claim C-001 --reject "Оставить как есть" --revisit-when "После 4 недель"
```

Утверждения имеют тип `fact`, `interpretation`, `hypothesis`, `forecast` или `synthetic`. Факт обязан ссылаться на известный источник и locator. Ссылки на источники, противоречащие и замещаемые утверждения, а также основания решения проверяются по реестрам. Все три журнала записываются добавлением новых строк.

### Проверка структуры и цитат

```powershell
psa validate demo-retention
psa verify demo-retention
```

`validate` проверяет версию состояния, основные артефакты, JSONL-синтаксис, уникальность ID и ссылки между утверждениями, источниками и решениями. `verify` пересчитывает SHA-256 сохранённых текстов и сверяет точные цитаты по locator вида `paragraph:4`, `p:4` или `line:4`. Неподдерживаемые locator отмечаются как предупреждения и не объявляются проверенными.

Для факта указывайте цитату вместе с каждым источником:

```powershell
psa claim add demo-retention --type fact --text "..." --source S-0123456789AB --locator "paragraph:4" --quote "Точный текст выдержки"
```


### Варианты и сборка результатов

Добавляйте варианты с ролями `status_quo` (оставить как есть), `stop` (закрыть) и `change` (изменить/расширить):

```powershell
psa option add demo-retention --name "Оставить как есть" --role status_quo --description "Сохранить текущий подход"
psa option add demo-retention --name "Закрыть направление" --role stop --description "Прекратить развитие и поддержать текущих пользователей"
psa option add demo-retention --name "Пилот для сегмента A" --role change --description "Проверить новое предложение на ограниченном сегменте" --benefits "Ниже риск" --costs "Команда пилота" --risks "Малый охват"
```

Свяжите решение с выбранным вариантом: `psa decision add ... --option-id O-003`. `psa validate` проверяет наличие минимум трёх вариантов с тремя обязательными ролями, если варианты уже начали записывать.

`psa render demo-retention` создаёт `03_evidence.md`, `04_options.md`, `decision.md`, `05_strategy.md` и `06_validation-plan.md`. Для продуктовой, коммуникационной стратегии и плана проверки команда создаёт исходные черновики в `drafts/`; повторный `render` читает их, но не меняет. Сгенерированные Markdown-файлы пересобираются при каждом запуске.
