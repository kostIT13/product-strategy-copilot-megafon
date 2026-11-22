"use strict";

const advancedCapabilities = ({ card, output }) => {
  function choiceList(label, values) {
    const wrapper = element("label", "demo-choice", label);
    const select = element("select");
    for (const name of values) select.append(element("option", "", name));
    wrapper.append(select);
    return { wrapper, select };
  }

  function search() {
    const section = card("Поиск в сохранённых материалах",
      "Браузерный поиск по трём учебным выдержкам. В проекте PSA ищет по текущим сохранённым версиям источников.");
    const form = element("form", "demo-query");
    const label = element("label", "", "Фраза");
    const input = element("input");
    input.value = "валовая прибыль";
    input.maxLength = 128;
    label.append(input);
    const submit = element("button", "primary", "Найти в источниках");
    const result = output();
    form.append(label, submit);
    form.onsubmit = (event) => {
      event.preventDefault();
      const query = input.value.trim();
      result.replaceChildren();
      if (!query) {
        result.append(element("p", "", "Введите фразу для поиска."));
        return;
      }
      const hits = scenario.sources.flatMap((source) => source.excerpt.split("\n")
        .filter((line) => line.toLowerCase().includes(query.toLowerCase()))
        .map((line) => `${source.name} · ${line}`));
      result.append(element("pre", "", `psa source search ${scenario.id} ${JSON.stringify(query)}`));
      for (const hit of hits) result.append(element("p", "", hit));
      if (!hits.length) result.append(element("p", "", "Совпадений в учебных выдержках нет."));
    };
    section.append(form, result);
    return section;
  }

  function media() {
    const section = card("Материал и проверяемая привязка",
      "Локальные учебные файлы. Откройте кадр или воспроизведите запись, затем покажите координаты или интервал наблюдения.");
    const { wrapper, select } = choiceList("Формат", ["PNG · экран", "MP4 · путь пользователя", "WAV · звуковой сигнал"]);
    const holder = element("div", "media-demo");
    const result = output();
    const samples = [
      { tag: "img", file: "sample-screen.png", anchor: "Пиксели · x=57, y=238, ширина 506, высота 57",
        note: "В выделенной области видна кнопка «Подтвердить выделение»." },
      { tag: "video", file: "sample-flow.mp4", anchor: "00:04.000–00:06.000",
        note: "На экране появляется итоговый статус «Операция завершена»." },
      { tag: "audio", file: "sample-cue.wav", anchor: "00:04.000–00:04.160",
        note: "В учебной дорожке слышен синтезированный сигнал. Причину и значение сигнала по одной записи установить нельзя." },
    ];

    function showSample() {
      const previous = holder.querySelector("video, audio");
      if (previous && !previous.paused) previous.pause();
      const sample = samples[select.selectedIndex];
      const player = element(sample.tag);
      if (sample.tag === "img") player.alt = "Учебный макет экрана, кнопка подтверждения внизу";
      else {
        player.controls = true;
        player.preload = "metadata";
      }
      player.src = `media/${sample.file}`;
      holder.replaceChildren(player);
      result.replaceChildren();
    }

    select.onchange = showSample;
    showSample();
    section.append(wrapper, holder, button("Показать привязку", () => {
      const sample = samples[select.selectedIndex];
      if (sample.tag === "img") holder.classList.add("marked-media");
      result.replaceChildren(element("strong", "", sample.anchor), element("p", "", sample.note),
        element("p", "muted", "В PSA media check проверяет границы привязки. Смысл материала оценивает человек или агент после просмотра."));
    }, "primary"), result);
    select.addEventListener("change", () => holder.classList.remove("marked-media"));
    return section;
  }

  function context() {
    const section = card("Инструкции, выбранные по этапу",
      "Фиксированный пример пакета 1.2.0. У каждого реального пакета есть хеш, рассчитанный по содержимому и состоянию кейса.");
    const profiles = [
      ["intake", "psa-intake", "M-SEGMENT-01"],
      ["options", "psa-options", "M-OPTIONS-01"],
      ["strategy", "psa-strategy, psa-communication", "M-ECONOMICS-01, M-COMMUNICATION-01"],
      ["validation", "psa-validation, psa-critic", "C-METRICS-01, C-CRITIC-01"],
    ];
    const { wrapper, select } = choiceList("Этап", profiles.map(([stage]) => stage));
    const result = output();
    select.onchange = () => result.replaceChildren();
    section.append(wrapper, element("code", "demo-note", `psa context ${scenario.id}`),
      button("Показать пакет этапа", () => {
        const [stage, skills, methods] = profiles[select.selectedIndex];
        result.replaceChildren(element("strong", "", `Этап ${stage} · версия 1.2.0`),
          element("p", "", "Правила: AGENTS.md и безопасность."),
          element("p", "", `Навыки: ${skills}.`), element("p", "", `Методики: ${methods}.`));
      }, "primary"), result);
    return section;
  }

  function handoff() {
    const section = card("Узкое задание субагенту",
      "Пример передачи только разрешённой выдержки для проверки основания. Карточка показывает заранее подготовленный результат.");
    const result = output();
    const show = button("Показать результат передачи", () => {
      result.append(element("strong", "", "Ответ роли evidence · симуляция"),
        element("p", "", "C-009 подтверждает уведомление на устройстве. Данных об эффекте семейного предупреждения оператора в выдержке нет."),
        element("p", "muted", "Основной агент сверяет замечание с источником. Ответ роли не меняет реестр и не согласует этап."));
      show.disabled = true;
      prepare.disabled = true;
    });
    const prepare = button("Подготовить пакет для роли evidence", () => {
      result.replaceChildren(element("p", "", "Передаваемая выдержка: C-009, справка Pixel, абзац о пороге."),
        element("p", "", "Вопрос: подтверждает ли цитата операторское семейное предупреждение?"));
      show.disabled = false;
    }, "primary");
    show.disabled = true;
    const actions = element("div", "actions");
    actions.append(prepare, show);
    section.append(actions, result);
    return section;
  }

  function recovery() {
    const section = card("Восстановление после прерывания записи",
      "Учебная операция остановилась после подготовки изменений. Журнал сохраняет состояние и UUID запроса.");
    const result = output();
    const restore = button("Разрешить восстановление", () => {
      result.append(element("p", "", "psa workflow recover · исходная операция подтверждена. Получена одна квитанция."));
      restore.disabled = true;
      inspect.disabled = true;
      replay.disabled = false;
    });
    const replay = button("Проверить точный повтор", () => {
      result.append(element("p", "", "Повтор того же UUID и запроса вернул существующую квитанцию. Записей: 1."));
      replay.disabled = true;
    });
    const inspect = button("Показать незавершённую операцию", () => {
      result.replaceChildren(element("p", "", "psa workflow pending · найдена подготовленная запись. Переход пока не опубликован."));
      restore.disabled = false;
    }, "primary");
    restore.disabled = replay.disabled = true;
    const actions = element("div", "actions");
    actions.append(inspect, restore, replay);
    section.append(actions, result);
    return section;
  }

  function diagnostics() {
    const section = card("Диагностика операции и расходов",
      "Сценарный отчёт только для чтения. В нём видны происхождение значений и границы проверки.");
    const result = output();
    section.append(element("code", "demo-note", `psa diagnostics usage ${scenario.id}`),
      button("Показать пример отчёта", () => {
        result.replaceChildren(
          element("p", "", "Локальная проверка целостности: вызовов модели 0, расходы на модель 0 ₽."),
          element("p", "", "Историческая работа в IDE: токены и стоимость не записаны. В отчёте поля остаются неизвестными."),
          element("p", "muted", "Историческая запись показывает зафиксированный результат. Перед новым согласованием проверяются текущие материалы."),
        );
      }, "primary"), result);
    return section;
  }

  return [
    ["Поиск по источникам", search], ["Контекст этапа", context], ["Медиа и таймкоды", media],
    ["Субагент", handoff], ["Восстановление", recovery], ["Диагностика", diagnostics],
  ];
};
