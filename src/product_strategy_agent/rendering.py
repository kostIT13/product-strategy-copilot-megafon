"""Render readable project artifacts from canonical ledgers and authored drafts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DRAFTS = {
    "product-strategy.md": """# Продуктовая стратегия\n\n## Аудитория и задача\n\nЗаполните целевой сегмент и задачу, которую он пытается решить.\n\n## Ценность и альтернативы\n\nОпишите ценность, текущие альтернативы и чем выбранное решение лучше.\n\n## Выбор и осознанные отказы\n\nУкажите выбранное направление, границы и то, что сознательно не делаем.\n\n## Связь пользы с затратами и доходами\n\nУкажите известное и отдельно пометьте гипотезы.\n""",
    "communication-strategy.md": """# Коммуникационная стратегия\n\n## Аудитория и ситуация\n\n## Барьер понимания или выбора\n\n## Ключевое сообщение и подтверждение\n\nОбещание должно соответствовать подтверждённым возможностям продукта.\n\n## Роль каналов\n\n## Неподтверждённые обещания\n""",
    "validation-plan.md": """# План проверки\n\n## Ожидаемое изменение\n\n## Базовая линия или сравнение\n\n## Метрики и сегмент\n\n## Окно наблюдения\n\n## Защитные показатели\n\n## Ответственный и критерий решения\n""",
}


def _records(project_dir: Path, name: str) -> list[dict[str, Any]]:
    path = project_dir / name
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write(project_dir: Path, name: str, text: str) -> None:
    (project_dir / name).write_text(text.rstrip() + "\n", encoding="utf-8")


def _bullets(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "- Нет данных"


def render_project(project_dir: Path) -> list[Path]:
    sources = _records(project_dir, "sources.jsonl")
    claims = _records(project_dir, "claims.jsonl")
    gaps = _records(project_dir, "gaps.jsonl")
    options = _records(project_dir, "options.jsonl")
    decisions = _records(project_dir, "decision-log.jsonl")
    source_map = {item.get("source_id"): item for item in sources}
    outputs: list[Path] = []

    evidence = ["# Реестр доказательств", "", "## Источники", ""]
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
    evidence_path = project_dir / "03_evidence.md"
    _write(project_dir, evidence_path.name, "\n".join(evidence))
    outputs.append(evidence_path)

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
    option_path = project_dir / "04_options.md"
    _write(project_dir, option_path.name, "\n".join(option_md))
    outputs.append(option_path)

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
    decision_path = project_dir / "decision.md"
    _write(project_dir, decision_path.name, "\n".join(decision_lines))
    outputs.append(decision_path)

    drafts_dir = project_dir / "drafts"
    drafts_dir.mkdir(exist_ok=True)
    for name, template in DRAFTS.items():
        target = drafts_dir / name
        if not target.exists():
            target.write_text(template, encoding="utf-8")

    strategy = ["# Стратегия", "", "Этот файл собран из решения и авторских черновиков. Изменяйте черновики в `drafts/`, затем повторно запускайте `psa render`.", "",
                "## Решение", "", latest.get("chosen_option", "Решение ещё не принято") if latest else "Решение ещё не принято", "",
                "## Продуктовая стратегия", "", (drafts_dir / "product-strategy.md").read_text(encoding="utf-8").strip(), "",
                "## Коммуникационная стратегия", "", (drafts_dir / "communication-strategy.md").read_text(encoding="utf-8").strip()]
    strategy_path = project_dir / "05_strategy.md"
    _write(project_dir, strategy_path.name, "\n".join(strategy))
    outputs.append(strategy_path)

    validation = ["# План проверки", "", "Этот файл собран из авторского черновика в `drafts/validation-plan.md` и открытых пробелов.", "",
                  (drafts_dir / "validation-plan.md").read_text(encoding="utf-8").strip(), "", "## Пробелы, влияющие на проверку", ""]
    validation.extend([f"- {gap.get('gap_id')}: {gap.get('question')}" for gap in gaps] or ["Пробелы не записаны."])
    validation_path = project_dir / "06_validation-plan.md"
    _write(project_dir, validation_path.name, "\n".join(validation))
    outputs.append(validation_path)
    return outputs
