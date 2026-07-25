MOJIBAKE_MARKERS = ("\u00c3", "\u00c2", "\u00c4", "\u00c5", "\u00e2", "\ufffd")


def repair_text(value: str | None) -> str:
    """Repair common UTF-8-as-Latin-1 text only when it improves the value."""
    text = " ".join(str(value or "").split())
    for _ in range(2):
        if not any(marker in text for marker in MOJIBAKE_MARKERS):
            break
        try:
            candidate = text.encode("latin-1").decode("utf-8")
        except UnicodeError:
            break
        before = sum(text.count(marker) for marker in MOJIBAKE_MARKERS)
        after = sum(candidate.count(marker) for marker in MOJIBAKE_MARKERS)
        if after >= before:
            break
        text = candidate
    return text


def has_mojibake(value: str | None) -> bool:
    return any(marker in str(value or "") for marker in MOJIBAKE_MARKERS)