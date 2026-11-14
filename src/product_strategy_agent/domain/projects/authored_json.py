"""Read one named authored JSON fence without treating examples/comments as input."""

import json
import re
from product_strategy_agent.domain.projects.validation_plan import (
    unique_object,
    reject_constant,
)

NO_BLOCK = object()


def optional_json_block(markdown, name):
    text = re.sub(r"(?s)<!--.*?-->", "", markdown)
    blocks, body, fence, selected = [], [], None, False
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            if fence is None:
                fence, selected, body = marker[1], marker[2].strip() == name, []
            elif (
                marker[1][0] == fence[0]
                and len(marker[1]) >= len(fence)
                and not marker[2].strip()
            ):
                if selected:
                    blocks.append("\n".join(body))
                fence, selected = None, False
            elif selected:
                body.append(line)
        elif selected:
            body.append(line)
    if fence is not None or "<!--" in text or len(blocks) > 1:
        raise ValueError(f"include at most one closed {name} JSON block")
    if not blocks:
        return NO_BLOCK
    try:
        return json.loads(
            blocks[0], object_pairs_hook=unique_object, parse_constant=reject_constant
        )
    except (json.JSONDecodeError, RecursionError):
        raise ValueError("invalid authored calculation JSON") from None
