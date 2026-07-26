MOJIBAKE_MARKERS = ("\u00c3", "\u00c2", "\u00c4", "\u00c5", "\u00e2", "\ufffd")


def repair_text(value: str | None) -> str:
    """Repair repeated UTF-8-as-single-byte corruption without fabricating text."""
    text = " ".join(str(value or "").split())
    for _ in range(3):
        if not any(marker in text for marker in MOJIBAKE_MARKERS):
            break
        before = sum(text.count(marker) for marker in MOJIBAKE_MARKERS)
        best = text
        for encoding in ("latin-1", "cp1252"):
            try:
                candidate = text.encode(encoding).decode("utf-8")
            except UnicodeError:
                continue
            after = sum(candidate.count(marker) for marker in MOJIBAKE_MARKERS)
            if after < before:
                best = candidate
                break
        if best == text:
            break
        text = best
    return text


def has_mojibake(value: str | None) -> bool:
    return any(marker in str(value or "") for marker in MOJIBAKE_MARKERS)