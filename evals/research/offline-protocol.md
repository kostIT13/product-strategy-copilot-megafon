# P7d: fixed offline research scenario

Это technical smoke на собственной синтетике, не продуктовый кейс или измерение агентного эффекта. Сценарий фиксируется до runner: один временный case, две ревизии одного TXT, один synthetic claim, два минимальных authored coverage paragraphs и один research-plan DRAFT. Никаких approvals/решений/семантических reviews, persistent case или реального fetch.

Проверяемые условия:

1. Fixed test scenario выбирает известные IDs из registry; registry authorization/activation остаются false. Public fetch только описывается, не вызывается; локальная копия — заранее разрешённый в test сценарии fallback, не результат автоматической проверки permissions.
2. Stage context прочитан; он не доказывает loading в IDE/качество методики. Поиск использует настоящий file store/service. Новая ревизия меняет hash, прежний marker исчезает из current hits; missing query возвращает empty без вывода об отсутствии явления.
3. Quote/locator/hash из current hit записываются штатным synthetic claim writer. Render/validate/verify/coverage проходят, coverage непустой. Research artifact сохраняется как draft; exact UUID replay ничего не переписывает и не становится approval.
4. Text с source instruction только находится как недоверенная quote. Case status/stages/approvals/decision log не меняются вследствие такого чтения. Это не LLM injection eval.
5. Invalid request и corrupt captured bytes отклоняются без записей от read services. Повреждение/restore выполняются только на собственной временной fixture для negative check; такого режима нет для пользовательского case. После restore исходные hashes и verification восстановлены.
6. Явный технический withdrawal на temporary fixture исключает source из current search и делает coverage ссылающегося claim невалидным. Claim bytes/history сохранены; человеческий выбор не затронут.
7. Guard запрещает DNS/socket requests; модель не используется. Все case writes находятся в собственном TemporaryDirectory. Human gates/decision log сравниваются с initial state. Failure runner даёт nonzero exit, не green partial report.

Вывод содержит только fixture hashes, выбранные tool IDs/versions и фиксированные pass checks, а не role/source texts, private paths или real telemetry. Timing охватывает весь synthetic run и cleanup, но не доказывает SLA; provider/human cost неизвестны/null. Набор и code известны автору, независимого reviewer нет. Польза tools по сравнению с manual/sequential agent и смысловая корректность recommendations остаются открытыми criteria P7/P8, не выводятся из pass этого smoke.
