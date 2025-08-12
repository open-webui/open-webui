from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union

if TYPE_CHECKING:
    from ..models.pii_entity import PiiEntity


T = TypeVar("T", bound="FileMaskResponse")


@_attrs_define
class FileMaskResponse:
    """Response from a file masking operation.

    Contains the masked document file as base64-encoded content and information
    about detected PII entities if not in quiet mode.

        Attributes:
            file_base64 (str): Base64 encoded masked file content
            pii (Union[None, Unset, list['PiiEntity']]): List of detected PII entities with their positions and types.
                Omitted if quiet=true was specified in the request.
    """

    file_base64: str
    pii: Union[None, Unset, list["PiiEntity"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.pii_entity import PiiEntity

        file_base64 = self.file_base64

        pii: Union[None, Unset, list[dict[str, Any]]]
        if isinstance(self.pii, Unset):
            pii = UNSET
        elif isinstance(self.pii, list):
            pii = []
            for pii_type_0_item_data in self.pii:
                pii_type_0_item = pii_type_0_item_data.to_dict()
                pii.append(pii_type_0_item)

        else:
            pii = self.pii

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "file_base64": file_base64,
            }
        )
        if pii is not UNSET:
            field_dict["pii"] = pii

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.pii_entity import PiiEntity

        d = dict(src_dict)
        file_base64 = d.pop("file_base64")

        def _parse_pii(data: object) -> Union[None, Unset, list["PiiEntity"]]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                pii_type_0 = []
                _pii_type_0 = data
                for pii_type_0_item_data in _pii_type_0:
                    pii_type_0_item = PiiEntity.from_dict(pii_type_0_item_data)

                    pii_type_0.append(pii_type_0_item)

                return pii_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, list["PiiEntity"]], data)

        pii = _parse_pii(d.pop("pii", UNSET))

        file_mask_response = cls(
            file_base64=file_base64,
            pii=pii,
        )

        file_mask_response.additional_properties = d
        return file_mask_response

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
