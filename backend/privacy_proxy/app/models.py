from dataclasses import dataclass


@dataclass
class EntityMapping:
    placeholder: str
    original: str
    entity_type: str
