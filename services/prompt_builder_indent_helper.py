# services.prompt_builder_indent_helper.py

def indent_three(text: str) -> str:
    """
    Prefix every line in *text* with two tab characters.
    Empty input is returned unchanged.
    """
    if not text:
        return text

    # Split on line breaks, keep the original line‑break characters
    lines = text.splitlines(keepends=True)

    # Add three tabs to the start of each line
    indented_lines = [f"\t\t\t{line}" for line in lines]

    return "".join(indented_lines)
def indent_two(text: str) -> str:
    """
    Prefix every line in *text* with two tab characters.
    Empty input is returned unchanged.
    """
    if not text:
        return text

    # Split on line breaks, keep the original line‑break characters
    lines = text.splitlines(keepends=True)

    # Add two tabs to the start of each line
    indented_lines = [f"\t\t{line}" for line in lines]

    return "".join(indented_lines)
def indent_one(text: str) -> str:
    """
    Prefix every line in *text* with two tab characters.
    Empty input is returned unchanged.
    """
    if not text:
        return text

    # Split on line breaks, keep the original line‑break characters
    lines = text.splitlines(keepends=True)

    # Add one tabs to the start of each line
    indented_lines = [f"\t{line}" for line in lines]

    return "".join(indented_lines)