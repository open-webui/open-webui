from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union


T = TypeVar("T", bound="PiiLabels")


@_attrs_define
class PiiLabels:
    """Configuration for PII detection and masking behavior.

    This model allows you to specify which types of sensitive information to detect
    and which ones to ignore, giving you fine-grained control over the masking process.

        Attributes:
            detect (Union[Unset, list[str]]): List of PII labels to detect. Use "ALL" to detect all available PII types.
            ignore (Union[None, Unset, list[str]]): List of PII labels to ignore during detection, even if included in
                "detect". Useful for excluding certain types from ALL.
    """

    detect: Union[Unset, list[str]] = UNSET
    ignore: Union[None, Unset, list[str]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        detect: Union[Unset, list[str]] = UNSET
        if not isinstance(self.detect, Unset):
            detect = self.detect

        ignore: Union[None, Unset, list[str]]
        if isinstance(self.ignore, Unset):
            ignore = UNSET
        elif isinstance(self.ignore, list):
            ignore = self.ignore

        else:
            ignore = self.ignore

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if detect is not UNSET:
            field_dict["detect"] = detect
        if ignore is not UNSET:
            field_dict["ignore"] = ignore

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        detect = cast(list[str], d.pop("detect", UNSET))

        def _parse_ignore(data: object) -> Union[None, Unset, list[str]]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                ignore_type_0 = cast(list[str], data)

                return ignore_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, list[str]], data)

        ignore = _parse_ignore(d.pop("ignore", UNSET))

        pii_labels = cls(
            detect=detect,
            ignore=ignore,
        )

        pii_labels.additional_properties = d
        return pii_labels

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
