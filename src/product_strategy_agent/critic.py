"""Build a neutral review bundle for a fresh-context critic."""

from __future__ import annotations

from product_strategy_agent.adapters.persistence.files.workflow_guard import require_workflow_ready
from product_strategy_agent.adapters.persistence.files.case_access import locked_case

import json
from pathlib import Path
from typing import Any

from product_strategy_agent.workflow import MODE_PROFILES


def _read_records(project_dir: Path, filename: str) -> list[dict[str, Any]]:
    path = project_dir / filename
    if not path.is_file():
        return []
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            if isinstance(record, dict):
                result.append(record)
    return result


def _section(project_dir: Path, heading: str, filename: str) -> list[str]:
    path = project_dir / filename
    content = path.read_text(encoding="utf-8").strip() if path.is_file() else "_Не подготовлено._"
    return [f"## {heading}", "", content, ""]


@locked_case
def build_critic_pack(project_dir: Path) -> str:
    require_workflow_ready(project_dir)
    sources = {item.get("source_id"): item for item in _read_records(project_dir, "sources.jsonl")}
    claims = _read_records(project_dir, "claims.jsonl")
    gaps = _read_records(project_dir, "gaps.jsonl")
    options = _read_records(project_dir, "options.jsonl")
    decisions = _read_records(project_dir, "decision-log.jsonl")
    latest = decisions[-1] if decisions else None
    state = json.loads((project_dir / "state.json").read_text(encoding="utf-8"))
    mode = state.get("mode", "decision_grade")
    if not isinstance(mode, str) or mode not in MODE_PROFILES:
        raise ValueError(f"Unknown project mode: {mode}")

    lines = [
        "# Независимый пакет критики",
        "",
        "> Создан автоматически из артефактов проекта. Оцените рекомендацию независимо: выбранный вариант — кандидат для проверки, а не заранее правильный ответ.",
        "",
        "## Задача",
        "",
        (project_dir / "01_brief.md").read_text(encoding="utf-8").strip() if (project_dir / "01_brief.md").is_file() else "_Бриф отсутствует._",
        "",
        "## Кандидат решения",
        "",
        f"Режим анализа: `{mode}` — {MODE_PROFILES[mode]['description']}",
        "",
    ]
    if latest:
        lines.extend([f"- Вариант: {latest.get('chosen_option')}",
                      f"- Связанный option ID: {latest.get('option_id') or 'нет'}",
                      f"- Обоснование: {latest.get('rationale') or 'не записано'}",
                      f"- Основания claim ID: {', '.join(latest.get('claim_ids', [])) or 'не записаны'}",
                      f"- Отвергнутые альтернативы: {', '.join(latest.get('rejected_alternatives', [])) or 'не записаны'}",
                      f"- Условие пересмотра: {latest.get('revisit_when') or 'не записано'}", ""])
    else:
        lines.extend(["_Решение пока не записано._", ""])

    lines.extend(["## Варианты", ""])
    if options:
        for option in options:
            lines.extend([f"### {option.get('option_id')} — {option.get('name')} [{option.get('role')}]"])
            lines.extend([f"- Механизм: {option.get('description')}",
                          f"- Польза: {option.get('benefits') or 'не описана'}",
                          f"- Затраты: {option.get('costs') or 'не описаны'}",
                          f"- Риски: {option.get('risks') or 'не описаны'}",
                          f"- Сильное возражение: {option.get('strongest_objection') or 'не записано'}",
                          f"- Claim IDs: {', '.join(option.get('claim_ids', [])) or 'нет'}", ""])
    else:
        lines.extend(["_Варианты не записаны._", ""])

    lines.extend(["## Утверждения и основания", ""])
    if claims:
        for claim in claims:
            lines.extend([f"### {claim.get('claim_id')} [{claim.get('type')}; уверенность {claim.get('confidence')}]"])
            lines.extend([claim.get("text", "")])
            for source_id, locator, quote in zip(claim.get("source_ids", []), claim.get("source_locators", []), claim.get("quotes", [])):
                source = sources.get(source_id, {})
                lines.extend([f"- Источник: {source_id} — {source.get('title', 'неизвестен')}; locator `{locator}`; статус: {source.get('status', 'неизвестен')}",
                              f"  Цитата: “{quote}”"])
            if claim.get("reasoning_note"):
                lines.append(f"- Пояснение: {claim['reasoning_note']}")
            if claim.get("contradicts"):
                lines.append(f"- Противоречия: {', '.join(claim['contradicts'])}")
            lines.append("")
    else:
        lines.extend(["_Утверждения не записаны._", ""])

    lines.extend(["## Неизвестное и пробелы", ""])
    lines.extend([f"- **{item.get('gap_id')} [{item.get('priority')}]** {item.get('question')} — важно: {item.get('why_it_matters') or 'не указано'}; метод: {item.get('resolution_method') or 'не указан'}" for item in gaps] or ["- Пробелы не записаны."])
    lines.append("")
    lines.extend(_section(project_dir, "Продуктовая стратегия", "drafts/product-strategy.md"))
    lines.extend(_section(project_dir, "Коммуникационная стратегия", "drafts/communication-strategy.md"))
    lines.extend(_section(project_dir, "План проверки", "drafts/validation-plan.md"))
    lines.extend([
        "## Задание рецензенту",
        "",
        "1. Отметьте неподтверждённые выводы, ложную точность, неверную атрибуцию и пропущенные ограничения.",
        "2. Дайте каждому критерию 0 (нет/ошибка), 1 (частично) или 2 (хорошо), с коротким обоснованием:",
        "   - каждое ключевое утверждение имеет проверяемое основание или явно обозначено как гипотеза/синтетика;",
        "   - рассмотрены три разных варианта, включая сохранение текущего положения и закрытие направления;",
        "   - показаны сильное возражение, предпосылки и условие изменения рекомендации;",
        "   - продуктовая и коммуникационная стратегии согласованы и не обещают неподтверждённого;",
        "   - план проверки задаёт метрики, базовую линию, срок и защитные показатели;",
        "   - указано, какие новые данные способны изменить рекомендацию.",
        "3. Назовите сильнейшую альтернативу и одно исследование, которое имеет наибольшую ценность для решения.",
        "4. Не трактуйте синтетические сведения как факты о рынке или реальных пользователях.",
        "",
        "Ответ рецензента не добавляется в реестр доказательств автоматически.",
    ])
    return "\n".join(lines).rstrip() + "\n"


@locked_case
def write_critic_pack(project_dir: Path, output_path: Path | None = None) -> Path:
    require_workflow_ready(project_dir)
    target = output_path or (project_dir / "reviews" / "critic-pack.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_critic_pack(project_dir), encoding="utf-8")
    return target
