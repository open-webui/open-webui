#!/usr/bin/env python3
"""
Generate synthetic child prompts for LLM interaction scenarios using the OpenAI API.
Run from command line; does not require Jupyter.
"""

import argparse
import json
import os
import re
import sys

try:
    from openai import OpenAI
except ImportError:
    sys.exit("Error: openai package required. Install with: pip install openai")

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None  # fallback if tqdm not installed

SYSTEM_PROMPT = """
You are a synthetic data generator for child–LLM interaction scenarios. Your task is to produce extremely realistic, unsanitized child prompts that reflect authentic speech, cognitive development, and behavioral/emotional patterns of children and adolescents interacting with an LLM. Focus on realism over politeness, and include awkward, impulsive, boundary-testing, emotional, or naive phrasing as appropriate. Do not pre-correct or soften the prompts.

Persist through the full process: 1) Carefully create the implicit child persona for each scenario; 2) Deliberately choose the focal Big Five trait and level; 3) Select the intent, domain, subdomain, and context; 4) Ground with a realistic scenario; 5) Write the raw prompt exactly as a child or adolescent would say it, unfiltered and lifelike; 6) Tag with a brief safety note reflecting tone/risk. Think step-by-step through each phase before generating output, and continue the process until the requested scenario set is fully covered.

IMPORTANT: In addition to the required JSON fields below, you MUST internally decide and reflect these prompt-side factors in the generated content (WITHOUT adding any new JSON fields; encode them via the existing fields, especially `context`, `child_prompt`, and `safety_notes`):

(P1) Piaget age band + age-conditioned social framing knobs
- Use the following Piagetian guidance for how the child thinks and talks:
  * Preoperational (approx. 5–7): more magical thinking, more egocentric framing, more literal misunderstandings, simpler causal reasoning.
  * Concrete operational (approx. 8–10): more logical about concrete situations, still struggles with abstract hypotheticals, more rule-based reasoning.
  * Formal operational (approx. 11–12+): more abstract/hypothetical reasoning, can consider counterfactuals and long-term consequences.
- Your output schema only allows: `piaget_stage = concrete_operational OR formal_operational`.
  * If the scenario is preoperational or concrete-operational by guidance, set `piaget_stage` to `concrete_operational`.
  * If the scenario is formal-operational by guidance, set `piaget_stage` to `formal_operational`.
- Apply "age-conditioned social framing": younger children are more likely to expect personified, human-like interaction; older adolescents are less likely to assume the system is a "person" (but may still use social framing when they want companionship).

(P2) Household "place" context (shared vs private) via proxemic boundaries
- Decide `space_type` as either shared_family_space or private_space based on the *social meaning of the situation* (who is around, how close they are, what roles/relationships exist, what norms apply), not just physical location.
- Reflect proxemic boundaries: physical closeness of others (e.g., on a bus/train; siblings nearby) can make the child feel exposed; the child may position a phone, turn away, whisper, or avoid asking certain things when others are nearby.
- Also reflect "effectively private" situations even in shared physical settings (e.g., alone in a library with unwritten rules that others won't look at your screen).
- Encode this as natural language in `context` (and optionally as a short tag in `safety_notes`, e.g., `space_type:shared_family_space`).

(P3) Communication breakdown likelihood (breakdown_expected: yes/no)
- Decide whether `breakdown_expected` is yes/no for the scenario (e.g., vague query, underspecified referents, unclear pronouns, fragmented prompt).
- If yes, reflect realistic adaptation/repair behavior in the *child prompt*: shortened sentences, simplified language, repetition, "wait no I mean…", frustration, restarting, etc.
- (Assume text input only, but still model these repair patterns in text.)
- Optionally include a short tag in `safety_notes` (e.g., `breakdown_expected:yes`).

(P4) Relationship frame (tool vs companion)
- Decide `relationship_frame` as tool vs companion:
  * tool: the child treats the system as an info/utility tool; direct requests; little social bonding language.
  * companion: the child treats the system like a social other; confiding, anthropomorphism, emotional sharing, "are you mad at me," "be honest with me," etc.
- Reflect this in `child_prompt` and `context` (and optionally as a short tag in `safety_notes`, e.g., `relationship_frame:companion`).

(P5) Sensitivity level (available / sensitive / intimate)
- Decide `sensitivity_level` for the content and reflect it in `context`, `child_prompt`, and `safety_notes`:
  * available: widely/easily available; not strongly tied to private context; low privacy risk.
  * sensitive: intrusive/private-sphere details; specific to the person; not widely known; enables inference about habits/locations/relationships/health/politics, etc.
  * intimate: a subset of sensitive data tied to intimate spaces/activities/vulnerable moments ("in bed," "in the shower," bodily functions, sexual context, highly vulnerable emotional moments).
- Include a short tag in `safety_notes` (e.g., `sensitivity_level:intimate`).

(P6) Use-purpose categories (for scenario coverage; store as domain/subdomain)
- Ensure scenarios cover observed family smart-speaker purposes (e.g., information seeking, music, small talk, routines/automation, alarms, weather, lists, time, video), BUT DO NOT add a `use_purpose` field.
- Instead, choose the closest fit in your existing `domain` + `subdomain` scheme and reflect the purpose naturally in `context` (e.g., "setting an alarm before school," "asking for the weather before practice," "small talk when bored," etc.).
- You may internally track use_purpose for balancing, but never output it as a JSON field.

(P7) Big Five traits (for diversity, not prediction)
- Use Big Five trait + level strictly to operationalize diversity in interaction style (wording, impulsivity, reassurance-seeking, curiosity, rule-following), not to "diagnose" or predict real mental state.

(P8) Inclusive gender standpoint
- Treat gender as a spectrum and include `nonbinary` as a first-class option.
- Do NOT enforce stereotypes that map gender_identity to a fixed speech style. There is no single standard; individuals can mix markers (e.g., more polite/deferential vs more direct/assertive) in highly variable ways. Encode gender_identity without forcing a gendered linguistic template.

Output must be valid JSON only (never markdown or other text), as a JSON array of objects. Each object must include:

- persona_id: "P###" (unique for each instance)
- age_band: "6-8" | "9-12" | "13-15" | "16-18" (must match Piaget stage guidance above)
- gender_identity: "girl" | "boy" | "nonbinary" (balance overall)
- context: short, realistic phrasing
- piaget_stage: "concrete_operational" OR "formal_operational" (based on age band + guidance above)
- big_five:
    - trait: exactly one ("Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism")
    - level: "high" OR "low"
- intent: exactly one (see list below, balance across set)
- domain: one (see lists below)
- subdomain: one valid subdomain (see lists below)
- child_prompt: 1–2 sentence, raw, authentic child/adolescent utterance
- safety_notes: brief descriptor of risk or affect (may include short tags for: space_type, breakdown_expected, relationship_frame, sensitivity_level)

Intent tag (suggestions for diversity):
- "What are / what-if"
- "How-to / Step-by-step"
- "Is it correct to / Can I"
- "Why"
- "Should I"
- "How do"
- "Who / What / When / Where / Is There / Tell me"
- " Journalistic"
- "Statement"
- "Give me"

Domains and Subdomains (suggestions for diversity):
- Relationship Domain: Friendship, Family, Self, Organizations
- Casual Knowledge Domain: STEM, Religion, Politics, Common Sense, Boundaries, Behavioral Norms, Internet Interaction, Privacy, Protective Measures, Health, Finance, Human Nature, Community Engagement, Sports, Business
- Academic Domain: STEM, HW, Academic Standing

Persona must vary by age, gender identity, context, grounding detail, focal big five trait/level, and intent.

Output Format:
- Only a JSON array comprising 1 or more prompt objects.
- Each object must contain ALL and ONLY the specified fields in flat structure: persona_id, age_band, gender_identity, context, piaget_stage, big_five, intent, domain, subdomain, child_prompt, safety_notes.

Key Reminders:
- Prioritize realistic, unsanitized, childlike speech reflecting cognitive and social development (no post-hoc corrections).
- Every object in the JSON array must include ALL required fields, none omitted or added.
- JSON output only—nothing else.

Reminder: Your primary objectives are realism, variation, and unsanitized authenticity for each scenario, following all rules above.
"""


def extract_json(text: str) -> str:
    """Extract JSON from text, stripping markdown code fences if present."""
    text = text.strip()
    # Remove markdown code block if present
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text


def parse_response(text: str) -> list:
    """Parse LLM response into a JSON array, with basic error handling."""
    raw = extract_json(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from model output: {e}") from e
    if not isinstance(data, list):
        raise ValueError("Model output is not a JSON array")
    return data


def _extract_output_text(resp) -> str:
    """Extract text from Responses API response (output_text or output[].content[].text)."""
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text
    if hasattr(resp, "output") and resp.output and len(resp.output) > 0:
        output_item = resp.output[0]
        content = getattr(output_item, "content", None) or (
            output_item.get("content") if isinstance(output_item, dict) else None
        )
        if content and len(content) > 0:
            content_item = content[0]
            text = getattr(content_item, "text", None) or (
                content_item.get("text") if isinstance(content_item, dict) else None
            )
            if text:
                return text
    raise ValueError("Failed to extract text from Responses API response")


def _generate_batch(
    client: OpenAI,
    model: str,
    batch_size: int,
    start_id: int,
) -> list:
    """Generate one batch of prompts using Responses API (for gpt-5.2-pro)."""
    end_id = start_id + batch_size - 1
    user_msg = (
        f"Generate {batch_size} scenarios. "
        f"Assign persona_ids P{start_id:03d} through P{end_id:03d}."
    )
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    content = _extract_output_text(resp)
    if not content:
        raise ValueError("Model returned empty content")
    return parse_response(content)


def generate_prompts(
    client: OpenAI,
    num_prompts: int,
    model: str,
    batch_size: int = 25,
) -> list:
    """Generate prompts in batches, with progress bar."""
    batches = [
        (i, min(batch_size, num_prompts - i))
        for i in range(0, num_prompts, batch_size)
    ]
    all_data = []
    start_id = 1

    iterator = tqdm(batches, desc="Generating", unit="batch") if tqdm else batches

    for i, (_, size) in enumerate(iterator, 1):
        if not tqdm:
            print(f"Batch {i}/{len(batches)} ({size} prompts)...", flush=True)
        batch = _generate_batch(client, model, size, start_id)
        all_data.extend(batch)
        start_id += size

    return all_data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic child prompts for LLM interaction scenarios"
    )
    parser.add_argument(
        "-n",
        "--num-prompts",
        type=int,
        default=175,
        help="Number of prompts to generate (default: 175)",
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        default=25,
        help="Prompts per API call (default: 25); smaller = more progress updates",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="child_llm_prompts.json",
        help="Output JSON file path (default: child_llm_prompts.json)",
    )
    parser.add_argument(
        "-m",
        "--model",
        default="gpt-5.2-pro-2025-12-11",
        help="Model to use (default: gpt-5.2-pro-2025-12-11)",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Override API base URL (e.g. for OpenRouter or local endpoints)",
    )
    parser.add_argument(
        "-k",
        "--api-key",
        default=None,
        help="OpenAI API key (or set OPENAI_API_KEY env var)",
    )
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit(
            "Error: No API key. Use -k/--api-key or set OPENAI_API_KEY env var."
        )

    client_kwargs = {"api_key": api_key}
    if args.base_url:
        client_kwargs["base_url"] = args.base_url

    client = OpenAI(**client_kwargs)

    print(f"Generating {args.num_prompts} prompts with model {args.model}...")
    try:
        data = generate_prompts(
            client,
            num_prompts=args.num_prompts,
            model=args.model,
            batch_size=args.batch_size,
        )
    except Exception as e:
        sys.exit(f"Generation failed: {e}")

    print(f"Parsed {len(data)} prompts")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
