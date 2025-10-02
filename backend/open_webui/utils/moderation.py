import json
import re
import os
from typing import Dict, List
from openai import OpenAI

# Moderation instructions mapping (updated from Viki's latest notebook)
MODERATION_INSTRUCTIONS = {
    "Refuse Response and Explain": "Decline to answer and give a simple, child-friendly reason.",
    "Remove Harmful Phrases": "Answer but avoid or replace harmful wording.",
    "Omit Unprompted Suggestions": "Only answer the direct question; no extra tips.",
    "Do Not Suggest Workarounds": "Do not offer workarounds or loopholes.",
    "Clarify Child's Intent": "Ask a gentle clarifying question first.",
    "Emphasize Emotional Support": "Acknowledge feelings in a warm, friendly tone.",
    "Explain Problems in Prompt": "Gently explain why the idea could be unsafe/problematic.",
    "Emphasize Risk Awareness": "Briefly mention age-appropriate risks.",
    "Redirect with Alternatives": "Redirect to a safer, positive alternative.",
    "Remind Model is Not Human": "State clearly you're an AI when relevant.",
    "Encourage Introspection": "Prompt the child to self-reflect instead of giving a direct answer.",
    "Tailor to Age Group": "Simplify language to be age-appropriate.",
    "Defer to Parents": "Defer this topic to a parent/trusted adult.",
    "Defer to Resources": "Suggest an appropriate real-world resource.",
}


def _strip_fences(s: str) -> str:
    """Remove markdown code fences from string"""
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", s.strip(), flags=re.I)


async def multi_moderations_openai(
    child_prompt: str,
    moderation_types: List[str],
    api_key: str = None,
    model: str = "gpt-4o-mini",
    max_chars: int = 600,
    custom_instructions: List[str] = None,
) -> Dict:
    """
    Apply multiple moderation strategies at once to a child's prompt.
    Based on Viki's updated multi-moderation logic, extended to support custom instructions.
    
    Args:
        child_prompt: The child's original question/prompt
        moderation_types: List of standard moderation strategy names
        api_key: OpenAI API key
        model: OpenAI model to use
        max_chars: Maximum combined length of response + rule
        custom_instructions: List of custom instruction texts (optional)
    
    Returns:
        Dict with moderation_types, refactored_response, system_prompt_rule, model, child_prompt
    """
    
    # Handle None case
    if custom_instructions is None:
        custom_instructions = []
    
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
    
    # Validate & dedupe standard moderation types, preserve order
    seen = set()
    cleaned = []
    for m in moderation_types:
        if m not in MODERATION_INSTRUCTIONS:
            raise ValueError(f"Unknown moderation_type: {m}")
        if m not in seen:
            cleaned.append(m)
            seen.add(m)
    
    # Build combined instruction list (numbered)
    instruction_parts = []
    idx = 1
    
    # Add standard moderation instructions
    for m in cleaned:
        instruction_parts.append(f"{idx}. {MODERATION_INSTRUCTIONS[m]}")
        idx += 1
    
    # Add custom instructions
    for custom in custom_instructions:
        instruction_parts.append(f"{idx}. {custom}")
        idx += 1
    
    # Allow zero selections -> just give a safe default instruction
    if instruction_parts:
        joined = "\n".join(instruction_parts)
    else:
        joined = "Provide a safe, age-appropriate answer."
    
    # Build system prompt following Viki's pattern
    system_content = (
        "You are a child-friendly AI assisting with parent-guided moderation.\n"
        "Follow ALL of the following instructions together:\n"
        f"{joined}\n\n"
        "Output STRICTLY as JSON (no extra text):\n"
        '{ "refactored_response": string, "system_prompt_rule": string }\n'
        f"Constraints: warm, age-appropriate, concise; combined length ≤ {max_chars} chars."
    )
    
    # Build messages for OpenAI API
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": json.dumps({"child_prompt": child_prompt}, ensure_ascii=False)},
    ]
    
    # Call OpenAI API (following Viki's pattern)
    client = OpenAI(api_key=api_key)
    resp = client.responses.create(model=model, input=messages)
    
    # Parse response
    raw = resp.output_text or ""
    data = json.loads(raw)
    
    # Extract refactored response and rule
    refactored = (data.get("refactored_response") or "").strip()
    rule = (data.get("system_prompt_rule") or "").strip()
    
    # Provide fallbacks if OpenAI didn't return expected data
    if not refactored:
        refactored = "Let's talk with a trusted adult about this. I can help with safer questions."
    if not rule:
        rule = "Prioritize child safety; avoid unsafe details; defer to a parent for sensitive topics."
    
    # Build the response with all applied strategies (standard + custom labels)
    all_strategy_names = cleaned.copy()
    for i, custom in enumerate(custom_instructions, 1):
        # Add custom instructions with labels
        all_strategy_names.append(f"Custom #{i}: {custom[:50]}..." if len(custom) > 50 else f"Custom #{i}: {custom}")
    
    return {
        "moderation_types": all_strategy_names,  # Include both standard and custom
        "refactored_response": refactored,
        "system_prompt_rule": rule,
        "model": model,
        "child_prompt": child_prompt,
    }

