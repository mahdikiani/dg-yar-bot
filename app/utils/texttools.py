import re
import string


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


def is_url(string):
    pattern = re.compile(
        r"^(https?:\/\/)"  # Protocol
        r"([a-zA-Z0-9_-]+\.)*"  # Subdomain (optional)
        r"([a-zA-Z0-9-]{2,})"  # Domain
        r"(\.[a-zA-Z0-9-]{2,})*"  # Domain extension
        r"(\.[a-z]{2,6})"  # Top-level domain
        r"([\/\w .-]*)*"  # Path (optional)
        r"(\?[;&a-zA-Z0-9%_.~+=-]*)?"  # Query string (optional)
        r"(#[-a-zA-Z0-9_]*)?$"  # Fragment (optional)
    )
    return re.match(pattern, string) is not None


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


def split_text(text, max_chunk_size=4096):
    # Split text into paragraphs
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 1 > max_chunk_size:
            if current_chunk:
                if current_chunk.count("```") % 2 == 1:
                    chunks.append(current_chunk[: current_chunk.rfind("```")].strip())
                    current_chunk = current_chunk[current_chunk.rfind("```") :]
                    continue

                chunks.append(current_chunk.strip())
                current_chunk = ""
                continue

        if len(paragraph) > max_chunk_size:
            # Split paragraph into sentences
            sentences = re.split(r"(?<=[.!?]) +", paragraph)
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 1 > max_chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = ""
                if len(sentence) > max_chunk_size:
                    # Split sentence into words
                    words = sentence.split(" ")
                    for word in words:
                        if len(current_chunk) + len(word) + 1 > max_chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                current_chunk = ""
                        current_chunk += word + " "
                else:
                    current_chunk += sentence + " "
        else:
            current_chunk += paragraph + "\n"
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def split_text2(text, max_chunk_size=4096):
    def should_split_within_code_block(text):
        return text.count("```") % 2 == 1

    # Split text into paragraphs
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = ""
    code_block_active = False

    for paragraph in paragraphs:
        if "```" in paragraph:
            code_block_active = not code_block_active

        # If we are already within a code block, or if adding this paragraph would exceed max_chunk_size
        if (
            len(current_chunk) + len(paragraph) + 1 > max_chunk_size
            and not code_block_active
        ):
            if current_chunk:
                # Make sure not to split code blocks
                if should_split_within_code_block(current_chunk):
                    current_chunk += paragraph + "\n"
                    continue

                chunks.append(current_chunk.strip())
                current_chunk = ""

        if len(paragraph) > max_chunk_size and not code_block_active:
            # Split paragraph into sentences if it's not a code block
            sentences = re.split(r"(?<=[.!?]) +", paragraph)
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 1 > max_chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = ""
                if len(sentence) > max_chunk_size:
                    # Split sentence into words
                    words = sentence.split(" ")
                    for word in words:
                        if len(current_chunk) + len(word) + 1 > max_chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                current_chunk = ""
                        current_chunk += word + " "
                else:
                    current_chunk += sentence + " "
        else:
            current_chunk += paragraph + "\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def backtick_formatter(text: str):
    text = text.strip().strip("```json").strip("```").strip()
    # if text.startswith("```"):
    #     text = "\n".join(text.split("\n")[1:-1])
    return text


def format_keys(text: str) -> set[str]:
    return {t[1] for t in string.Formatter().parse(text) if t[1]}


def format_fixer(**kwargs):
    list_length = len(next(iter(kwargs.values())))

    # Initialize the target list
    target = []

    # Iterate over each index of the lists
    for i in range(list_length):
        # Create a new dictionary for each index
        entry = {key: kwargs[key][i] for key in kwargs}
        # Append the new dictionary to the target list
        target.append(entry)

    return target


def get_dict_data(data, key, value):
    for r in data:
        if r.get(key) == value:
            return r
