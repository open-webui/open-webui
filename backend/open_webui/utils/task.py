import logging
import math
import re
from datetime import datetime
from typing import Optional, Any
import uuid


from open_webui.utils.misc import get_last_user_message, get_messages_content

from open_webui.env import SRC_LOG_LEVELS
from open_webui.config import DEFAULT_RAG_TEMPLATE


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def get_task_model_id(
    default_model_id: str, task_model: str, task_model_external: str, models
) -> str:
    # Set the task model
    task_model_id = default_model_id
    # Check if the user has a custom task model and use that model
    if models[task_model_id].get("connection_type") == "local":
        if task_model and task_model in models:
            task_model_id = task_model
    else:
        if task_model_external and task_model_external in models:
            task_model_id = task_model_external

    return task_model_id


def prompt_variables_template(template: str, variables: dict[str, str]) -> str:
    for variable, value in variables.items():
        template = template.replace(variable, value)
    return template


def _get_user_variables(user: Optional[Any] = None) -> dict:
    """
    Extract user variables for template substitution.

    Args:
        user: User object or dict

    Returns:
        Dict of user variables
    """
    USER_VARIABLES = {}

    if user:
        if hasattr(user, "model_dump"):
            user = user.model_dump()

        if isinstance(user, dict):
            user_info = user.get("info", {}) or {}
            birth_date = user.get("date_of_birth")
            age = None

            if birth_date:
                try:
                    # If birth_date is str, convert to datetime
                    if isinstance(birth_date, str):
                        birth_date = datetime.strptime(birth_date, "%Y-%m-%d")

                    today = datetime.now()
                    age = (
                        today.year
                        - birth_date.year
                        - (
                            (today.month, today.day)
                            < (birth_date.month, birth_date.day)
                        )
                    )
                except Exception:
                    pass

            USER_VARIABLES = {
                "name": str(user.get("name")),
                "location": str(user_info.get("location")),
                "bio": str(user.get("bio")),
                "gender": str(user.get("gender")),
                "birth_date": str(birth_date),
                "age": str(age),
            }

    return USER_VARIABLES


def _resolve_basic_variables(template: str, user: Optional[Any] = None) -> str:
    """
    Resolve basic template variables (dates, user info) but NOT nested prompts.
    This is used internally when resolving prompt content to avoid circular dependencies.

    Args:
        template: The template string to resolve
        user: User object for resolving user-specific variables

    Returns:
        Template with basic variables resolved
    """
    USER_VARIABLES = _get_user_variables(user)

    # Get the current date
    current_date = datetime.now()

    # Format the date to YYYY-MM-DD
    formatted_date = current_date.strftime("%Y-%m-%d")
    formatted_time = current_date.strftime("%I:%M:%S %p")
    formatted_weekday = current_date.strftime("%A")

    template = template.replace("{{CURRENT_DATE}}", formatted_date)
    template = template.replace("{{CURRENT_TIME}}", formatted_time)
    template = template.replace(
        "{{CURRENT_DATETIME}}", f"{formatted_date} {formatted_time}"
    )
    template = template.replace("{{CURRENT_WEEKDAY}}", formatted_weekday)

    template = template.replace("{{USER_NAME}}", USER_VARIABLES.get("name", "Unknown"))
    template = template.replace("{{USER_BIO}}", USER_VARIABLES.get("bio", "Unknown"))
    template = template.replace(
        "{{USER_GENDER}}", USER_VARIABLES.get("gender", "Unknown")
    )
    template = template.replace(
        "{{USER_BIRTH_DATE}}", USER_VARIABLES.get("birth_date", "Unknown")
    )
    template = template.replace(
        "{{USER_AGE}}", str(USER_VARIABLES.get("age", "Unknown"))
    )
    template = template.replace(
        "{{USER_LOCATION}}", USER_VARIABLES.get("location", "Unknown")
    )

    return template


def replace_prompts_variable(
    template: str,
    prompts: Optional[list[dict]] = None,
    visited_prompts: Optional[set[str]] = None,
    user: Optional[Any] = None,
    depth: int = 0,
    max_depth: int = 50,
) -> str:
    """
    Replace {{PROMPTS.prompt_name}} variables with prompt content, recursively.
    The prompt content itself is resolved for ALL variables including nested {{PROMPTS.*}}.
    Circular dependencies are prevented by tracking visited prompts.

    Args:
        template: The template string containing prompt variables
        prompts: List of prompt objects with 'command' and 'content' fields
        visited_prompts: Set of prompt commands already visited (prevents circular references)
        user: User object for resolving user-specific variables in prompt content
        depth: Current recursion depth
        max_depth: Maximum recursion depth to prevent infinite loops (default: 50)

    Returns:
        Template with prompt variables replaced recursively
    """
    if not prompts:
        return template

    if visited_prompts is None:
        visited_prompts = set()

    # Check max depth to prevent excessive recursion
    if depth >= max_depth:
        log.warning(
            f"Maximum recursion depth ({max_depth}) reached for prompt variable resolution"
        )
        return template

    # Build a mapping of prompt names to their content
    prompt_map = {}
    for prompt in prompts:
        # Remove leading '/' from command if present
        command = prompt.get("command", "").lstrip("/")
        content = prompt.get("content", "")
        if command:
            prompt_map[command] = content

    # Pattern to match {{PROMPTS.prompt_name}}
    pattern = r"{{PROMPTS\.([a-zA-Z0-9-_]+)}}"

    def replacement_function(match):
        prompt_name = match.group(1)

        # Prevent circular dependencies
        if prompt_name in visited_prompts:
            raise ValueError(f"Circular reference detected for prompt '{prompt_name}'")

        # Get the prompt content
        content = prompt_map.get(prompt_name)
        if content is not None:
            # Add this prompt to visited set for this branch of recursion
            new_visited = visited_prompts | {prompt_name}

            # First resolve basic variables (dates, user info)
            resolved_content = _resolve_basic_variables(content, user)

            # Then recursively resolve any nested {{PROMPTS.*}} references
            resolved_content = replace_prompts_variable(
                resolved_content,
                prompts=prompts,
                visited_prompts=new_visited,
                user=user,
                depth=depth + 1,
                max_depth=max_depth,
            )

            return resolved_content
        else:
            # If prompt not found, leave the variable unchanged
            log.debug(f"Prompt variable not found: {{{{PROMPTS.{prompt_name}}}}}")
            return match.group(0)

    template = re.sub(pattern, replacement_function, template)
    return template


def prompt_template(
    template: str,
    user: Optional[Any] = None,
    prompts: Optional[list[dict]] = None,
    current_prompt_command: Optional[
        str
    ] = None,  # Deprecated but kept for backward compatibility
) -> str:
    # Resolve basic variables (dates, user info)
    template = _resolve_basic_variables(template, user)

    # Replace {{PROMPTS.prompt_name}} variables with nested resolution
    # Access control is handled by the prompts list - it only contains prompts the user can access
    template = replace_prompts_variable(
        template,
        prompts=prompts,
        visited_prompts=None,  # Start with empty visited set
        user=user,
        depth=0,
        max_depth=50,
    )

    return template


def replace_prompt_variable(template: str, prompt: str) -> str:
    def replacement_function(match):
        full_match = match.group(
            0
        ).lower()  # Normalize to lowercase for consistent handling
        start_length = match.group(1)
        end_length = match.group(2)
        middle_length = match.group(3)

        if full_match == "{{prompt}}":
            return prompt
        elif start_length is not None:
            return prompt[: int(start_length)]
        elif end_length is not None:
            return prompt[-int(end_length) :]
        elif middle_length is not None:
            middle_length = int(middle_length)
            if len(prompt) <= middle_length:
                return prompt
            start = prompt[: math.ceil(middle_length / 2)]
            end = prompt[-math.floor(middle_length / 2) :]
            return f"{start}...{end}"
        return ""

    # Updated regex pattern to make it case-insensitive with the `(?i)` flag
    pattern = r"(?i){{prompt}}|{{prompt:start:(\d+)}}|{{prompt:end:(\d+)}}|{{prompt:middletruncate:(\d+)}}"
    template = re.sub(pattern, replacement_function, template)
    return template


def replace_messages_variable(
    template: str, messages: Optional[list[dict]] = None
) -> str:
    def replacement_function(match):
        full_match = match.group(0)
        start_length = match.group(1)
        end_length = match.group(2)
        middle_length = match.group(3)
        # If messages is None, handle it as an empty list
        if messages is None:
            return ""

        # Process messages based on the number of messages required
        if full_match == "{{MESSAGES}}":
            return get_messages_content(messages)
        elif start_length is not None:
            return get_messages_content(messages[: int(start_length)])
        elif end_length is not None:
            return get_messages_content(messages[-int(end_length) :])
        elif middle_length is not None:
            mid = int(middle_length)

            if len(messages) <= mid:
                return get_messages_content(messages)
            # Handle middle truncation: split to get start and end portions of the messages list
            half = mid // 2
            start_msgs = messages[:half]
            end_msgs = messages[-half:] if mid % 2 == 0 else messages[-(half + 1) :]
            formatted_start = get_messages_content(start_msgs)
            formatted_end = get_messages_content(end_msgs)
            return f"{formatted_start}\n{formatted_end}"
        return ""

    template = re.sub(
        r"{{MESSAGES}}|{{MESSAGES:START:(\d+)}}|{{MESSAGES:END:(\d+)}}|{{MESSAGES:MIDDLETRUNCATE:(\d+)}}",
        replacement_function,
        template,
    )

    return template


# {{prompt:middletruncate:8000}}


def rag_template(template: str, context: str, query: str):
    if template.strip() == "":
        template = DEFAULT_RAG_TEMPLATE

    template = prompt_template(template)

    if "[context]" not in template and "{{CONTEXT}}" not in template:
        log.debug(
            "WARNING: The RAG template does not contain the '[context]' or '{{CONTEXT}}' placeholder."
        )

    if "<context>" in context and "</context>" in context:
        log.debug(
            "WARNING: Potential prompt injection attack: the RAG "
            "context contains '<context>' and '</context>'. This might be "
            "nothing, or the user might be trying to hack something."
        )

    query_placeholders = []
    if "[query]" in context:
        query_placeholder = "{{QUERY" + str(uuid.uuid4()) + "}}"
        template = template.replace("[query]", query_placeholder)
        query_placeholders.append(query_placeholder)

    if "{{QUERY}}" in context:
        query_placeholder = "{{QUERY" + str(uuid.uuid4()) + "}}"
        template = template.replace("{{QUERY}}", query_placeholder)
        query_placeholders.append(query_placeholder)

    template = template.replace("[context]", context)
    template = template.replace("{{CONTEXT}}", context)
    template = template.replace("[query]", query)
    template = template.replace("{{QUERY}}", query)

    for query_placeholder in query_placeholders:
        template = template.replace(query_placeholder, query)

    return template


def title_generation_template(
    template: str,
    messages: list[dict],
    user: Optional[Any] = None,
    prompts: Optional[list[dict]] = None,
) -> str:

    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = prompt_template(template, user, prompts)

    return template


def follow_up_generation_template(
    template: str,
    messages: list[dict],
    user: Optional[Any] = None,
    prompts: Optional[list[dict]] = None,
) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = prompt_template(template, user, prompts)
    return template


def tags_generation_template(
    template: str,
    messages: list[dict],
    user: Optional[Any] = None,
    prompts: Optional[list[dict]] = None,
) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = prompt_template(template, user, prompts)
    return template


def image_prompt_generation_template(
    template: str,
    messages: list[dict],
    user: Optional[Any] = None,
    prompts: Optional[list[dict]] = None,
) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = prompt_template(template, user, prompts)
    return template


def emoji_generation_template(
    template: str,
    prompt: str,
    user: Optional[Any] = None,
    prompts: Optional[list[dict]] = None,
) -> str:
    template = replace_prompt_variable(template, prompt)
    template = prompt_template(template, user, prompts)

    return template


def autocomplete_generation_template(
    template: str,
    prompt: str,
    messages: Optional[list[dict]] = None,
    type: Optional[str] = None,
    user: Optional[Any] = None,
    prompts: Optional[list[dict]] = None,
) -> str:
    template = template.replace("{{TYPE}}", type if type else "")
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = prompt_template(template, user, prompts)
    return template


def query_generation_template(
    template: str,
    messages: list[dict],
    user: Optional[Any] = None,
    prompts: Optional[list[dict]] = None,
) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = prompt_template(template, user, prompts)
    return template


def moa_response_generation_template(
    template: str, prompt: str, responses: list[str]
) -> str:
    def replacement_function(match):
        full_match = match.group(0)
        start_length = match.group(1)
        end_length = match.group(2)
        middle_length = match.group(3)

        if full_match == "{{prompt}}":
            return prompt
        elif start_length is not None:
            return prompt[: int(start_length)]
        elif end_length is not None:
            return prompt[-int(end_length) :]
        elif middle_length is not None:
            middle_length = int(middle_length)
            if len(prompt) <= middle_length:
                return prompt
            start = prompt[: math.ceil(middle_length / 2)]
            end = prompt[-math.floor(middle_length / 2) :]
            return f"{start}...{end}"
        return ""

    template = re.sub(
        r"{{prompt}}|{{prompt:start:(\d+)}}|{{prompt:end:(\d+)}}|{{prompt:middletruncate:(\d+)}}",
        replacement_function,
        template,
    )

    responses = [f'"""{response}"""' for response in responses]
    responses = "\n\n".join(responses)

    template = template.replace("{{responses}}", responses)
    return template


def tools_function_calling_generation_template(template: str, tools_specs: str) -> str:
    template = template.replace("{{TOOLS}}", tools_specs)
    return template


def validate_prompt_references(
    prompt_command: str,
    prompt_content: str,
    all_prompts: list[dict],
    accessible_prompts: Optional[list[dict]] = None,
    max_depth_warning: int = 15,
    max_depth_error: int = 50,
) -> dict:
    """
    Validate {{PROMPTS.*}} references in a prompt before saving.

    Args:
        prompt_command: The command of the prompt being validated (without leading /)
        prompt_content: The content to validate
        all_prompts: List of all prompts in the system (for admins) or user's accessible prompts
        accessible_prompts: List of prompts the user has access to (None for admins)
        max_depth_warning: Depth threshold for warnings
        max_depth_error: Depth threshold for errors

    Returns:
        dict with 'errors' (list), 'warnings' (list), and 'valid' (bool)
    """
    errors = []
    warnings = []

    # Extract all {{PROMPTS.command}} references
    pattern = r"{{PROMPTS\.([a-zA-Z0-9-_]+)}}"
    references = re.findall(pattern, prompt_content)

    if not references:
        return {"valid": True, "errors": [], "warnings": []}

    # Build prompt map
    prompt_map = {}
    for p in all_prompts:
        cmd = p.get("command", "").lstrip("/")
        if cmd:
            prompt_map[cmd] = p.get("content", "")

    # Build accessible prompt set (if applicable)
    accessible_set = None
    if accessible_prompts is not None:
        accessible_set = set(
            p.get("command", "").lstrip("/") for p in accessible_prompts
        )

    # Check for non-existent or inaccessible prompts
    for ref in references:
        if ref not in prompt_map:
            errors.append(f"Referenced prompt '/{ref}' does not exist")
        elif accessible_set is not None and ref not in accessible_set:
            errors.append(f"You don't have access to prompt '/{ref}'")

    # If there are errors, don't proceed with circular dependency check
    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}

    # Check for circular dependencies and max depth
    def check_circular_and_depth(
        current_cmd: str, visited: set[str], depth: int
    ) -> tuple[bool, int]:
        """
        Returns (has_circular, max_depth_reached)
        """
        if current_cmd in visited:
            return True, depth

        if depth >= max_depth_error:
            return False, depth

        content = prompt_map.get(current_cmd, "")
        nested_refs = re.findall(pattern, content)

        if not nested_refs:
            return False, depth

        new_visited = visited | {current_cmd}
        max_depth_found = depth

        for ref in nested_refs:
            if ref in prompt_map:
                has_circ, nested_depth = check_circular_and_depth(
                    ref, new_visited, depth + 1
                )
                if has_circ:
                    return True, nested_depth
                max_depth_found = max(max_depth_found, nested_depth)

        return False, max_depth_found

    # Check starting from the current prompt
    has_circular, max_depth = check_circular_and_depth(prompt_command, set(), 0)

    if has_circular:
        errors.append(
            "Circular dependency detected: this prompt references itself through other prompts"
        )

    # Check depth warnings
    if max_depth >= max_depth_error:
        errors.append(
            f"Nesting depth ({max_depth}) exceeds maximum allowed ({max_depth_error})"
        )
    elif max_depth >= max_depth_warning:
        warnings.append(
            f"Nesting depth ({max_depth}) is high. Consider simplifying your prompt references."
        )

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}
