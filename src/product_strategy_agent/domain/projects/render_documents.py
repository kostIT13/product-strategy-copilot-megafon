"""Version-one pure Markdown builder, independent of filesystem publication."""
import json
from product_strategy_agent.domain.projects.render_templates import DRAFTS


def _records(inputs, name):
    return [json.loads(line) for line in inputs[name].splitlines() if line.strip()]


def _write(outputs, name, text):
    outputs[name] = text.rstrip() + "\n"


def _bullets(values):
    return "\n".join(f"- {value}" for value in values) if values else "- Нет данных"


def render_documents_v1(state, inputs):
    sources = _records(inputs, "sources.jsonl")
    claims = _records(inputs, "claims.jsonl")
    gaps = _records(inputs, "gaps.jsonl")
    options = _records(inputs, "options.jsonl")
    decisions = _records(inputs, "decision-log.jsonl")
    capabilities = _records(inputs, "capabilities.jsonl")
    source_map = {item.get("source_id"): item for item in sources}
    outputs: dict[str, str] = {}

    evidence = ["# Реестр доказательств", "", f"Режим исследования: `{state.get('mode', 'decision_grade')}`", "", "## Источники", ""]
    if sources:
        for item in sources:
            evidence.extend([f"### {item.get('source_id', 'S-?')} — {item.get('title', 'Без названия')}",
                             f"- Тип и статус: {item.get('kind', 'неизвестно')} / {item.get('status', 'неизвестно')}",
                             f"- URI/путь: `{item.get('uri_or_path', '')}`",
                             f"- Владелец: {item.get('publisher_or_owner') or 'не указан'}; надёжность: {item.get('reliability', 'не оценена')}",
                             f"- Дата обращения: {item.get('accessed_at', 'не записана')}", ""])
    else:
        evidence.append("Источники пока не добавлены.\n")
    evidence.extend(["## Утверждения", ""])
    if claims:
        for item in claims:
            evidence.extend([f"### {item.get('claim_id', 'C-?')} [{item.get('type', 'тип не задан')}] — уверенность: {item.get('confidence', 'не задана')}",
                             item.get("text", ""), ""])
            for source_id, locator, quote in zip(item.get("source_ids", []), item.get("source_locators", []), item.get("quotes", [])):
                source = source_map.get(source_id, {})
                evidence.extend([f"Основание: **{source_id}** ({source.get('title', 'источник не найден')}), locator `{locator}`.", f"> {quote}", ""])
            if item.get("reasoning_note"):
                evidence.extend([f"Пояснение: {item['reasoning_note']}", ""])
            if item.get("contradicts"):
                evidence.extend([f"Противоречит: {', '.join(item['contradicts'])}", ""])
    else:
        evidence.append("Утверждения пока не добавлены.\n")
    evidence.extend(["## Открытые пробелы", ""])
    if gaps:
        for gap in gaps:
            evidence.extend([f"- **{gap.get('gap_id')} [{gap.get('priority')}]** {gap.get('question')}",
                             f"  - Почему важно: {gap.get('why_it_matters') or 'не указано'}",
                             f"  - Как закрыть: {gap.get('resolution_method') or 'не указано'}"])
    else:
        evidence.append("Пробелы пока не записаны.")
    evidence_path = "03_evidence.md"
    _write(outputs, evidence_path, "\n".join(evidence))

    option_md = ["# Варианты решения", "", "Варианты сравниваются по механизму, эффекту, затратам, рискам и сильнейшему возражению.", ""]
    if options:
        for option in options:
            option_md.extend([f"## {option.get('option_id')} — {option.get('name')} ({option.get('role')})", "",
                              option.get("description", ""), "",
                              f"- Польза: {option.get('benefits') or 'не описана'}",
                              f"- Затраты: {option.get('costs') or 'не описаны'}",
                              f"- Риски: {option.get('risks') or 'не описаны'}",
                              f"- Сильнейшее возражение: {option.get('strongest_objection') or 'не записано'}",
                              f"- Основания: {', '.join(option.get('claim_ids', [])) or 'пока не привязаны'}", ""])
    else:
        option_md.extend(["Варианты пока не добавлены. Требуются как минимум три разных варианта, включая сохранение текущего положения и закрытие направления."])
    roles = {option.get("role") for option in options}
    if options and (len(options) < 3 or not {"status_quo", "stop", "change"}.issubset(roles)):
        option_md.extend(["", "> **Нужно дополнить:** требуется не менее трёх вариантов с ролями `status_quo`, `stop` и `change`."])
    option_path = "04_options.md"
    _write(outputs, option_path, "\n".join(option_md))

    latest = decisions[-1] if decisions else None
    decision_lines = ["# Решение", ""]
    if latest:
        selected = next((item for item in options if item.get("option_id") == latest.get("option_id")), None)
        decision_lines.extend([f"Зафиксированный выбор: **{latest.get('chosen_option')}**", "",
                               f"Вариант: {selected.get('option_id')} — {selected.get('name')}" if selected else "Вариант не связан с записью options.jsonl.",
                               f"Ответственный: {latest.get('owner')}", f"Дата: {latest.get('decided_at')}", "",
                               f"Обоснование: {latest.get('rationale') or 'не записано'}", "",
                               f"Основания: {', '.join(latest.get('claim_ids', [])) or 'не записаны'}", "",
                               f"Отвергнутые альтернативы: {', '.join(latest.get('rejected_alternatives', [])) or 'не записаны'}", "",
                               f"Предпосылки: {', '.join(latest.get('assumptions', [])) or 'не записаны'}", "",
                               f"Риски: {', '.join(latest.get('risks', [])) or 'не записаны'}", "",
                               f"Пересмотреть, когда: {latest.get('revisit_when') or 'условие не записано'}"])
    else:
        decision_lines.append("Решение ещё не зафиксировано. После сравнения вариантов человек выбирает направление командой `psa decision add`.")
    decision_path = "decision.md"
    _write(outputs, decision_path, "\n".join(decision_lines))

    drafts = {name: inputs["drafts/" + name] if inputs["drafts/" + name] is not None else template for name, template in DRAFTS.items()}

    strategy = ["# Стратегия", "", "Этот файл собран из решения и авторских черновиков. Изменяйте черновики в `drafts/`, затем повторно запускайте `psa render`.", "",
                "## Решение", "", latest.get("chosen_option", "Решение ещё не принято") if latest else "Решение ещё не принято", "",
                "## Продуктовая стратегия", "", drafts["product-strategy.md"].strip(), "",
                "## Коммуникационная стратегия", "", drafts["communication-strategy.md"].strip(), "",
                "## Реестр возможностей продукта", ""]
    if capabilities:
        strategy.extend([f"- **{item.get('capability_id')} [{item.get('status')}]** {item.get('name')} — основания: {', '.join(item.get('claim_ids', [])) or 'не указаны'}"
                          for item in capabilities])
    else:
        strategy.append("Возможности продукта пока не зарегистрированы.")
    strategy_path = "05_strategy.md"
    _write(outputs, strategy_path, "\n".join(strategy))

    validation = ["# План проверки", "", "Этот файл собран из авторского черновика в `drafts/validation-plan.md` и открытых пробелов.", "",
                  drafts["validation-plan.md"].strip(), "", "## Пробелы, влияющие на проверку", ""]
    validation.extend([f"- {gap.get('gap_id')}: {gap.get('question')}" for gap in gaps] or ["Пробелы не записаны."])
    validation_path = "06_validation-plan.md"
    _write(outputs, validation_path, "\n".join(validation))
    return outputs
