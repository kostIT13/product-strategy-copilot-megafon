# P7b: параметры до реализации candidate

17.11.2026. Этот файл и [holdout.json](holdout.json) фиксируются отдельным коммитом до реализации candidate. Набор синтетический, составлен тем же разработчиком; это preimplementation test set, не слепой независимый benchmark. После просмотра результатов gold/пороги не менять; следующая настройка требует нового набора и отдельной записи.

Baseline — unchanged `literal_ignore_case_v1`. Candidate — только development experiment: literal-first, затем fallback по всем Unicode word tokens запроса в одном окне до 500 символов одной секции. Если literal hits уже есть, выдача сохраняется. Без морфологии, словаря синонимов, embeddings, сети, модели или нового runtime dependency. Production CLI/FastMCP остаются прежними.

Одинаковые 10 sources/16 queries, snapshot, k=3. Разметка включает word order, отделённые слова, actor ambiguity, отрицания, числа/единицы, PDF/XLSX scopes, regex punctuation, отсутствие ответа, межсекционную границу и недоверенный source text. Gold указывает релевантность свидетельства, не утверждает истинность позитивной гипотезы: отрицание может быть релевантным свидетельством. Текст с инструкцией только возвращается как quote; это не проверка поведения LLM при prompt injection.

Lifecycle fixture из того же JSON отдельно проверяется на temporary file case через настоящий store: повторный импорт ревизии, отзыв второго источника, current-token находится, obsolete/withdrawn tokens отсутствуют для обоих kernels. Никакой persistent case или пользовательское согласование не создаётся. Локальные fake actor/UUID относятся только к синтетическому тесту технического writer, не реальному human gate.

Engineering criteria, зафиксированные до запуска:

- Recall выше baseline минимум на 0.10, micro precision не ниже baseline; отсутствие регрессий для queries с baseline hits (сохраняются references/quotes). Отдельно показать все категории и ошибки.
- Все hits с точными quote/hash/locator; без cross-scope или stale/withdrawn references; existing file-search negative tests проходят.
- Локальный budget: 0 external/model calls, 0 новых runtime dependencies; среднее время candidate evaluation loop не более 0.10 s на этом маленьком готовом snapshot, 5 повторов. Это измеряемый критерий, не hard timeout или SLA. Memory/file load/human time не измеряются и остаются null. Нет разрешения внешних вызовов/расходов.
- Неудача любого критерия исключает candidate из дальнейшего adoption в этом виде. Даже успех не включает метод в production: runtime/resource/integrity и независимая оценка остаются отдельными шагами.

P7a corpus остаётся development regression corpus, не добавляется в holdout metrics. Сравнение должно записать baseline/candidate версии, hash fixture и исходников, commit/dirty state, Python/OS, scope timing, unknown cost и отсутствие независимого review. Historical reports не переписывать.
