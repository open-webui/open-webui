"""The visualization tool validates source; only the isolated browser frame executes it."""

from typing import Literal

MAX_HTML_BYTES = 256 * 1024


async def render_visualization(
    title: str,
    html: str,
    libraries: list[Literal['chartjs']] | None = None,
) -> dict:
    """Render an interactive chart, SVG diagram, calculator, or explainer inline in chat.

    Use proactively when a visual helps the user understand or explore the answer,
    even when they have not explicitly asked for a visualization. Good uses include
    comparisons, trends, mechanisms, and exploring how inputs change an outcome.
    Prefer plain text for simple facts or short answers. Put the entire visualization
    in html; write explanation in normal messages. HTML/SVG previews
    appear progressively. Scripts run once, after the complete call is accepted.
    Default to a lean, compact, flat inline design: concise labels, restrained spacing,
    readable text, and only useful controls. Use regular font weight almost everywhere;
    use medium (500) sparingly and never heavier weights. Prefer flat layouts to cards.
    Inherit the default body text size (0.90625rem, matching chat) for normal text
    and labels; do not shrink body text to make a layout compact.
    Use rem for CSS typography, spacing, radii, and dimensions; use responsive widths.
    Prefer 0.25–0.5rem gaps and padding, with 0.75rem only between distinct sections.
    Keep labels close to controls and trim heading, paragraph, and list margins.
    Avoid fixed-pixel styling and empty space.
    The chat displays title above the visual; avoid repeating it in html. Avoid hero
    headers, introductory copy, decorative gradients/shadows, oversized typography,
    and nested cards unless requested.
    Let content determine height; use the chat's scrolling, not internal scroll areas.
    Emit a fragment: styles first, visible content next, classic inline scripts last.
    Use addEventListener, not onclick attributes or DOMContentLoaded. No external
    scripts, imports, fetch, frames, or parent-page access are available.
    Request libraries=["chartjs"] to get window.Chart (no script URL needed).
    Wrap each canvas in .chart-container; use responsive:true, maintainAspectRatio:false.
    Buttons, inputs, tables, and details have built-in styling. Use CSS variables
    --owui-background, --owui-surface, --owui-text, --owui-muted, --owui-border,
    --owui-accent. Include accessible labels and responsive layouts; avoid vh heights.
    window.openwebui.context supplies theme, language, direction, reducedMotion.
    Listen for openwebui:contextchange for custom canvas theme updates.
    await openwebui.sendMessage(text) requests a user-confirmed follow-up and returns
    {sent:boolean}. Never assume access to chat history, credentials, or storage.

    :param title: Short accessible title, 1–160 characters.
    :param html: Self-contained HTML/SVG/CSS/JavaScript fragment, at most 256 KiB UTF-8.
    :param libraries: Omit or use [] for native HTML/SVG, or ["chartjs"] for charts.
    """
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 160:
        return {'error': 'title must contain 1–160 characters'}
    if not isinstance(html, str) or not html.strip():
        return {'error': 'html must be a nonempty string'}
    try:
        size = len(html.encode('utf-8'))
    except UnicodeEncodeError:
        return {'error': 'html must contain valid Unicode'}
    if size > MAX_HTML_BYTES:
        return {'error': 'html exceeds the 256 KiB limit'}
    if libraries is not None and libraries not in ([], ['chartjs']):
        return {'error': 'libraries must be [] or ["chartjs"]'}
    return {'status': 'accepted'}
