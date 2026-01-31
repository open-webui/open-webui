import json
import re
import os
import httpx
from typing import Dict, List
from openai import OpenAI

# Moderation instructions mapping
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
    # model: str = "gpt-5.2-pro-2025-12-11",  # Commented out: using chat-latest instead
    model: str = "gpt-5.2-chat-latest",
    max_chars: int = 600,
    custom_instructions: List[str] = None,
    child_age: str = None,
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
        child_age: Child's age for age-appropriate tailoring (optional)

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
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

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
        # Customize "Tailor to Age Group" instruction if child_age is provided
        if m == "Tailor to Age Group" and child_age:
            instruction_parts.append(
                f"{idx}. Tailor language and complexity for a {child_age} child. Explain terms and concepts they might not understand."
            )
        else:
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
        system_content = (
            "You are a child-friendly AI assisting with parent-guided moderation.\n"
            "You will be given a child's original prompt and the assistant's original response.\n"
            "Your job is to rewrite the response to follow ALL of the following parent-selected rules:\n"
            f"{joined}\n\n"
            "Output STRICTLY as JSON (no extra text):\n"
            '{ "refactored_response": string, "system_prompt_rule": string }\n'
            f"Constraints: warm, child-friendly, concise; combined length ≤ {max_chars} chars."
        )

        user_content = json.dumps(
            {"child_prompt": child_prompt, "original_response": original_response},
            ensure_ascii=False,
        )
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

    # Build messages array for Chat Completions API
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    # Call OpenAI API using Chat Completions endpoint (for gpt-5.2-chat-latest)
    # Commented out: Responses API code (for gpt-5.2-pro-2025-12-11)
    # client = OpenAI(api_key=api_key)
    # print(f"🔍 [MODERATION] Calling OpenAI API with model: {model}")
    # resp = client.responses.create(
    #     model=model,
    #     input=user_content,  # User content as input string
    #     instructions=system_content  # System instructions
    # )
    # print(f"✅ [MODERATION] OpenAI API response received. Model used: {resp.model}")
    #
    # # Parse response (Responses API returns output array with content items)
    # # Try SDK convenience property first (output_text), then fall back to manual parsing
    # raw = ""
    # try:
    #     # Check if SDK provides output_text convenience property (SDK-only, supported in Python SDK)
    #     if hasattr(resp, 'output_text') and resp.output_text:
    #         raw = resp.output_text
    #         print(f"✅ [MODERATION] Extracted text using output_text property")
    #     elif hasattr(resp, 'output') and resp.output and len(resp.output) > 0:
    #         # Parse output array structure: output[0].content[0].text
    #         output_item = resp.output[0]
    #
    #         # Get content array from output item
    #         if hasattr(output_item, 'content'):
    #             content = output_item.content
    #         elif isinstance(output_item, dict):
    #             content = output_item.get('content')
    #         else:
    #             content = None
    #
    #         if content and len(content) > 0:
    #             # Get first content item (should be output_text type)
    #             content_item = content[0]
    #
    #             # Extract text from content item
    #             if hasattr(content_item, 'text'):
    #                 raw = content_item.text or ""
    #             elif isinstance(content_item, dict):
    #                 raw = content_item.get('text') or ""
    #             elif hasattr(content_item, 'type') and content_item.type == 'output_text':
    #                 # Handle output_text type explicitly
    #                 if hasattr(content_item, 'text'):
    #                     raw = content_item.text or ""
    #                 elif isinstance(content_item, dict):
    #                     raw = content_item.get('text') or ""
    #
    #             if raw:
    #                 print(f"✅ [MODERATION] Extracted text from output array structure")
    # except Exception as e:
    #     print(f"⚠️ [MODERATION] Error parsing response: {e}")
    #     import traceback
    #     print(f"⚠️ [MODERATION] Traceback: {traceback.format_exc()}")
    #     raw = ""
    #
    # if not raw:
    #     # Additional debugging before raising error
    #     print(f"🔍 [MODERATION] Failed to extract text. Response structure:")
    #     print(f"  - Has output_text: {hasattr(resp, 'output_text')}")
    #     if hasattr(resp, 'output_text'):
    #         print(f"  - output_text value: {resp.output_text}")
    #     print(f"  - Has output: {hasattr(resp, 'output')}")
    #     if hasattr(resp, 'output'):
    #         print(f"  - output type: {type(resp.output)}")
    #         print(f"  - output length: {len(resp.output) if resp.output else 0}")
    #         if resp.output and len(resp.output) > 0:
    #             print(f"  - output[0] type: {type(resp.output[0])}")
    #             print(f"  - output[0] attributes: {[x for x in dir(resp.output[0]) if not x.startswith('_')] if hasattr(resp.output[0], '__dict__') else 'N/A'}")
    #     raise ValueError("Failed to extract text from Responses API response")

    client = OpenAI(api_key=api_key)
    print(f"🔍 [MODERATION] Calling OpenAI API with model: {model}")
    resp = client.chat.completions.create(model=model, messages=messages)
    print(f"✅ [MODERATION] OpenAI API response received. Model used: {resp.model}")

    # Parse response (Chat Completions API)
    raw = resp.choices[0].message.content or ""

    data = json.loads(_strip_fences(raw))

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
        all_strategy_names.append(
            f"Custom #{i}: {custom[:50]}..."
            if len(custom) > 50
            else f"Custom #{i}: {custom}"
        )

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
    # model: str = "gpt-5.2-pro-2025-12-11",  # Commented out: using chat-latest instead
    model: str = "gpt-5.2-chat-latest",
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
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

    system_content = (
        "You are a child-friendly assistant.\n"
        "Task: Create ONE realistic follow-up prompt a child might ask, "
        "based on their initial prompt and your previous response.\n"
        "Output as JSON only:\n"
        '{"child_followup_prompt": string}'
    )

    user_payload = {
        "initial_child_prompt": initial_prompt,
        "assistant_initial_response": initial_response,
    }

    # Build messages array for Chat Completions API
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]

    # Call OpenAI API using Chat Completions endpoint (for gpt-5.2-chat-latest)
    # Commented out: Responses API code (for gpt-5.2-pro-2025-12-11)
    # client = OpenAI(api_key=api_key)
    # print(f"🔍 [FOLLOWUP] Calling OpenAI API with model: {model}")
    # resp = client.responses.create(
    #     model=model,
    #     input=json.dumps(user_payload, ensure_ascii=False),  # User content as input string
    #     instructions=system_content  # System instructions
    # )
    # print(f"✅ [FOLLOWUP] OpenAI API response received. Model used: {resp.model}")
    #
    # # Parse response (Responses API returns output array with content items)
    # # Try SDK convenience property first (output_text), then fall back to manual parsing
    # raw = ""
    # try:
    #     # Check if SDK provides output_text convenience property (SDK-only, supported in Python SDK)
    #     if hasattr(resp, 'output_text') and resp.output_text:
    #         raw = resp.output_text
    #         print(f"✅ [FOLLOWUP] Extracted text using output_text property")
    #     elif hasattr(resp, 'output') and resp.output and len(resp.output) > 0:
    #         # Parse output array structure: output[0].content[0].text
    #         output_item = resp.output[0]
    #
    #         # Get content array from output item
    #         if hasattr(output_item, 'content'):
    #             content = output_item.content
    #         elif isinstance(output_item, dict):
    #             content = output_item.get('content')
    #         else:
    #             content = None
    #
    #         if content and len(content) > 0:
    #             # Get first content item (should be output_text type)
    #             content_item = content[0]
    #
    #             # Extract text from content item
    #             if hasattr(content_item, 'text'):
    #                 raw = content_item.text or ""
    #             elif isinstance(content_item, dict):
    #                 raw = content_item.get('text') or ""
    #             elif hasattr(content_item, 'type') and content_item.type == 'output_text':
    #                 # Handle output_text type explicitly
    #                 if hasattr(content_item, 'text'):
    #                     raw = content_item.text or ""
    #                 elif isinstance(content_item, dict):
    #                     raw = content_item.get('text') or ""
    #
    #             if raw:
    #                 print(f"✅ [FOLLOWUP] Extracted text from output array structure")
    # except Exception as e:
    #     print(f"⚠️ [FOLLOWUP] Error parsing response: {e}")
    #     import traceback
    #     print(f"⚠️ [FOLLOWUP] Traceback: {traceback.format_exc()}")
    #     raw = ""
    #
    # if not raw:
    #     # Additional debugging before raising error
    #     print(f"🔍 [FOLLOWUP] Failed to extract text. Response structure:")
    #     print(f"  - Has output_text: {hasattr(resp, 'output_text')}")
    #     if hasattr(resp, 'output_text'):
    #         print(f"  - output_text value: {resp.output_text}")
    #     print(f"  - Has output: {hasattr(resp, 'output')}")
    #     if hasattr(resp, 'output'):
    #         print(f"  - output type: {type(resp.output)}")
    #         print(f"  - output length: {len(resp.output) if resp.output else 0}")
    #         if resp.output and len(resp.output) > 0:
    #             print(f"  - output[0] type: {type(resp.output[0])}")
    #             print(f"  - output[0] attributes: {[x for x in dir(resp.output[0]) if not x.startswith('_')] if hasattr(resp.output[0], '__dict__') else 'N/A'}")
    #     raise ValueError("Failed to extract text from Responses API response")

    client = OpenAI(api_key=api_key)
    print(f"🔍 [FOLLOWUP] Calling OpenAI API with model: {model}")
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    print(f"✅ [FOLLOWUP] OpenAI API response received. Model used: {resp.model}")

    # Parse response (Chat Completions API)
    raw = resp.choices[0].message.content or ""

    data = json.loads(_strip_fences(raw))

    return data.get("child_followup_prompt", "").strip()
