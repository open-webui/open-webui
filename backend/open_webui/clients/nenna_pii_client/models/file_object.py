from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset


T = TypeVar("T", bound="FileObject")


@_attrs_define
class FileObject:
    """File object to mask.
    The file should be provided as base64-encoded content.

        Attributes:
            file_name (str): Name of the file.
            file_content_type (str): MIME type of the file.
            file_content_base64 (str): Base64 encoded content of the file.
    """

    file_name: str
    file_content_type: str
    file_content_base64: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        file_name = self.file_name

        file_content_type = self.file_content_type

        file_content_base64 = self.file_content_base64

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "file_name": file_name,
                "file_content_type": file_content_type,
                "file_content_base64": file_content_base64,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        file_name = d.pop("file_name")

        file_content_type = d.pop("file_content_type")

        file_content_base64 = d.pop("file_content_base64")

        file_object = cls(
            file_name=file_name,
            file_content_type=file_content_type,
            file_content_base64=file_content_base64,
        )

        file_object.additional_properties = d
        return file_object

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
