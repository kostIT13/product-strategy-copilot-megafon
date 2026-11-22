"use strict";

const key = "psa-workspace-demo-1";
const $ = (selector) => document.querySelector(selector);
const startPrompt = "Какое небольшое изменение стоит проверить первым, чтобы клиенты вымышленного оператора успевали отреагировать на риск перебоя связи? Покажи бриф и остановись перед согласованием.";
const resumePrompt = `Возобнови учебный кейс ${scenario.id}. Покажи сохранённый этап, последнее решение и следующий шаг.`;
const fresh = () => ({ stage: 0, option: null, chat: 1, started: false, paused: false, awaitingResume: false,
  revision: 0, events: [], messages: [] });

function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(key));
    if (Number.isInteger(saved?.stage) && scenario.stages[saved.stage] &&
        Array.isArray(saved.events) && Array.isArray(saved.messages)) {
      // The original demo opened the case automatically.
      return { started: true, awaitingResume: false, ...saved };
    }
  } catch { /* The demo also works without browser storage. */ }
  return fresh();
}

let state = load();
let tab = "sources";
const active = () => scenario.stages[state.stage];
const choice = () => scenario.options.find(({ id }) => id === state.option);
const decisionId = () => `D-00${state.revision + 1}`;

function fillMessage(text) {
  const input = $("#message");
  input.value = text;
  input.focus();
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function button(label, action, className) {
  const node = element("button", className, label);
  node.type = "button";
  node.onclick = action;
  return node;
}

function log(type, command) { state.events.push({ type, command }); }
function say(text, role = "agent") { state.messages.push({ role, text }); }

function update(scroll = true) {
  try { localStorage.setItem(key, JSON.stringify(state)); } catch { /* In-memory fallback. */ }
  render();
  if (scroll) window.scrollTo(0, document.documentElement.scrollHeight);
}

function report(completed, sources, unknown, next) {
  return `Сделано: ${completed}\nИсточники: ${sources}\nНеизвестно: ${unknown}\nПотрачено: 0 ₽ · время не замерялось\nСледующий шаг: ${next}`;
}

function content(file) {
  const option = choice();
  const hypothesis = "Эффект, стоимость внедрения и размер подходящей группы предстоит проверить.";
  const comparison = scenario.options.map((item) => {
    const [benefit, cost, revisitCondition] = scenario.tradeoffs[item.id];
    return `${item.id} · ${item.name} · ${item.role}\n${item.product}\nПольза: ${benefit}\nИздержки и риски: ${cost}\nСильное возражение: ${item.objection}\nУсловие пересмотра: ${revisitCondition}`;
  }).join("\n\n");
  const docs = {
    brief: "Решение: какое небольшое изменение проверить первым, чтобы вымышленный оператор мог помочь со связью.\n\nВладелец: руководитель направления. В конце Q1 решаем, есть ли основания для пилота. В конце Q2 пересматриваем масштаб. Согласие, тариф и права доступа ограничивают доступные действия.",
    plan: "1. Сопоставить причины ограничения: исчерпание пакета, неоплата, недоступность устройства.\n2. Проверить, кто может отреагировать и выполняется ли действие.\n3. Сравнить ранний сигнал с текущим обслуживанием и альтернативами.\n\nДостаточность: понятны причина, достижимая аудитория и измеримый результат.",
    evidence: scenario.sources.map((source) => `${source.name}\n${source.excerpt}`).join("\n\n") +
      (state.revision ? "\n\nSRC-REV-0001 · учебное дополнение предлагает 400 ₽ вместо 500 ₽ за дополнительный номеро-месяц. Старая ставка сохранена в истории." : ""),
    options: comparison,
    product: option ? `${option.id} · ${option.name}\n\n${option.product}\n\n${hypothesis}` +
      (option.id === "O-003" && !state.revision ? "\n\nПрогноз (учебный): 279,25 / 278,65 млн ₽ при цели 285 млн ₽." : "") : "",
    communication: option ? `${option.id}\n\n${option.communication}\n\nУказываем только доступное действие. Ограничения тарифа и полномочий показываем до операции.` : "",
    validation: option ? `Метрика: ${option.metric}\n\nБаза неизвестна. Аналитик собирает её на подходящей когорте и фиксирует знаменатель и исключения. Сравнение с обычным обслуживанием. Отдельно учитываются ошибки, нарушения прав и неизвестные исходы. Остановка при подтверждённом нарушении прав или неправильном исполнении.` : "",
    critic: option ? `Критический разбор · ${option.id}\n\nВозражение: ${option.objection}\n\nСузить обещания до подтверждённых действий. Перед запуском проверить сопоставимость базы, качество событий и границы применимости. ${hypothesis}\n\nРазбор подготовлен для учебного сценария. Смысловую оценку подтверждает человек.` : "",
    decision: option ? `${decisionId()} · ${option.id}\n\n${option.product}\n\nУсловие пересмотра: новые сведения о причинах перебоев, правах доступа или экономике. Выбор относится к учебному сценарию.` : "Решение ещё не принято.",
  };
  return docs[file];
}

function preview(title, text) {
  $("#preview-title").textContent = title;
  $("#preview-body").textContent = text;
  $("#preview").showModal();
}

function openFile(file) {
  preview(scenario.files[file], content(file));
}

function visibleFiles() {
  const files = ["brief", "plan", "evidence"];
  if (state.stage >= 4) files.push("options");
  if (state.option) files.push("product", "communication", "decision");
  if (state.stage >= 6) files.push("validation", "critic");
  return files;
}

function renderRail() {
  $("#progress").textContent = `${state.stage} / 7`;
  $("#stages").replaceChildren(...scenario.stages.map((stage, index) => {
    const status = index === state.stage ? "current" : index < state.stage ? "done" : "";
    const row = element("div", `stage-row ${status}`.trim());
    if (status === "current") row.setAttribute("aria-current", "step");
    row.append(element("span", "step-mark", status === "done" ? "✓" : String(index + 1)), stage.name);
    return row;
  }));
  $("#files").replaceChildren(...visibleFiles().map((file) => {
    const row = button(scenario.files[file], () => openFile(file), "file-row");
    row.prepend(element("span", "", "▧"));
    return row;
  }));
}

function renderConversation() {
  $("#chat-index").textContent = `Чат ${String(state.chat).padStart(2, "0")}`;
  $("#conversation").replaceChildren(...state.messages.map(({ role, text }) => {
    const row = element("div", `message ${role}`);
    const body = element("div");
    body.append(element("strong", "", role === "user" ? "Вы" : "PSA · агент"), element("p", "", text));
    row.append(element("span", "avatar", role === "user" ? "В" : "✳"), body);
    return row;
  }));
}

function renderInspector() {
  document.querySelectorAll("[data-tab]").forEach((item) => item.setAttribute("aria-pressed", String(item.dataset.tab === tab)));
  const panel = $("#inspector-content");
  if (tab === "sources") {
    panel.replaceChildren(...scenario.sources.map(({ id, name, format, summary, excerpt }) => {
      const node = button("", () => preview(name, excerpt), "source-card");
      node.append(element("span", "file-meta", `${id} · ${format}`), element("strong", "", name), element("small", "", summary));
      return node;
    }));
    return;
  }
  if (tab === "files") {
    panel.replaceChildren(...visibleFiles().map((file) => button(scenario.files[file], () => openFile(file), "source-card")));
    return;
  }
  panel.replaceChildren(...state.events.slice().reverse().map(({ type, command }) => {
    const row = element("div", "journal-entry");
    row.append(element("strong", "", type), element("code", "", command));
    return row;
  }));
  if (!state.events.length) panel.append(element("p", "muted", "После первого действия здесь появятся записи учебного прогона."));
}

function inputList(values, type, className, onChange) {
  const list = element("div", className);
  for (const [value, description] of values) {
    const label = element("label", type === "radio" ? "option" : "criterion");
    const input = element("input");
    input.type = type;
    input.name = type === "radio" ? "selected-option" : "review-check";
    input.value = value;
    input.onchange = () => onChange(list);
    label.append(input, element("span", "", description));
    list.append(label);
  }
  return list;
}

function renderStage() {
  const stage = active();
  const panel = $("#stage-action");
  const actions = element("div", "actions");
  if (!state.started || state.awaitingResume) {
    const newCase = !state.started;
    panel.replaceChildren(
      element("div", "action-label", newCase ? "Начало" : "Новый чат"),
      element("h2", "", newCase ? "Отправьте запрос агенту" : "Возобновите сохранённый кейс"),
      element("p", "", newCase ? "Введите продуктовый вопрос или воспользуйтесь примером." :
        "История предыдущего чата закрыта. Попросите агента прочитать сохранённый этап и решение."),
      actions,
    );
    actions.append(button(newCase ? "Вставить пример запроса" : "Вставить запрос на возобновление",
      () => fillMessage(newCase ? startPrompt : resumePrompt), "primary"));
    return;
  }
  panel.replaceChildren(element("div", "action-label", state.paused ? "Пауза" : stage.id),
    element("h2", "", state.paused ? "Точка продолжения сохранена" : stage.title),
    element("p", "", state.paused ? `Текущий этап: ${stage.name}.` : stage.detail));
  if (state.paused) {
    actions.append(button("Новый чат", newChat, "primary"), button("Продолжить здесь", resume));
  } else if (stage.id === "completed") {
    actions.append(button("Открыть решение", () => openFile("decision"), "primary"));
    if (!state.revision) actions.append(button("Показать новые данные", revisit));
  } else {
    const approval = button("Согласовать этап", () => approve(), "primary");
    if (stage.id === "options") {
      approval.textContent = "Подтвердить выбор";
      approval.disabled = true;
      panel.append(inputList(scenario.options.map(({ id, name }) => [id, `${id} · ${name}`]), "radio", "option-list", (list) => {
        const selected = list.querySelector(":checked").value;
        approval.disabled = false;
        approval.onclick = () => approve(selected);
      }));
    }
    if (["strategy", "validation"].includes(stage.id)) {
      approval.disabled = true;
      panel.append(inputList(scenario.criteria.map((criterion, index) => [String(index), criterion]), "checkbox", "criteria", (list) => {
        approval.disabled = list.querySelectorAll(":checked").length !== scenario.criteria.length;
      }));
      actions.append(button(stage.id === "strategy" ? "Коммуникация" : "Критический разбор",
        () => openFile(stage.id === "strategy" ? "communication" : "critic")));
    }
    actions.prepend(button("Открыть материал", () => openFile(stage.file)), approval);
    actions.append(button("Пауза", pause));
  }
  panel.append(actions);
}

function render() {
  $("#new-chat").disabled = !state.started || state.awaitingResume;
  renderRail();
  renderConversation();
  renderStage();
  renderInspector();
}

function approve(selected) {
  if (!state.started || state.paused || state.stage >= 7) return;
  const { id, name } = active();
  if (id === "options") state.option = selected;
  say(selected ? `Утверждаю сравнение и выбираю ${selected}.` : `Подтверждаю этап «${name}».`, "user");
  if (["strategy", "validation"].includes(id)) log("Смысловая оценка · 6 из 6", `psa review record ${scenario.id} --scope ${id}`);
  log("Переход по согласию человека", `psa gate approve ${scenario.id} --stage ${id}`);
  if (selected) log(`Выбор человека · ${selected}`, `psa decision add ${scenario.id} --option-id ${selected}`);
  state.stage += 1;
  if (state.stage === 4) log("Сравнение вариантов", `psa option check ${scenario.id}`);
  if ([5, 6].includes(state.stage)) {
    log("Подготовка смысловой оценки", `psa review prepare ${scenario.id} --scope ${active().id}`);
    if (state.stage === 6) log("Критический разбор", `psa critic-pack ${scenario.id}`);
  }
  if (state.stage === 7) log("Итоговая сводка", `psa decision summary ${scenario.id}`);
  say(report(`${name} согласовано.`, "PDF-бриф, CSV и выдержка Pixel", "фактический охват и эффект", active().title));
  update();
  $("#stage-action h2").setAttribute("tabindex", "-1");
  $("#stage-action h2").focus({ preventScroll: true });
}

function pause() {
  if (!state.started || state.paused) return;
  state.paused = true;
  log("Сохранена точка продолжения", `psa status ${scenario.id}`);
  const savedChoice = state.option ? ` Сохранён выбор ${decisionId()} / ${state.option}.` : "";
  say(`Сохранил этап «${active().name}».${savedChoice} Откройте новый чат и отправьте запрос на возобновление.`);
  update();
}

function newChat() {
  if (!state.started || state.awaitingResume) return;
  state.chat += 1;
  state.messages = [];
  state.paused = true;
  state.awaitingResume = true;
  $("#message").value = "";
  update(false);
  window.scrollTo(0, 0);
}

function resume() {
  if (!state.paused) {
    say(`Кейс уже открыт на этапе «${active().name}».`);
    return update();
  }
  state.paused = false;
  state.awaitingResume = false;
  log("Чтение сохранённого состояния", `psa resume ${scenario.id}`);
  if (state.option) log("Чтение сохранённого решения", `psa decision summary ${scenario.id}`);
  const savedChoice = state.option ? `\nСохранённый выбор: ${decisionId()} / ${state.option} · ${choice().name} (decision.md).` : "";
  say(`Восстановил кейс ${scenario.id}.\nЭтап: ${active().name} (${active().id}).${savedChoice}\nСледующий шаг: ${active().title}.\nПрежние согласования и импорт сохранились в журнале.`);
  update();
}

function revisit() {
  if (state.stage !== 7 || state.revision) return;
  log("Новые данные · SRC-REV-0001", `psa revisit context ${scenario.id} SRC-REV-0001`);
  preview("Пересмотр · SRC-REV-0001", "Учебное дополнение предлагает 400 ₽ за дополнительный оплаченный месяц вместо 500 ₽. Затронуты C-005, прогноз и сохранённое решение.");
  const reopen = button("Разрешить возврат к вариантам", () => {
    $("#preview").close();
    state.revision += 1;
    state.stage = 4;
    state.option = null;
    log("Возврат по согласию человека", `psa workflow reopen ${scenario.id} --stage options`);
    say("Вернулся к альтернативам. Прежний выбор и согласования видны в журнале. Сравните варианты и подтвердите новый выбор.");
    update();
  }, "primary");
  const actions = element("div", "actions");
  actions.append(reopen);
  $("#preview-body").append(actions);
  update(false);
}

$("#composer").onsubmit = (event) => {
  event.preventDefault();
  const input = $("#message");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  say(text, "user");
  if (!state.started) {
    state.started = true;
    log("Получен исходный запрос", `psa status ${scenario.id}`);
    log("Подготовка контекста", `psa context ${scenario.id}`);
    say(report("Открыл бриф учебного кейса и выделил вопрос решения.",
      "01_brief.md, пример брифа PDF", "причины перебоев, подходящий охват и эффект",
      "Проверьте бриф и согласуйте постановку."));
    return update();
  }
  if (/^(?:продолж(?:и|ить|ай)|возобнов(?:и|ить|ляй))(?:$|[.!,\s])/iu.test(text)) return resume();
  if (state.awaitingResume) {
    say("Попросите возобновить кейс, чтобы я прочитал сохранённый этап и решение.");
    return update();
  }
  if (/^(стоп|пауза|остановись)(?:$|[.!,:\s])/iu.test(text)) {
    if (!state.paused) return pause();
    say("Кейс уже на паузе. Точка продолжения сохранена.");
    return update();
  }
  if (/источник|цитат/iu.test(text)) {
    say("Справа доступны PDF-бриф, производная CSV-таблица и выдержка Pixel. Откройте карточку, чтобы увидеть цитаты и привязки.");
    tab = "sources";
    $("#inspector").classList.add("open");
  } else if (/вариант|альтернатив/iu.test(text) && state.stage >= 4) {
    say("Открыл сравнение. В нём есть статус-кво, закрытие и два варианта изменения.");
    openFile("options");
  } else if (/решени/iu.test(text) && state.option) {
    say(`Сохранённый выбор: ${state.option}. В решении указано условие пересмотра.`);
    openFile("decision");
  } else if (/статус|этап|дальше/iu.test(text)) {
    say(`Текущий этап: ${active().name}. ${state.paused ? "Работа на паузе." : active().title + "."}`);
  } else {
    say("В учебном чате можно попросить показать источники, статус, поставить работу на паузу или продолжить. Выбор и согласования доступны в карточке этапа.");
  }
  update();
};

$("#new-chat").onclick = newChat;
$("#research-toggle").onclick = () => $("#inspector").classList.toggle("open");
$("#close-inspector").onclick = () => $("#inspector").classList.remove("open");
$("#reset").onclick = () => { $("#reset-dialog").returnValue = ""; $("#reset-dialog").showModal(); };
$("#reset-dialog").onclose = () => {
  if ($("#reset-dialog").returnValue !== "reset") return;
  state = fresh();
  tab = "sources";
  update(false);
  window.scrollTo(0, 0);
};
document.querySelectorAll("[data-tab]").forEach((item) => item.onclick = () => { tab = item.dataset.tab; renderInspector(); });
render();
