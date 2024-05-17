def escape_markdown(text):
    replacements = [
        ("_", r"\_"),
        ("*", r"\*"),
        ("[", r"\["),
        ("]", r"\]"),
        ("(", r"\("),
        (")", r"\)"),
        ("~", r"\~"),
        # ("`", r"\`"),
        (">", r"\>"),
        ("#", r"\#"),
        ("+", r"\+"),
        ("-", r"\-"),
        ("=", r"\="),
        ("|", r"\|"),
        ("{", r"\{"),
        ("}", r"\}"),
        (".", r"\."),
        ("!", r"\!"),
        ("=", r"\="),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    return text


def telegram_markdown_formatter(text: str):
    parts = text.split("`")
    for i, p in enumerate(parts):
        if i % 2 == 0:
            parts[i] = escape_markdown(p)
    return "`".join(parts)
