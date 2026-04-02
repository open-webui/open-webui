import logging
import math
import re
from datetime import datetime
from typing import Optional, Any
import uuid


from open_webui.utils.misc import get_last_user_message, get_messages_content

from open_webui.config import DEFAULT_RAG_TEMPLATE

log = logging.getLogger(__name__)


# Let the right tool be given for the work at hand,
# not the one that flatters, but the one that serves.
def get_task_model_id(default_model_id: str, task_model: str, task_model_external: str, models) -> str:
    # Set the task model
    task_model_id = default_model_id
    # Check if the user has a custom task model and use that model
    if models.get(task_model_id, {}).get('connection_type') == 'local':
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


def prompt_template(template: str, user: Optional[Any] = None) -> str:
    USER_VARIABLES = {}

    if user:
        if hasattr(user, 'model_dump'):
            user = user.model_dump()

        if isinstance(user, dict):
            user_info = user.get('info', {}) or {}
            birth_date = user.get('date_of_birth')
            age = None

            if birth_date:
                try:
                    # If birth_date is str, convert to datetime
                    if isinstance(birth_date, str):
                        birth_date = datetime.strptime(birth_date, '%Y-%m-%d')

                    today = datetime.now()
                    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                except Exception as e:
                    pass

            USER_VARIABLES = {
                'name': str(user.get('name')),
                'email': str(user.get('email')),
                'location': str(user_info.get('location')),
                'bio': str(user.get('bio')),
                'gender': str(user.get('gender')),
                'birth_date': str(birth_date),
                'age': str(age),
            }

    # Get the current date
    current_date = datetime.now()

    # Format the date to YYYY-MM-DD
    formatted_date = current_date.strftime('%Y-%m-%d')
    formatted_time = current_date.strftime('%I:%M:%S %p')
    formatted_weekday = current_date.strftime('%A')

    template = template.replace('{{CURRENT_DATE}}', formatted_date)
    template = template.replace('{{CURRENT_TIME}}', formatted_time)
    template = template.replace('{{CURRENT_DATETIME}}', f'{formatted_date} {formatted_time}')
    template = template.replace('{{CURRENT_WEEKDAY}}', formatted_weekday)

    template = template.replace('{{USER_NAME}}', USER_VARIABLES.get('name', 'Unknown'))
    template = template.replace('{{USER_EMAIL}}', USER_VARIABLES.get('email', 'Unknown'))
    template = template.replace('{{USER_BIO}}', USER_VARIABLES.get('bio', 'Unknown'))
    template = template.replace('{{USER_GENDER}}', USER_VARIABLES.get('gender', 'Unknown'))
    template = template.replace('{{USER_BIRTH_DATE}}', USER_VARIABLES.get('birth_date', 'Unknown'))
    template = template.replace('{{USER_AGE}}', str(USER_VARIABLES.get('age', 'Unknown')))
    template = template.replace('{{USER_LOCATION}}', USER_VARIABLES.get('location', 'Unknown'))

    return template


def replace_prompt_variable(template: str, prompt: str) -> str:
    def replacement_function(match):
        full_match = match.group(0).lower()  # Normalize to lowercase for consistent handling
        start_length = match.group(1)
        end_length = match.group(2)
        middle_length = match.group(3)

        if full_match == '{{prompt}}':
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
            return f'{start}...{end}'
        return ''

    # Updated regex pattern to make it case-insensitive with the `(?i)` flag
    pattern = r'(?i){{prompt}}|{{prompt:start:(\d+)}}|{{prompt:end:(\d+)}}|{{prompt:middletruncate:(\d+)}}'
    template = re.sub(pattern, replacement_function, template)
    return template


def truncate_content(content: str, max_chars: int, mode: str = 'middletruncate') -> str:
    """Truncate a string to max_chars using the specified mode.

    Modes:
        - middletruncate: keep beginning and end, join with '...'
        - start: keep first max_chars characters
        - end: keep last max_chars characters
    """
    if not content or len(content) <= max_chars:
        return content

    if mode == 'start':
        return content[:max_chars]
    elif mode == 'end':
        return content[-max_chars:]
    else:  # middletruncate
        half = max_chars // 2
        return f'{content[:half]}...{content[-(max_chars - half) :]}'


def apply_content_filter(messages: list[dict], filter_str: str) -> list[dict]:
    """Apply a content filter to each message's content.

    filter_str is like 'middletruncate:500', 'start:200', or 'end:200'.
    Returns a new list with truncated content (original messages are not mutated).
    """
    parts = filter_str.split(':')
    if len(parts) != 2:
        return messages

    mode = parts[0].lower()
    try:
        max_chars = int(parts[1])
    except ValueError:
        return messages

    if mode not in ('middletruncate', 'start', 'end'):
        return messages

    result = []
    for msg in messages:
        new_msg = dict(msg)
        if isinstance(new_msg.get('content'), str):
            new_msg['content'] = truncate_content(new_msg['content'], max_chars, mode)
        elif isinstance(new_msg.get('content'), list):
            new_content = []
            for item in new_msg['content']:
                if isinstance(item, dict) and item.get('type') == 'text':
                    new_item = dict(item)
                    new_item['text'] = truncate_content(item.get('text', ''), max_chars, mode)
                    new_content.append(new_item)
                else:
                    new_content.append(item)
            new_msg['content'] = new_content
        result.append(new_msg)
    return result


def replace_messages_variable(template: str, messages: Optional[list[dict]] = None) -> str:
    def replacement_function(match):
        # Groups: (1) filter for bare MESSAGES
        #         (2) START count, (3) filter for START
        #         (4) END count,   (5) filter for END
        #         (6) MIDDLE count,(7) filter for MIDDLE
        bare_filter = match.group(1)
        start_length = match.group(2)
        start_filter = match.group(3)
        end_length = match.group(4)
        end_filter = match.group(5)
        middle_length = match.group(6)
        middle_filter = match.group(7)

        # If messages is None, handle it as an empty list
        if messages is None:
            return ''

        # Select messages based on the variant
        if start_length is not None:
            selected = messages[: int(start_length)]
            content_filter = start_filter
        elif end_length is not None:
            selected = messages[-int(end_length) :]
            content_filter = end_filter
        elif middle_length is not None:
            mid = int(middle_length)
            if len(messages) <= mid:
                selected = messages
            else:
                half = mid // 2
                start_msgs = messages[:half]
                end_msgs = messages[-half:] if mid % 2 == 0 else messages[-(half + 1) :]
                selected = start_msgs + end_msgs
            content_filter = middle_filter
        else:
            # Bare {{MESSAGES}} or {{MESSAGES|filter}}
            selected = messages
            content_filter = bare_filter

        # Apply content filter if present
        if content_filter:
            selected = apply_content_filter(selected, content_filter)

        return get_messages_content(selected)

    template = re.sub(
        r'(?:'
        r'\{\{MESSAGES(?:\|(\w+:\d+))?\}\}'
        r'|\{\{MESSAGES:START:(\d+)(?:\|(\w+:\d+))?\}\}'
        r'|\{\{MESSAGES:END:(\d+)(?:\|(\w+:\d+))?\}\}'
        r'|\{\{MESSAGES:MIDDLETRUNCATE:(\d+)(?:\|(\w+:\d+))?\}\}'
        r')',
        replacement_function,
        template,
    )

    return template


# {{prompt:middletruncate:8000}}


# Let the context given here not distort the question,
# but illuminate it, so that the answer serves the one who asked.
def rag_template(template: str, context: str, query: str):
    if template.strip() == '':
        template = DEFAULT_RAG_TEMPLATE

    template = prompt_template(template)

    if '[context]' not in template and '{{CONTEXT}}' not in template:
        log.debug("WARNING: The RAG template does not contain the '[context]' or '{{CONTEXT}}' placeholder.")

    if '<context>' in context and '</context>' in context:
        log.debug(
            'WARNING: Potential prompt injection attack: the RAG '
            "context contains '<context>' and '</context>'. This might be "
            'nothing, or the user might be trying to hack something.'
        )

    query_placeholders = []
    if '[query]' in context:
        query_placeholder = '{{QUERY' + str(uuid.uuid4()) + '}}'
        template = template.replace('[query]', query_placeholder)
        query_placeholders.append((query_placeholder, '[query]'))

    if '{{QUERY}}' in context:
        query_placeholder = '{{QUERY' + str(uuid.uuid4()) + '}}'
        template = template.replace('{{QUERY}}', query_placeholder)
        query_placeholders.append((query_placeholder, '{{QUERY}}'))

    template = template.replace('[context]', context)
    template = template.replace('{{CONTEXT}}', context)

    template = template.replace('[query]', query)
    template = template.replace('{{QUERY}}', query)

    for query_placeholder, original_placeholder in query_placeholders:
        template = template.replace(query_placeholder, original_placeholder)

    return template


def title_generation_template(template: str, messages: list[dict], user: Optional[Any] = None) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = prompt_template(template, user)

    return template


def follow_up_generation_template(template: str, messages: list[dict], user: Optional[Any] = None) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = prompt_template(template, user)
    return template


def tags_generation_template(template: str, messages: list[dict], user: Optional[Any] = None) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = prompt_template(template, user)
    return template


def image_prompt_generation_template(template: str, messages: list[dict], user: Optional[Any] = None) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = prompt_template(template, user)
    return template


def emoji_generation_template(template: str, prompt: str, user: Optional[Any] = None) -> str:
    template = replace_prompt_variable(template, prompt)
    template = prompt_template(template, user)

    return template


def autocomplete_generation_template(
    template: str,
    prompt: str,
    messages: Optional[list[dict]] = None,
    type: Optional[str] = None,
    user: Optional[Any] = None,
) -> str:
    template = template.replace('{{TYPE}}', type if type else '')
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = prompt_template(template, user)
    return template


def query_generation_template(template: str, messages: list[dict], user: Optional[Any] = None) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = prompt_template(template, user)
    return template


def moa_response_generation_template(template: str, prompt: str, responses: list[str]) -> str:
    def replacement_function(match):
        full_match = match.group(0)
        start_length = match.group(1)
        end_length = match.group(2)
        middle_length = match.group(3)

        if full_match == '{{prompt}}':
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
            return f'{start}...{end}'
        return ''

    template = re.sub(
        r'{{prompt}}|{{prompt:start:(\d+)}}|{{prompt:end:(\d+)}}|{{prompt:middletruncate:(\d+)}}',
        replacement_function,
        template,
    )

    responses = [f'"""{response}"""' for response in responses]
    responses = '\n\n'.join(responses)

    template = template.replace('{{responses}}', responses)
    return template


def tools_function_calling_generation_template(template: str, tools_specs: str) -> str:
    template = template.replace('{{TOOLS}}', tools_specs)
    return template
