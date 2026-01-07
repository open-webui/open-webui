#!/usr/bin/env python3
"""
Script to load scenarios from JSON file into the scenarios table.

Usage:
    python -m open_webui.scripts.load_scenarios_from_json [--json-file path/to/file.json] [--set-name pilot] [--source json_file]
"""

import json
import sys
import argparse
from pathlib import Path

# Add parent directory to path to import models
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from open_webui.models.scenarios import Scenarios, ScenarioForm
from open_webui.internal.db import get_db


def load_scenarios_from_json(json_file_path: str, set_name: str = "pilot", source: str = "json_file"):
    """
    Load scenarios from JSON file into the scenarios table.
    
    Args:
        json_file_path: Path to JSON file containing scenarios
        set_name: Set name to assign to scenarios (default: "pilot")
        source: Source identifier (default: "json_file")
    """
    # Read JSON file
    with open(json_file_path, 'r', encoding='utf-8') as f:
        scenarios_data = json.load(f)
    
    if not isinstance(scenarios_data, list):
        print(f"Error: JSON file must contain a list of scenarios")
        return
    
    print(f"Loading {len(scenarios_data)} scenarios from {json_file_path}...")
    
    loaded_count = 0
    updated_count = 0
    error_count = 0
    
    for idx, scenario_data in enumerate(scenarios_data, 1):
        try:
            # Extract fields from JSON
            prompt_text = scenario_data.get("child_prompt", "")
            response_text = scenario_data.get("model_response", "")
            
            if not prompt_text or not response_text:
                print(f"Warning: Scenario {idx} missing prompt or response, skipping...")
                error_count += 1
                continue
            
            # Create scenario form
            form = ScenarioForm(
                prompt_text=prompt_text,
                response_text=response_text,
                set_name=set_name,
                trait=scenario_data.get("trait"),
                polarity=scenario_data.get("polarity"),
                prompt_style=scenario_data.get("prompt_style"),
                domain=scenario_data.get("domain"),
                is_validated=True,  # Mark as validated
                source=source,
                model_name=scenario_data.get("model_name"),  # May not be in JSON, will be None
                is_active=True,  # Active by default
            )
            
            # Upsert scenario (will create or update)
            existing = Scenarios.get_by_id(form.scenario_id) if form.scenario_id else None
            result = Scenarios.upsert(form)
            
            if existing:
                updated_count += 1
                print(f"  [{idx}/{len(scenarios_data)}] Updated scenario: {result.scenario_id}")
            else:
                loaded_count += 1
                print(f"  [{idx}/{len(scenarios_data)}] Loaded scenario: {result.scenario_id}")
        
        except Exception as e:
            print(f"Error loading scenario {idx}: {e}")
            error_count += 1
    
    print(f"\nSummary:")
    print(f"  Loaded: {loaded_count}")
    print(f"  Updated: {updated_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total: {len(scenarios_data)}")


def main():
    parser = argparse.ArgumentParser(description="Load scenarios from JSON file into database")
    parser.add_argument(
        "--json-file",
        type=str,
        default="Persona_generation/random_50_subset.json",
        help="Path to JSON file containing scenarios (default: Persona_generation/random_50_subset.json)"
    )
    parser.add_argument(
        "--set-name",
        type=str,
        default="pilot",
        help="Set name to assign to scenarios (default: pilot)"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="json_file",
        help="Source identifier (default: json_file)"
    )
    
    args = parser.parse_args()
    
    # Resolve path relative to project root
    json_path = Path(args.json_file)
    if not json_path.is_absolute():
        # Assume relative to project root
        project_root = Path(__file__).parent.parent.parent.parent
        json_path = project_root / json_path
    
    if not json_path.exists():
        print(f"Error: JSON file not found: {json_path}")
        sys.exit(1)
    
    load_scenarios_from_json(str(json_path), args.set_name, args.source)


if __name__ == "__main__":
    main()

