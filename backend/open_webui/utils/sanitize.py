import re


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
