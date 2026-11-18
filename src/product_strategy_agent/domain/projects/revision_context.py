"""Prepare a focused view around the first difference of two source revisions."""


def change_excerpt(before: str, after: str, radius: int = 2000) -> dict:
    offset = next(
        (index for index, (old, new) in enumerate(zip(before, after)) if old != new),
        min(len(before), len(after)),
    )
    start = max(0, offset - 300)
    end = offset + radius
    return {
        "first_difference_offset": offset,
        "excerpt_start_offset": start,
        "before": before[start:end],
        "after": after[start:end],
        "partial": start > 0 or max(len(before), len(after)) > end,
    }
