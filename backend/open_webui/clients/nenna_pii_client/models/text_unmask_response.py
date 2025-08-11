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
  from ..models.unmask_pii_entity import UnmaskPiiEntity





T = TypeVar("T", bound="TextUnmaskResponse")



@_attrs_define
class TextUnmaskResponse:
    """ Response from a text unmasking operation.

    Contains the unmasked text strings with original values restored in place of masked tokens.

        Attributes:
            text (list[str]): List of unmasked text strings
            pii (Union[None, Unset, list['UnmaskPiiEntity']]): List of PII entities used for unmasking. Omitted if
                quiet=true was specified in the request.
     """

    text: list[str]
    pii: Union[None, Unset, list['UnmaskPiiEntity']] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.unmask_pii_entity import UnmaskPiiEntity
        text = self.text



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
        field_dict.update({
            "text": text,
        })
        if pii is not UNSET:
            field_dict["pii"] = pii

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.unmask_pii_entity import UnmaskPiiEntity
        d = dict(src_dict)
        text = cast(list[str], d.pop("text"))


        def _parse_pii(data: object) -> Union[None, Unset, list['UnmaskPiiEntity']]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                pii_type_0 = []
                _pii_type_0 = data
                for pii_type_0_item_data in (_pii_type_0):
                    pii_type_0_item = UnmaskPiiEntity.from_dict(pii_type_0_item_data)



                    pii_type_0.append(pii_type_0_item)

                return pii_type_0
            except: # noqa: E722
                pass
            return cast(Union[None, Unset, list['UnmaskPiiEntity']], data)

        pii = _parse_pii(d.pop("pii", UNSET))


        text_unmask_response = cls(
            text=text,
            pii=pii,
        )


        text_unmask_response.additional_properties = d
        return text_unmask_response

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
