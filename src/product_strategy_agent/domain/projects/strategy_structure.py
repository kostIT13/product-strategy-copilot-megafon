"""Version-one structural completeness, independent of evidence truth and consent."""

from dataclasses import dataclass
import hashlib
import json
import re

SECTIONS = {
    "drafts/product-strategy.md": (
        ("audience_job", "Аудитория и задача", "Audience and job"),
        ("value_alternatives", "Ценность и альтернативы", "Value and alternatives"),
        (
            "choice_refusals",
            "Выбор и осознанные отказы",
            "Choice and deliberate refusals",
        ),
        ("economics", "Связь пользы с затратами и доходами", "Value costs and revenue"),
    ),
    "drafts/communication-strategy.md": (
        ("audience_situation", "Аудитория и ситуация", "Audience and situation"),
        ("barrier", "Барьер понимания или выбора", "Understanding or choice barrier"),
        (
            "message_proof",
            "Ключевое сообщение и подтверждение",
            "Key message and proof",
        ),
        ("channels", "Роль каналов", "Role of channels"),
    ),
}
PLACEHOLDER = re.compile(
    r"\b(?:todo|tbd|заполните|укажите|опишите)\b|добавьте сюда|fill in|insert here",
    re.IGNORECASE,
)
MARKER = re.compile(
    r"\[(?:C-\d+|HYPOTHESIS|OPEN QUESTION|COMMITMENT:\s*CAP-\d+)\]", re.IGNORECASE
)


@dataclass(frozen=True)
class StrategySnapshot:
    version: int
    documents: dict
    input_hashes: dict


def normalize_heading(value):
    return " ".join(value.strip().rstrip("#").strip().casefold().split())


def inspect_document(path, text):
    specs = SECTIONS[path]
    aliases = {normalize_heading(name): key for key, *names in specs for name in names}
    bodies, lines, issues = {}, {}, []
    if text is None:
        return {"path": path, "sections": [], "issues": ["document_missing"]}
    text = re.sub(r"(?s)<!--.*?-->", lambda match: "\n" * match[0].count("\n"), text)
    if "<!--" in text:
        issues.append("unterminated_comment")
    current, fence = None, None
    for number, line in enumerate(text.splitlines(), 1):
        fenced = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fenced:
            marker = fenced[1]
            if fence is None:
                fence = marker
            elif (
                marker[0] == fence[0]
                and len(marker) >= len(fence)
                and not fenced[2].strip()
            ):
                fence = None
            continue
        if fence is not None or line.startswith(("    ", "\t")):
            continue
        heading = re.match(r"^ {0,3}(#{1,6})(?:\s+|$)(.*)$", line)
        if heading:
            level = len(heading[1])
            if level <= 2:
                current = (
                    aliases.get(normalize_heading(heading[2])) if level == 2 else None
                )
                if current is not None:
                    if current in bodies:
                        issues.append(f"{current}:duplicate_section")
                    else:
                        bodies[current], lines[current] = [], number
            continue
        if current is not None:
            bodies[current].append(line)
    if fence is not None:
        issues.append("unterminated_fence")
    sections = []
    for key, title, _ in specs:
        body = "\n".join(bodies.get(key, []))
        prose = MARKER.sub("", body)
        letters = sum(char.isalpha() for char in prose)
        status = "complete"
        if key not in bodies:
            status = "missing"
        elif PLACEHOLDER.search(body):
            status = "placeholder"
        elif letters < 24:
            status = "empty_or_too_short"
        if status != "complete":
            issues.append(f"{key}:{status}")
        sections.append(
            {
                "id": key,
                "heading": title,
                "line": lines.get(key),
                "status": status,
                "prose_letters": letters,
            }
        )
    return {"path": path, "sections": sections, "issues": issues}


def structure_report(project_id, snapshot):
    documents = [inspect_document(path, snapshot.documents[path]) for path in SECTIONS]
    packet = {
        "format_version": 1,
        "project_id": project_id,
        "workflow_version": snapshot.version,
        "scope": "strategy_structure_v1",
        "structural_status": "incomplete"
        if any(row["issues"] for row in documents)
        else "complete",
        "documents": documents,
        "input_hashes": snapshot.input_hashes,
        "requires_human_review": True,
        "semantic_alignment_verified": False,
        "publication_approved": False,
    }
    raw = json.dumps(packet, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {**packet, "review_hash": hashlib.sha256(raw).hexdigest()}
