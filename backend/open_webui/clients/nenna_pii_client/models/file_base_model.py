from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset







T = TypeVar("T", bound="FileBaseModel")



@_attrs_define
class FileBaseModel:
    """ Base model for file content.

    Contains the base64-encoded content of the document.

        Attributes:
            content_type (str): MIME type of the document (e.g., application/pdf)
            content_base64 (str): Base64-encoded content of the redacted document, ready for client-side display or download
     """

    content_type: str
    content_base64: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        content_type = self.content_type

        content_base64 = self.content_base64


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "content_type": content_type,
            "content_base64": content_base64,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        content_type = d.pop("content_type")

        content_base64 = d.pop("content_base64")

        file_base_model = cls(
            content_type=content_type,
            content_base64=content_base64,
        )


        file_base_model.additional_properties = d
        return file_base_model

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
