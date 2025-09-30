import json
import re
import os
from typing import Dict

# Moderation instructions mapping
MODERATION_INSTRUCTIONS = {
    "Refuse Response and Explain": "Decline to answer and give a simple, child-friendly reason. Also return a short system rule.",
    "Remove Harmful Phrases": "Answer but avoid or replace harmful wording. Also return a short system rule.",
    "Omit Unprompted Suggestions": "Only answer the direct question; no extra tips. Also return a short system rule.",
    "Do Not Suggest Workarounds": "Do not offer workarounds or loopholes. Also return a short system rule.",
    "Clarify Child's Intent": "Ask a gentle clarifying question first. Also return a short system rule.",
    "Emphasize Emotional Support": "Acknowledge feelings in a warm, friendly tone. Also return a short system rule.",
    "Explain Problems in Prompt": "Gently explain why the idea could be unsafe/problematic. Also return a short system rule.",
    "Emphasize Risk Awareness": "Briefly mention age-appropriate risks. Also return a short system rule.",
    "Redirect with Alternatives": "Redirect to a safer, positive alternative. Also return a short system rule.",
    "Remind Model is Not Human": "State clearly you're an AI when relevant. Also return a short system rule.",
    "Encourage Introspection": "Prompt the child to self-reflect instead of giving a direct answer. Also return a short system rule.",
    "Tailor to Age Group": "Simplify language to be age-appropriate. Also return a short system rule.",
    "Defer to Parents": "Defer this topic to a parent/trusted adult. Also return a short system rule.",
    "Defer to Resources": "Suggest an appropriate real-world resource. Also return a short system rule.",
}


def _strip_fences(s: str) -> str:
    """Remove markdown code fences from string"""
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", s.strip(), flags=re.I)


async def apply_moderation_and_update(
    child_prompt: str,
    moderation_type: str,
    api_key: str = None,
    model: str = "gpt-4o-mini",
    max_chars: int = 600,
) -> Dict:
    """
    Apply moderation strategy to a child's prompt and generate refactored response.
    
    This is a demo/mock version that simulates the OpenAI call.
    In production, you would actually call OpenAI's API here.
    """
    
    # Get the instruction for this moderation type
    instruction = MODERATION_INSTRUCTIONS.get(moderation_type)
    
    if not instruction:
        raise ValueError(f"Invalid moderation type: {moderation_type}")
    
    # For demo purposes, we'll create a mock response
    # In production, this would call OpenAI's API with the system prompt
    
    # Mock refactored responses based on moderation type
    # In production, these would come from OpenAI API calls using Viki's logic
    mock_responses = {
        "Refuse Response and Explain": {
            "refactored_response": "I can't help with that question. It's something best discussed with a parent or trusted adult who can give you the right guidance for your age.",
            "system_prompt_rule": "When a child asks about sensitive topics, politely decline and suggest they speak with a trusted adult."
        },
        "Remove Harmful Phrases": {
            "refactored_response": "That's an interesting question. Let's discuss this topic in a way that's safe and appropriate for you. Would you like to talk about something related but more suitable?",
            "system_prompt_rule": "Replace potentially harmful content with age-appropriate alternatives."
        },
        "Omit Unprompted Suggestions": {
            "refactored_response": "I can answer your direct question, but I'll keep it simple and won't suggest extra things you didn't ask about.",
            "system_prompt_rule": "Answer only what's asked without providing unsolicited suggestions or workarounds."
        },
        "Do Not Suggest Workarounds": {
            "refactored_response": "I understand your question, but I can't provide ways to get around rules or safety measures. Let's focus on following the right approach.",
            "system_prompt_rule": "Never suggest loopholes, workarounds, or ways to bypass rules or safety measures."
        },
        "Clarify Child's Intent": {
            "refactored_response": "I want to make sure I understand what you're asking. Can you tell me a little more about why you're curious about this?",
            "system_prompt_rule": "Ask clarifying questions to understand the child's true intent before providing an answer."
        },
        "Emphasize Emotional Support": {
            "refactored_response": "I understand you might be curious about this. It's normal to have questions! Let's talk with a trusted adult who can help answer this in the best way for you.",
            "system_prompt_rule": "Acknowledge the child's feelings warmly before redirecting to appropriate support."
        },
        "Explain Problems in Prompt": {
            "refactored_response": "I notice this question might lead to something unsafe or not quite right. Let me explain why this could be a problem, and then we can find a better approach together.",
            "system_prompt_rule": "Gently explain why a prompt or idea could be problematic before suggesting alternatives."
        },
        "Emphasize Risk Awareness": {
            "refactored_response": "Before we talk about this, it's important to know that there are some risks involved. Let me help you understand them in a way that makes sense for your age.",
            "system_prompt_rule": "Always mention age-appropriate risks when discussing potentially dangerous topics."
        },
        "Redirect with Alternatives": {
            "refactored_response": "Let's talk about something fun instead! How about we discuss your favorite hobbies or learn about cool animals? What interests you most?",
            "system_prompt_rule": "When encountering inappropriate topics, redirect the conversation to age-appropriate, positive alternatives."
        },
        "Remind Model is Not Human": {
            "refactored_response": "Remember, I'm an AI assistant, not a real person. For this kind of question, it's better to talk to a real human like your parent or teacher who can help you properly.",
            "system_prompt_rule": "Clearly state AI limitations and remind children to seek human guidance when appropriate."
        },
        "Encourage Introspection": {
            "refactored_response": "That's a thoughtful question! Before I answer, what do you think about this? Sometimes thinking it through yourself can help you learn even more.",
            "system_prompt_rule": "Prompt children to reflect and think critically before providing direct answers."
        },
        "Tailor to Age Group": {
            "refactored_response": "Let me explain this in a simple way that's easy to understand. [Age-appropriate simplified explanation would go here]",
            "system_prompt_rule": "Always simplify language and concepts to be developmentally appropriate for the child's age."
        },
        "Defer to Parents": {
            "refactored_response": "This is something best discussed with your parent or a trusted adult. They can give you the right information and guidance for this topic.",
            "system_prompt_rule": "Defer sensitive, complex, or personal topics to parents or trusted adults."
        },
        "Defer to Resources": {
            "refactored_response": "This is a great question for talking to a teacher, reading a book about it from the library, or checking out kid-friendly educational websites with your parent.",
            "system_prompt_rule": "Suggest appropriate real-world resources like teachers, libraries, or educational materials."
        }
    }
    
    # Get mock response or use a generic fallback (shouldn't happen with all 14 defined)
    mock_data = mock_responses.get(moderation_type, {
        "refactored_response": "Let's talk with a trusted adult about this topic. They can help guide you in the right direction.",
        "system_prompt_rule": f"Apply {moderation_type} moderation strategy to protect child safety."
    })
    
    return {
        "type": "moderation_update",
        "data": {
            "moderation_type": moderation_type,
            "instruction_used": instruction,
            "child_prompt": child_prompt,
            "refactored_response": mock_data["refactored_response"],
            "system_prompt_rule": mock_data["system_prompt_rule"],
            "max_chars": max_chars,
            "model": model,
        }
    }

