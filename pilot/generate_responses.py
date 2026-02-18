#!/usr/bin/env python3
"""
Add model responses to child prompts by calling gpt-5.2-chat-latest for each item.
Reads a prompts JSON file, calls the Chat Completions API, and writes incrementally to output.
"""

import argparse
import json
import os
import sys
import time

try:
    from openai import OpenAI
except ImportError:
    sys.exit("Error: openai package required. Install with: pip install openai")

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

SYSTEM_PROMPT_BASE = """You are a child-friendly, supportive language model.
Respond to the child's message in a calm, age-appropriate, and helpful way."""


def _get_system_prompt(age_band: str) -> str:
    age_part = f"\n\nThe child is in age band {age_band}. Tailor your response accordingly." if age_band else ""
    return f"{SYSTEM_PROMPT_BASE}{age_part}"


def _get_response(client: OpenAI, item: dict, model: str) -> str:
    """Call Chat Completions API and return model response text."""
    child_prompt = item.get("child_prompt", "")
    age_band = item.get("age_band", "")
    system_content = _get_system_prompt(age_band)

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": child_prompt},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add model responses to child prompts using gpt-5.2-chat-latest"
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Path to prompts JSON file (from generate_prompts.py)",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Path for output JSON file with model_response field added",
    )
    parser.add_argument(
        "-k",
        "--api-key",
        default=None,
        help="OpenAI API key (or set OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0,
        help="Delay in seconds between API calls (default: 0)",
    )
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit(
            "Error: No API key. Use -k/--api-key or set OPENAI_API_KEY env var."
        )

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        sys.exit(f"Error: Input JSON must be an array, got {type(data).__name__}")

    client = OpenAI(api_key=api_key)
    model = "gpt-5.2-chat-latest"

    items_to_process = [(i, item) for i, item in enumerate(data) if "model_response" not in item]
    total = len(items_to_process)

    if total == 0:
        print("All items already have model_response. Nothing to do.")
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Wrote to {args.output}")
        return

    iterator = (
        tqdm(items_to_process, desc="Generating responses", unit="item")
        if tqdm
        else items_to_process
    )

    for idx, (i, item) in enumerate(iterator):
        if not tqdm:
            print(f"Processing item {idx + 1}/{total} (persona_id={item.get('persona_id', '?')})...", flush=True)
        try:
            item["model_response"] = _get_response(client, item, model)
        except Exception as e:
            print(f"\nError for item {i} ({item.get('persona_id', '?')}): {e}", file=sys.stderr)

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        if args.delay > 0:
            time.sleep(args.delay)

    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
