import re
from typing import Optional
from open_webui.utils.task import rag_template
from open_webui.config import DEFAULT_RAG_TEMPLATE


def extract_mentions(message: str, triggerChar: str = '@'):
    # Escape triggerChar in case it's a regex special character
    triggerChar = re.escape(triggerChar)
    pattern = rf'<{triggerChar}([A-Z]):([^|>]+)'

    matches = re.findall(pattern, message)
    return [{'id_type': id_type, 'id': id_value} for id_type, id_value in matches]


def replace_mentions(message: str, triggerChar: str = '@', use_label: bool = True):
    """
    Replace mentions in the message with either their label (after the pipe `|`)
    or their id if no label exists.

    Example:
      "<@M:gpt-4.1|GPT-4>" -> "GPT-4"   (if use_label=True)
      "<@M:gpt-4.1|GPT-4>" -> "gpt-4.1" (if use_label=False)
    """
    # Escape triggerChar
    triggerChar = re.escape(triggerChar)

    def replacer(match):
        id_type, id_value, label = match.groups()
        return label if use_label and label else id_value

    # Regex captures: idType, id, optional label
    pattern = rf'<{triggerChar}([A-Z]):([^|>]+)(?:\|([^>]+))?>'
    return re.sub(pattern, replacer, message)


def build_message_with_rag_context(user_message: str, sources: list[dict], template: Optional[str] = None) -> str:
    """
    Inject knowledge sources into message using RAG template.
    Simplified for channel messaging (no complex formatting).
    """
    if not sources:
        return user_message

    template = template or DEFAULT_RAG_TEMPLATE

    # Build context from sources
    context_parts = []
    for idx, source in enumerate(sources, 1):
        for doc_idx, doc in enumerate(source.get("document", [])):
            metadata = source.get("metadata", [])[doc_idx] if doc_idx < len(source.get("metadata", [])) else {}
            name = metadata.get("name") or metadata.get("source") or f"Source {idx}"
            context_parts.append(f"[{idx}] {name}:\n{doc}")

    context = "\n\n".join(context_parts)
    return rag_template(template, context, user_message)
