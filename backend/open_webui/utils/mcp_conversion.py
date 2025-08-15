# MCP conversion utilities

from typing import Dict


def convert_mcp_tool_to_openai_spec(mcp_spec: dict, server_name: str) -> dict:
    name = mcp_spec.get("name") or mcp_spec.get("id") or "mcp_tool"
    description = mcp_spec.get("description") or f"MCP tool {name} from {server_name}"

    input_schema: Dict = mcp_spec.get("inputSchema") or {}
    schema_type = input_schema.get("type", "object")

    properties = input_schema.get("properties") or {}
    required = input_schema.get("required") or []

    openai_properties: Dict[str, dict] = {}
    for key, val in properties.items():
        if not isinstance(val, dict):
            continue
        # Ensure required OpenAI schema fields
        prop_type = val.get("type") or "string"
        openai_properties[key] = {
            "type": prop_type,
            **({"description": val.get("description")} if val.get("description") else {}),
        }
        # Pass through enum and items if present
        if "enum" in val:
            openai_properties[key]["enum"] = val["enum"]
        if prop_type == "array" and "items" in val:
            openai_properties[key]["items"] = val["items"]

    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": schema_type,
            "properties": openai_properties,
            "required": required,
        },
    } 