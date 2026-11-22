"use strict";

(() => {
  const dialog = $("#capabilities");
  const nav = $("#capability-nav");
  const panel = $("#capability-content");
  const rubles = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 });

  function card(title, description) {
    const section = element("div", "demo-step");
    section.append(element("h3", "", title), element("p", "", description));
    return section;
  }

  function output() { return element("div", "demo-output"); }

  function interview() {
    const section = card("Интервью с модельным респондентом",
      "Вымышленная роль: организатор семейной группы. Ответы подготовлены для демонстрации.");
    const exchanges = [
      ["Как вы узнали, что у близкого закончился интернет?", "Он написал мне в семейный чат уже после того, как связь стала прерываться."],
      ["Что помогло бы вам среагировать раньше?", "Предупреждение с понятным следующим действием. Я бы хотел видеть, хватает ли общего остатка."],
      ["Что помешало бы вам воспользоваться подсказкой?", "Неясно, кому выделится интернет и нужно ли подтверждать действие."],
    ];
    const transcript = output();
    const result = output();
    const next = button("Задать первый вопрос", () => {
      const [question, answer] = exchanges[index++];
      transcript.append(element("p", "", `Агент: ${question}`), element("p", "", `Респондент: ${answer}`));
      next.textContent = index === exchanges.length ? "Интервью завершено" : "Задать следующий вопрос";
      next.disabled = index === exchanges.length;
      analyse.disabled = !next.disabled;
      if (next.disabled) analyse.focus();
    }, "primary");
    let index = 0;
    const analyse = button("Выделить гипотезу", () => {
      result.replaceChildren(
        element("strong", "", "Синтетика · только для формирования гипотез"),
        element("p", "", "Гипотеза: явный получатель и статус операции могут снизить число ошибочных действий."),
        element("p", "", "Проверка: предложить одинаковую задачу на двух прототипах. Сравнить правильность выбора получателя и понимание результата."),
        element("p", "", "Спрос и распространённость проблемы остаются неизвестными."),
      );
    });
    analyse.disabled = true;
    const actions = element("div", "actions");
    actions.append(next, analyse);
    section.append(transcript, actions, result);
    return section;
  }

  function ux() {
    const section = card("Сравнение двух экранов",
      "Учебные макеты одного шага. Задача — проверить, можно ли безопасно помочь близкому со связью.");
    const screens = element("div", "mock-pair");
    for (const [title, text, action] of [
      ["Экран A · общий остаток", "Семейный пакет: 4 ГБ. Сведения об остатке участника доступны с его согласия.", "Выделить интернет"],
      ["Экран B · помощь участнику", "Получатель: Мария. Выделение доступно на совместимом тарифе при свободном остатке.", "Проверить условия выделения"],
    ]) {
      const screen = element("div", "mock-screen");
      screen.append(element("strong", "", title), element("p", "", text), element("span", "mock-action", action));
      screens.append(screen);
    }
    const result = output();
    section.append(screens, button("Показать UX-разбор", () => {
      screens.classList.add("marked");
      result.replaceChildren(
        element("p", "", "Привязка: подпись выделенного действия в нижней части обоих экранов."),
        element("p", "", "Наблюдение: экран A предлагает выделить интернет сразу. На экране B указаны получатель и предварительная проверка условий."),
        element("p", "", "Гипотеза: пояснение снизит число ошибок на шаге подтверждения. Проверка: сравнить выполнение задачи без подсказок."),
      );
    }, "primary"), result);
    return section;
  }

  function forecast() {
    const section = card("Пересчёт валовой прибыли по CSV", "Локальный расчёт для исходного учебного варианта O-003. Период — плановый год, единицы — рубли.");
    const row = "gross_profit_rub,RUB,planning_year,279000000,285000000,3";
    const [baseline, goal] = row.split(",").slice(3, 5).map(Number);
    const rate = 500;
    const result = output();
    const examples = [
      { name: "Основной", months: [0, 200, 350, 650], costs: [0, 120000, 100000, 130000] },
      { name: "Менее благоприятный", months: [0, 40, 60, 100], costs: [0, 150000, 140000, 160000] },
    ];
    section.append(element("pre", "demo-note", `baseline.csv · paragraph:2\n${row}\nСтавка из учебного брифа: ${rate} ₽ за дополнительный оплаченный номеро-месяц.`),
      button("Пересчитать два сценария", () => {
        result.replaceChildren(element("p", "", "Прибыль = база + оплаченные номеро-месяцы × ставка − прямые расходы."));
        for (const { name, months, costs } of examples) {
          const sum = (items) => items.reduce((total, value) => total + value, 0);
          const paidMonths = sum(months);
          const expenses = sum(costs);
          const margin = baseline + paidMonths * rate - expenses;
          result.append(element("p", "", `${name}: ${paidMonths} номеро-месяцев, расходы ${rubles.format(expenses)}. Прибыль ${rubles.format(margin)}, разрыв до цели ${rubles.format(goal - margin)}.`));
        }
        result.append(element("p", "muted", "Допущения описывают учебные сценарии. Реальный эффект предстоит измерить."));
      }, "primary"), result);
    return section;
  }

  function fastMcp() {
    const section = card("Проверка цитат через FastMCP",
      "Имитация вызова из IDE. В настоящем проекте psa_verify сверяет цитаты и целостность сохранённых источников.");
    const result = output();
    section.append(element("p", "demo-note", "Запрос: проверь цитаты и покажи, к каким источникам они привязаны."),
      element("code", "demo-note", `psa_verify({ "project_id": "${scenario.id}" })`),
      button("Показать ответ инструмента", () => {
        result.replaceChildren(
          element("strong", "", "Сценарный ответ · проверка пройдена"),
          element("p", "", "9 цитат в трёх материалах: C-001–C-007 (PDF), C-008 (CSV), C-009 (выдержка Pixel)."),
          element("p", "", "Каждая выдержка связана с локатором в источнике. Смысл вывода и надёжность источника оцениваются отдельно."),
        );
      }, "primary"), result);
    return section;
  }

  function promises() {
    const section = card("Проверка обещания по возможностям продукта",
      "Учебная карточка O-003. Сверяем текст уведомления с возможностью и условиями из C-004 и C-006.");
    const draft = element("p", "demo-note", "Черновик: «Мы автоматически восстановим связь у вашего близкого».");
    const result = output();
    const narrow = button("Уточнить обещание", () => {
      draft.textContent = "Уточнённый текст: «Проверьте, можно ли вручную выделить интернет из общего остатка». Действие зависит от согласия, прав, тарифа и свободного объёма.";
      result.replaceChildren(
        element("strong", "", "Обещание ограничено доступным действием"),
        element("p", "", "Автоматическое восстановление связи исключено. Перед согласованием человек проверяет текст и условия."),
      );
      narrow.disabled = true;
      check.disabled = true;
    });
    narrow.disabled = true;
    const check = button("Проверить обещание", () => {
      result.replaceChildren(
        element("strong", "", "Сценарный ответ · обнаружено несоответствие"),
        element("p", "", "Бриф подтверждает ручное выделение свободного объёма. Автоматическое восстановление связи не подтверждено."),
      );
      narrow.disabled = false;
    }, "primary");
    const actions = element("div", "actions");
    actions.append(check, narrow);
    section.append(draft, element("code", "demo-note", `psa promise check ${scenario.id}`), actions, result);
    return section;
  }

  function preflight() {
    const section = card("Локальный хук перед согласованием",
      "Учебный снимок этапа validation. В первом варианте плана пропущено окно наблюдения.");
    const plan = element("p", "demo-note", "Метрика: доля подходящих номеров с ограничением. Окно наблюдения: не указано.");
    const result = output();
    let windowAdded = false;
    const repair = button("Добавить окно и перепроверить", () => {
      windowAdded = true;
      plan.textContent = "Метрика: доля подходящих номеров с ограничением. Окно наблюдения: семь дней.";
      showCheck();
    });
    repair.disabled = true;

    function showCheck() {
      result.replaceChildren(
        element("strong", "", windowAdded ? "Сценарный ответ · passed" : "Сценарный ответ · blocked"),
        element("p", "", "Структура и цитаты: пройдены."),
        element("p", "", windowAdded ? "Требования этапа и материалы для смысловой оценки: пройдены." :
          "Требования этапа и материалы для смысловой оценки: в плане отсутствует окно."),
        element("p", "muted", "Переход согласует человек отдельным действием."),
      );
      repair.disabled = windowAdded;
    }

    const actions = element("div", "actions");
    actions.append(button("Запустить проверку", showCheck, "primary"), repair);
    section.append(plan, element("code", "demo-note", "before_validation_gate · psa hook check"), actions, result);
    return section;
  }

  function impact() {
    const section = card("Зависимости решения после исправления",
      "Учебная копия O-003. В ревизии SRC-REV-0001 ставка из C-005 уточнена с 500 до 400 ₽ за оплаченный номеро-месяц.");
    const result = output();
    section.append(element("pre", "demo-note", `psa claim impact ${scenario.id}\npsa decision summary ${scenario.id}`),
      button("Показать затронутые материалы", () => {
        result.replaceChildren(
          element("strong", "", "Сценарный ответ · требуется пересмотр"),
          element("p", "", "C-005: прежняя ставка хранится в истории. Для нового расчёта используется исправленная запись."),
          element("p", "", "Затронуты сравнение O-003, прогноз прибыли и обоснование D-001. Прогноз нужно пересчитать."),
          element("p", "", "Ответственный: руководитель направления. Следующий шаг: оценить новый расчёт и подтвердить прежний выбор или выбрать альтернативу."),
        );
      }, "primary"), result);
    return section;
  }

  const examples = [
    ["Модельное интервью", interview], ["UX-разбор", ux],
    ["Расчёт по CSV", forecast], ["FastMCP", fastMcp],
    ["Обещания продукта", promises], ["Хук проверки", preflight], ["Влияние исправления", impact],
  ];
  const controls = examples.map(([label], index) => button(label, () => select(index)));
  nav.append(...controls);

  function select(index) {
    controls.forEach((control, position) => control.setAttribute("aria-pressed", String(position === index)));
    panel.replaceChildren(examples[index][1]());
  }

  $("#open-capabilities").onclick = () => { select(0); dialog.showModal(); };
})();
