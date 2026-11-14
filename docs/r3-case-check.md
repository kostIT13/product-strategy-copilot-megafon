# R3: сквозная проверка разрешённого кейса

Цель — проверить читаемый результат ТЗ на конкретном разрешённом материале. Это не очередной unit fixture, не независимая оценка R5 и не автоматическое закрытие R1/M6/M8. Протокол подготовлен; новый прогон не считается выполненным до выбора кейса и фиксации результатов.

## Входы и сохранение истории

Нужны project ID/путь существующего кейса либо описание нового: продукт, вопрос решения, аудитория, ограничения, владелец выбора и разрешённые источники. Не создавать новый кейс только ради разработки кода. Для нового кейса `psa init` выполняется после определения задачи; для существующего сначала status/resume/context. Из другого каталога передать --projects-dir и --instructions-root для context. Открытые инструкции/skills/knowledge читать по context; ошибку загрузки не выдавать за успех.

Перед изменениями зафиксировать Git revision runtime, host/model (если известны), источник/разрешение материалов, ID/путь, время и hashes входов. Outputs с персональными данными/секретами и рабочий кейс не коммитить. Подробные записи хранить в разрешённом месте; в reports/ — безопасные результаты и ограничения. Для legacy сначала `psa policy show`: обновление runtime не мигрирует case policy и не делает старое completed согласованием новых требований.

## Read-only диагностика

Ниже CASE — выбранный ID; для внешнего каталога добавить `--projects-dir PATH` к командам.

```powershell
psa status CASE
psa resume CASE
psa context CASE
psa policy show CASE
psa validate CASE
psa verify CASE
psa coverage CASE
psa strategy check CASE
psa validation check CASE
psa validation numbers CASE
psa validation calculations CASE
psa strategy numeric-inventory CASE
psa review prepare CASE --scope strategy
psa review prepare CASE --scope validation
```

Проверять не только exit code, но и packet: review prepare с exit 0 может содержать blocking_issues; numeric inventory с exit 0 оставляет tokens unassessed. Not_applicable не подтверждает отсутствие вычислений. Validate/verify/coverage могут пройти на legacy кейсе с неполным measurement/strategy contract. При pending workflow сначала явно восстановить точную сохранённую операцию штатным pending/recover; не обходить guard ручной правкой state.

## Содержательная проверка

| Критерий | Что показать | Что не считать подтверждением |
|---|---|---|
| Вопрос и исследование | Brief, вопросы, способные изменить решение, выбранные методы/knowledge с версиями | Наличие файлов или выдуманное чтение источника |
| Основания | Прочитанные материалы, current claims/цитаты/locators, противоречия и неизвестные | Успешный поиск цитаты как доказательство всей рекомендации |
| Альтернативы | Разные status_quo/stop/change, издержки, сильные возражения и условия пересмотра | Три названия одного решения |
| Человеческий выбор | Явная инструкция и structured decision с основаниями | Выбор основного агента/critic вместо человека |
| Стратегии | Восемь разделов product/communication, связь с выбором и допустимость обещаний | Только matching заголовки/claim markers |
| Числа и план измерения | Metric/unit/population/period, baseline либо честный unknown с планом получения, denominator, comparison/window/guardrails/owner | Digit inventory/arithmetic_match как semantic approval или наблюдаемый эффект |
| Review и продолжение | Текущие semantic assessments и отдельные gates, ошибки, сохранённый следующий шаг | Старый completed/UUID replay как новое согласование; отсутствие IDE-проверки как passed |

Для поддержанных reported baseline/расчётов использовать соответствующие contracts; числа вне их области оценить по исходному документу и материалу. Unknown нельзя заменять выдуманным baseline, сроком или размером эффекта. Совпадение context labels не доказывает сопоставимость популяции/периода. Synthetic/open/own материалы маркируются явно; synthetic результат не является рыночным доказательством.

## Исправления и согласования

Изменять authored drafts штатным авторским путём, реестры — командами; generated Markdown — render. Исправления/отзыв claims/sources и policy enablement выполняются отдельно с attribution и явной инструкцией человека. Не переписывать исходную историю и не мигрировать legacy кейсы автоматически ради зелёного отчёта. После существенных изменений заново проверить freshness и подготовить review.

Gates, decision add и semantic review record требуют явного указания человека по действующим правилам. Показать результат, текущие blockers и ожидаемый выбор; не записывать своё имя, пример checklist со всеми true или согласие critic вместо ответов человека. Checks-файл для CLI review готовить до prepare либо вне каталога кейса, чтобы не изменить reviewed snapshot. Эксперименты/публикации требуют собственных разрешений; functional check их не выдаёт.

## Запись результата и переход к R3.1

Для каждого критерия записать passed/blocked/not_verified, конкретный артефакт/hash, фактическую команду/exit/packet issues и оценку человека там, где она требуется. Отдельно указать изменения, runtime revision, host/model, время/стоимость/помощь человека и неизмеренные величины. Невыполненную проверку не считать ошибкой программы или успешной приёмкой. Без текущего человеческого review и существенного выбора результат R3 не закрывать.

После завершения R3 начинается R3.1 — субагенты и хуки по [основному плану](solution_plans/plan-main.md). Ранее отложенные live IDE/M6/M8 остаются отдельными открытыми проверками.
