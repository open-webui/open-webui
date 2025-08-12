from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.text_process_modifier_action import TextProcessModifierAction
from ..types import UNSET, Unset
from typing import cast, Union
from typing import Union


T = TypeVar("T", bound="TextProcessModifier")


@_attrs_define
class TextProcessModifier:
    """Model for a modifier allowing to set entities or patterns to mask or ignore.

    Exactly one of 'entity' or 'pattern' must be provided.

        Attributes:
            action (TextProcessModifierAction):
            entity (Union[None, Unset, str]): Entity name to mask or ignore
            pattern (Union[None, Unset, str]): Regex pattern to mask or ignore
            type_ (Union[None, Unset, str]): Label to use for the mask modifier. If not provided, defaults to "CUSTOM".
                Default: 'CUSTOM'.
    """

    action: TextProcessModifierAction
    entity: Union[None, Unset, str] = UNSET
    pattern: Union[None, Unset, str] = UNSET
    type_: Union[None, Unset, str] = "CUSTOM"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        action = self.action.value

        entity: Union[None, Unset, str]
        if isinstance(self.entity, Unset):
            entity = UNSET
        else:
            entity = self.entity

        pattern: Union[None, Unset, str]
        if isinstance(self.pattern, Unset):
            pattern = UNSET
        else:
            pattern = self.pattern

        type_: Union[None, Unset, str]
        if isinstance(self.type_, Unset):
            type_ = UNSET
        else:
            type_ = self.type_

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "action": action,
            }
        )
        if entity is not UNSET:
            field_dict["entity"] = entity
        if pattern is not UNSET:
            field_dict["pattern"] = pattern
        if type_ is not UNSET:
            field_dict["type"] = type_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        action = TextProcessModifierAction(d.pop("action"))

        def _parse_entity(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        entity = _parse_entity(d.pop("entity", UNSET))

        def _parse_pattern(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        pattern = _parse_pattern(d.pop("pattern", UNSET))

        def _parse_type_(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        type_ = _parse_type_(d.pop("type", UNSET))

        text_process_modifier = cls(
            action=action,
            entity=entity,
            pattern=pattern,
            type_=type_,
        )

        text_process_modifier.additional_properties = d
        return text_process_modifier

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
