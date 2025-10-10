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
    original_response: str = None,
    highlighted_texts: List[str] = None,
    api_key: str = None,
    model: str = "gpt-4o-mini",
    max_chars: int = 600,
    custom_instructions: List[str] = None,
) -> Dict:
    """
    Apply moderation strategies to either:
    1. Generate a response (original_response=None) - GENERATION MODE
    2. Refactor an existing response (original_response provided) - REFACTORING MODE
    
    Based on notebook (3) iterative moderation design.
    
    Args:
        child_prompt: The child's original question/prompt
        moderation_types: List of standard moderation strategy names
        original_response: The AI's original response to refactor (optional)
        highlighted_texts: Phrases parent flagged as concerning (optional)
        api_key: OpenAI API key
        model: OpenAI model to use
        max_chars: Maximum combined length of response + rule
        custom_instructions: List of custom instruction texts (optional)
    
    Returns:
        Dict with moderation_types, refactored_response, system_prompt_rule, model, child_prompt,
        original_response, highlighted_texts
    """
    
    # Handle None cases
    if custom_instructions is None:
        custom_instructions = []
    if highlighted_texts is None:
        highlighted_texts = []
    
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
    
    # Different system prompts for different modes
    if original_response:
        # REFACTORING MODE (from notebook function 1)
        # Add highlighted texts context if provided
        highlight_instruction = ""
        if highlighted_texts:
            highlight_instruction = (
                f"\n\nThe parent has highlighted these specific phrases as concerning:\n"
                f"{', '.join(['\"' + text + '\"' for text in highlighted_texts])}\n"
                f"Pay special attention to these phrases when refactoring."
            )
        
        system_content = (
            "You are a child-friendly AI assisting with parent-guided moderation.\n"
            "You will be given a child's original prompt and the assistant's original response.\n"
            f"Your job is to rewrite the response to follow ALL of the following parent-selected rules:\n"
            f"{joined}{highlight_instruction}\n\n"
            "Output STRICTLY as JSON (no extra text):\n"
            '{ "refactored_response": string, "system_prompt_rule": string }\n'
            "Constraints: warm, child-friendly, concise."
        )
        
        user_content = json.dumps({
            "child_prompt": child_prompt,
            "original_response": original_response
        }, ensure_ascii=False)
    else:
        # GENERATION MODE (original behavior)
        system_content = (
            "You are a child-friendly AI assisting with parent-guided moderation.\n"
            "Follow ALL of the following instructions together:\n"
            f"{joined}\n\n"
            "Output STRICTLY as JSON (no extra text):\n"
            '{ "refactored_response": string, "system_prompt_rule": string }\n'
            f"Constraints: warm, age-appropriate, concise; combined length ≤ {max_chars} chars."
        )
        
        user_content = json.dumps({"child_prompt": child_prompt}, ensure_ascii=False)
    
    # Build messages for OpenAI API
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
    
    # Call OpenAI API with correct method
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"}  # Ensures JSON output
    )
    
    # Parse response correctly
    raw = resp.choices[0].message.content or ""
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
        "model": model,
        "child_prompt": child_prompt,
        "original_response": original_response,  # Include in response
        "highlighted_texts": highlighted_texts,  # Include in response
        "moderation_types": all_strategy_names,  # Include both standard and custom
        "refactored_response": refactored,
        "system_prompt_rule": rule,
    }


async def generate_second_pass_prompt(
    initial_prompt: str,
    initial_response: str,
    api_key: str = None,
    model: str = "gpt-4o-mini",
) -> str:
    """
    Generate a realistic follow-up question a child might ask based on
    their initial prompt and the refactored response they received.
    
    Based on notebook (3) function 2.
    
    Args:
        initial_prompt: The child's original question
        initial_response: The refactored/moderated response they received
        api_key: OpenAI API key
        model: OpenAI model to use
    
    Returns:
        A follow-up question string
    """
    
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
    
    system_content = (
        "You are a child-friendly assistant.\n"
        "Task: Create ONE realistic follow-up prompt a child might ask, "
        "based on their initial prompt and your previous response.\n"
        "Output as JSON only:\n"
        '{"child_followup_prompt": string}'
    )
    
    user_payload = {
        "initial_child_prompt": initial_prompt,
        "assistant_initial_response": initial_response
    }
    
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        response_format={"type": "json_object"}
    )
    
    raw = resp.choices[0].message.content or ""
    data = json.loads(raw)
    
    return data.get("child_followup_prompt", "").strip()

