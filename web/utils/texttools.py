import re


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
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    return text


def telegram_markdown_formatter(text: str, **kwargs):
    if kwargs.get("bot", "telegram") != "telegram":
        return text
    parts = text.split("`")
    for i, p in enumerate(parts):
        if i % 2 == 0:
            parts[i] = escape_markdown(p)
    return "`".join(parts)


# Define a regular expression pattern for a URL
url_pattern = re.compile(
    r"^(https?|ftp):\/\/"  # http:// or https:// or ftp://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
    r"localhost|"  # localhost...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|"  # ...or ipv4
    r"\[?[A-F0-9]*:[A-F0-9:]+\]?)"  # ...or ipv6
    r"(?::\d+)?"  # optional port
    r"(?:\/[^\s]*)?$",  # resource path
    re.IGNORECASE,
)


def is_valid_url(url: str) -> bool:
    return re.match(url_pattern, url) is not None
