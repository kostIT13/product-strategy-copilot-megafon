# Runbook: пересмотр после изменения источника

**Цель:** показать, что повторный импорт того же URI с изменённым содержимым сохраняет прежнюю версию, связывает событие с зависимыми claim/decision и требует человеческого review. Набор данных полностью синтетический.

## Подготовка

Запустить из корня репозитория в PowerShell. Идентификатор проекта в примере новый; для повторного прогона задайте другой.

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$projectId = 'revisit-demo-20261106'
$demoInput = Join-Path $env:TEMP 'psa-revisit-demo.csv'
Copy-Item evals/revisit-demo/source.csv $demoInput
python -m product_strategy_agent.cli init $projectId
python -m product_strategy_agent.cli source add $projectId $demoInput --title 'Synthetic revision fixture'
```

Скопировать `source_id`, напечатанный последней командой, в `$sourceId`. Исходная таблица содержит `renewed,10`, `eligible,20`, `other,1`.

## Создать зависимости

```powershell
$sourceId = 'S-ID-ИЗ-ВЫВОДА-КОМАНДЫ'
python -m product_strategy_agent.cli claim add $projectId --text 'В источнике указано renewed=10.' --type fact --source $sourceId --locator line:2 --quote 'renewed,10' --confidence medium --reasoning-note 'Учебная строка CSV.'
python -m product_strategy_agent.cli option add $projectId --name Keep --role status_quo --description 'Keep the current action after review.' --claim C-001
python -m product_strategy_agent.cli option add $projectId --name Stop --role stop --description 'Stop if evidence no longer supports the action.' --claim C-001
python -m product_strategy_agent.cli option add $projectId --name Test --role change --description 'Run a limited controlled test after review.' --claim C-001
python -m product_strategy_agent.cli decision add $projectId --option Keep --option-id O-001 --owner demo-owner --rationale 'The source claim remains supported.' --claim C-001 --revisit-when 'After reviewing the changed source'
```

## Изменить тот же источник и проверить зависимости

```powershell
Copy-Item evals/revisit-demo/changed-source.csv $demoInput -Force
python -m product_strategy_agent.cli source add $projectId $demoInput --title 'Synthetic revision fixture'
python -m product_strategy_agent.cli revisit list $projectId
```

Ожидается source revision event, архив в `projects/<project-id>/sources/history/<source_id>/`, а в отчёте — `C-001` и `D-001` со статусом `pending_review`. В таблице поменялось только `other`; цитата `renewed,10` сохранилась.

## Зафиксировать review

```powershell
python -m product_strategy_agent.cli revisit resolve $projectId SRC-REV-0001 --by 'Демо-владелец' --reason 'Проверены связанные вывод и решение; цитата и вывод не изменились' --reviewed-claim C-001 --reviewed-decision D-001
python -m product_strategy_agent.cli revisit list $projectId
python -m product_strategy_agent.cli verify $projectId
```

После review ожидается `pending_count: 0`; локатор/цитата проходят `verify`. Архивная версия и оба события остаются в проекте. Runbook — сценарий ручной приёмки, его прохождение отдельно фиксируется в журнале; этот документ сам по себе не доказывает, что команды уже выполнялись.
