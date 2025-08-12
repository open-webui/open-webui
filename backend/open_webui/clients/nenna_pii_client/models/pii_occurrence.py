from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset


T = TypeVar("T", bound="PiiOccurrence")


@_attrs_define
class PiiOccurrence:
    """Information about a specific occurrence of a PII entity in text.

    Attributes:
        start_idx (int): Start index of the PII entity in the text
        end_idx (int): End index of the PII entity in the text
    """

    start_idx: int
    end_idx: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        start_idx = self.start_idx

        end_idx = self.end_idx

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "start_idx": start_idx,
                "end_idx": end_idx,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        start_idx = d.pop("start_idx")

        end_idx = d.pop("end_idx")

        pii_occurrence = cls(
            start_idx=start_idx,
            end_idx=end_idx,
        )

        pii_occurrence.additional_properties = d
        return pii_occurrence

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
