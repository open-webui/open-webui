import re

# ANSI escape code pattern - matches all common ANSI sequences
# This includes color codes, cursor movement, and other terminal control sequences
ANSI_ESCAPE_PATTERN = re.compile(
    r"\x1b\[[0-9;]*[A-Za-z]|\x1b\([AB]|\x1b[PX^_].*?\x1b\\|\x1b\].*?(?:\x07|\x1b\\)"
)


def strip_ansi_codes(text: str) -> str:
    """
    Strip ANSI escape codes from text.

    ANSI escape codes can be introduced by LLMs that include terminal
    color codes in their output. These codes cause syntax errors when
    the code is sent to Jupyter for execution.

    Common ANSI codes include:
    - Color codes: \x1b[31m (red), \x1b[32m (green), etc.
    - Reset codes: \x1b[0m, \x1b[39m
    - Cursor movement: \x1b[1A, \x1b[2J, etc.
    """
    return ANSI_ESCAPE_PATTERN.sub("", text)


def strip_markdown_code_fences(code: str) -> str:
    """
    Strip markdown code fences if present.

    This is a defensive, non-breaking change — if the code doesn't
    contain fences, it passes through unchanged.

    Handles patterns like:
    - ```python
    - ```py
    - ```
    """
    code = code.strip()
    # Remove opening fence (```python, ```py, ``` etc.)
    code = re.sub(r"^```\w*\n?", "", code)
    # Remove closing fence
    code = re.sub(r"\n?```\s*$", "", code)
    return code.strip()


def sanitize_code(code: str) -> str:
    """
    Sanitize code for execution by applying all necessary cleanup steps.

    This is the recommended function to use before sending code to
    interpreters like Jupyter or Pyodide.

    Steps applied:
    1. Strip ANSI escape codes (from LLM output)
    2. Strip markdown code fences (if model included them)
    """
    code = strip_ansi_codes(code)
    code = strip_markdown_code_fences(code)
    return code
