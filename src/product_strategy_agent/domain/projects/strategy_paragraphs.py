"""Existing Markdown trace markers and paragraph semantics, without filesystem I/O."""

import re

CLAIM_MARKER = re.compile(r"\[(C-\d+)\]")
CLASSIFICATION_MARKER = re.compile(r"\[(HYPOTHESIS|OPEN QUESTION)\]", re.IGNORECASE)
COMMITMENT_MARKER = re.compile(r"\[COMMITMENT:\s*(CAP-\d+)\]", re.IGNORECASE)


def paragraphs(text):
    text = re.sub(
        r"(?s)<!--.*?-->", lambda match: "\n" * match.group(0).count("\n"), text
    )
    result, section = [], ""
    for match in re.finditer(r"(?m)(?:^\s*\n)*(\S[\s\S]*?)(?=\n\s*\n|\Z)", text):
        paragraph = " ".join(line.strip() for line in match.group(1).splitlines())
        if paragraph.casefold().startswith(
            ("заполните ", "укажите ", "опишите ", "добавьте сюда", "todo", "tbd")
        ):
            continue
        lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
        if lines and all(line.startswith("#") for line in lines):
            section = lines[-1].lstrip("# ").strip()
        elif paragraph:
            result.append((text.count("\n", 0, match.start(1)) + 1, paragraph, section))
    return result
