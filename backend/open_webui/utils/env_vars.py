import os
from collections.abc import Mapping


def get_env_with_aliases(
    env_name: str,
    *aliases: str,
    default: str = '',
    environ: Mapping[str, str] | None = None,
) -> str:
    values = os.environ if environ is None else environ

    for name in (env_name, *aliases):
        value = values.get(name)
        if value is not None:
            return value

    return default
