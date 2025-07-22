I've located the `DEFAULT_TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE` in `backend/open_webui/config.py`. Here is the content of the template:

```
Available Tools: {{TOOLS}}

Your task is to choose and return the correct tool(s) from the list of available tools based on the query. Follow these guidelines:

- Return only the JSON object, without any additional text or explanation.

- If no tools match the query, return an empty array: 
   {
     "tool_calls": []
   }

- If one or more tools match the query, construct a JSON response containing a "tool_calls" array with objects that include:
   - "name": The tool's name.
   - "parameters": A dictionary of required parameters and their corresponding values.

The format for the JSON response is strictly:
{
  "tool_calls": [
    {"name": "toolName1", "parameters": {"key1": "value1"}},
    {"name": "toolName2", "parameters": {"key2": "value2"}}
  ]
}
```

In the `chat_completion_tools_handler` function within `backend/open_webui/utils/middleware.py`, this template is passed to the `tools_function_calling_generation_template` function. This function then replaces the `{{TOOLS}}` placeholder with a JSON string containing the specifications of all available tools.

So, the final prompt sent to the model will look like the template above, but with `{{TOOLS}}` replaced by a JSON array of tool specifications. For example:

```json
[
  {
    "name": "web_search",
    "description": "Searches the web for the given query.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "The search query."
        }
      },
      "required": ["query"]
    }
  },
  {
    "name": "image_generation",
    "description": "Generates an image based on the given prompt.",
    "parameters": {
      "type": "object",
      "properties": {
        "prompt": {
          "type": "string",
          "description": "The prompt for image generation."
        }
      },
      "required": ["prompt"]
    }
  }
]
```

This combined text forms the complete prompt that the model uses to decide which tool to use.