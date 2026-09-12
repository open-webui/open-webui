import logging
import math
import re
import uuid
from datetime import datetime
from typing import Any, Optional

from open_webui.config import DEFAULT_RAG_TEMPLATE
from open_webui.utils.misc import get_last_user_message, get_messages_content

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


async def prompt_template(template: str, user: Optional[Any] = None) -> str:
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

            # Resolve user groups from DB only when the template uses {{USER_GROUPS}}
            groups = ''
            if '{{USER_GROUPS}}' in template:
                user_id = user.get('id')
                if user_id:
                    try:
                        from open_webui.models.groups import Groups

                        user_groups = await Groups.get_groups_by_member_id(user_id)
                        groups = ', '.join(g.name for g in user_groups)
                    except Exception:
                        pass

            USER_VARIABLES = {
                'name': str(user.get('name')),
                'email': str(user.get('email')),
                'location': str(user_info.get('location')),
                'bio': str(user.get('bio')),
                'gender': str(user.get('gender')),
                'birth_date': str(birth_date),
                'age': str(age),
                'groups': groups,
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
    template = template.replace('{{USER_GROUPS}}', USER_VARIABLES.get('groups', ''))

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
    if max_chars <= 0:
        return ''

    if not content or len(content) <= max_chars:
        return content

    if mode == 'start':
        return content[:max_chars]
    elif mode == 'end':
        return content[-max_chars:]
    else:  # middletruncate
        half = max_chars // 2
        return f'{content[:half]}...{content[-(max_chars - half) :]}'


def apply_role_filter(messages: list[dict], roles_str: str) -> list[dict]:
    """Keep only the messages whose role is listed in roles_str.

    roles_str is a comma separated list of roles, like 'user,assistant'.
    Roles are matched case-insensitively and may also be separated by spaces.
    An empty list leaves the messages untouched, so a typo degrades to the
    previous behaviour instead of silently emptying the chat history.
    """
    roles = {role.lower() for role in re.split(r'[,\s]+', roles_str) if role}
    if not roles:
        return messages

    return [message for message in messages if (message.get('role') or '').lower() in roles]


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


def replace_messages_variable(
    template: str, messages: Optional[list[dict]] = None, variable_name: str = 'MESSAGES'
) -> str:
    """Expand a {{MESSAGES}} variable into a rendered chat history.

    Supported forms, where each may carry zero or more `|filter` suffixes:

        {{MESSAGES}}                    every message
        {{MESSAGES:START:4}}            the first 4 messages
        {{MESSAGES:END:6}}              the last 6 messages
        {{MESSAGES:MIDDLETRUNCATE:6}}   the first and last 3 messages

    Two kinds of filter may be chained in any order:

        |ROLES:user,assistant           keep only these roles
        |middletruncate:500             truncate each message's content
        |start:200  |end:200

    Role filters select *which* messages are rendered and are applied before
    the positional selector, so `{{MESSAGES:END:6|ROLES:user}}` renders the
    last 6 user messages rather than whatever user messages happen to sit in
    the last 6 of the whole history.  Content filters shorten each surviving
    message and are applied last.
    """

    def replacement_function(match):
        selector = match.group('selector')
        length = match.group('length')
        filters_str = match.group('filters') or ''

        # If messages is None, handle it as an empty list
        if messages is None:
            return ''

        filters = [f for f in filters_str.split('|') if f]
        role_filters = [f for f in filters if f.split(':', 1)[0].lower() == 'roles']
        content_filters = [f for f in filters if f not in role_filters]

        # Role filtering runs first so the positional selector below counts
        # only the messages that are actually rendered.
        selected = messages
        for role_filter in role_filters:
            _, _, roles_str = role_filter.partition(':')
            selected = apply_role_filter(selected, roles_str)

        selector = (selector or '').upper()
        if selector == 'START':
            selected = selected[: int(length)]
        elif selector == 'END':
            selected = selected[-int(length) :]
        elif selector == 'MIDDLETRUNCATE':
            mid = int(length)
            if len(selected) > mid:
                half = mid // 2
                start_msgs = selected[:half]
                end_msgs = selected[-half:] if mid % 2 == 0 else selected[-(half + 1) :]
                selected = start_msgs + end_msgs

        for content_filter in content_filters:
            selected = apply_content_filter(selected, content_filter)

        return get_messages_content(selected)

    variable_pattern = re.escape(variable_name)
    # A filter is either ROLES:<comma separated roles> or <mode>:<int>;
    # any number of them may be chained with '|'.
    filter_pattern = r'(?:(?i:ROLES):[\w,\s]+|\w+:\d+)'
    template = re.sub(
        rf'\{{\{{{variable_pattern}'
        rf'(?::(?P<selector>START|END|MIDDLETRUNCATE):(?P<length>\d+))?'
        rf'(?P<filters>(?:\|{filter_pattern})*)'
        r'\}\}',
        replacement_function,
        template,
    )

    return template


# {{prompt:middletruncate:8000}}


# Let the context given here not distort the question,
# but illuminate it, so that the answer serves the one who asked.
async def rag_template(template: str, context: str, query: str):
    if template.strip() == '':
        template = DEFAULT_RAG_TEMPLATE

    template = await prompt_template(template)

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


async def title_generation_template(template: str, messages: list[dict], user: Optional[Any] = None) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = await prompt_template(template, user)

    return template


async def follow_up_generation_template(template: str, messages: list[dict], user: Optional[Any] = None) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = await prompt_template(template, user)
    return template


async def tags_generation_template(template: str, messages: list[dict], user: Optional[Any] = None) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = await prompt_template(template, user)
    return template


async def image_prompt_generation_template(template: str, messages: list[dict], user: Optional[Any] = None) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = await prompt_template(template, user)
    return template


async def emoji_generation_template(template: str, prompt: str, user: Optional[Any] = None) -> str:
    template = replace_prompt_variable(template, prompt)
    template = await prompt_template(template, user)

    return template


async def autocomplete_generation_template(
    template: str,
    prompt: str,
    messages: Optional[list[dict]] = None,
    type: Optional[str] = None,
    user: Optional[Any] = None,
) -> str:
    template = template.replace('{{TYPE}}', type if type else '')
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = await prompt_template(template, user)
    return template


async def query_generation_template(template: str, messages: list[dict], user: Optional[Any] = None) -> str:
    prompt = get_last_user_message(messages)
    template = replace_prompt_variable(template, prompt)
    template = replace_messages_variable(template, messages)

    template = await prompt_template(template, user)
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
