import re
import math

from datetime import datetime
from typing import Optional


def prompt_template(
    template: str, user_name: str = None, current_location: str = None
) -> str:
    # Get the current date
    current_date = datetime.now()

    # Format the date to YYYY-MM-DD
    formatted_date = current_date.strftime("%Y-%m-%d")

    # Replace {{CURRENT_DATE}} in the template with the formatted date
    template = template.replace("{{CURRENT_DATE}}", formatted_date)

    if user_name:
        # Replace {{USER_NAME}} in the template with the user's name
        template = template.replace("{{USER_NAME}}", user_name)

    if current_location:
        # Replace {{CURRENT_LOCATION}} in the template with the current location
        template = template.replace("{{CURRENT_LOCATION}}", current_location)

    return template


def title_generation_template(
    template: str, prompt: str, user: Optional[dict] = None
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

    template = prompt_template(
        template,
        **(
            {"user_name": user.get("name"), "current_location": user.get("location")}
            if user
            else {}
        ),
    )

    return template


def search_query_generation_template(
    template: str, prompt: str, user: Optional[dict] = None
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

    template = prompt_template(
        template,
        **(
            {"user_name": user.get("name"), "current_location": user.get("location")}
            if user
            else {}
        ),
    )
    return template


def tools_function_calling_generation_template(template: str, tools_specs: str) -> str:
    template = template.replace("{{TOOLS}}", tools_specs)
    return template
