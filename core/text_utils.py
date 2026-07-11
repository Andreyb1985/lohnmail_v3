def repair_mojibake(text: object) -> str:
    repaired = str(text)
    for _ in range(2):
        next_text = None
        for source_encoding in ("latin1", "cp1252"):
            try:
                next_text = repaired.encode(source_encoding).decode("utf-8")
                break
            except UnicodeError:
                continue
        if next_text is None or next_text == repaired:
            break
        repaired = next_text
    return repaired
