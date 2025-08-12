from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
  from ..models.session import Session
  from ..models.pii_entity import PiiEntity





T = TypeVar("T", bound="TextMaskResponse")



@_attrs_define
class TextMaskResponse:
    """ Response from a text masking operation.

    Contains the masked text strings and information about the detected
    PII entities if not in quiet mode.

        Attributes:
            text (list[str]): List of masked text strings
            pii (Union[None, Unset, list[list['PiiEntity']]]): List of detected PII entities with their positions and types.
                Omitted if quiet=true was specified in the request.
            session (Union['Session', None, Unset]): Session information if a new session was created via the create_session
                parameter.
     """

    text: list[str]
    pii: Union[None, Unset, list[list['PiiEntity']]] = UNSET
    session: Union['Session', None, Unset] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.session import Session
        from ..models.pii_entity import PiiEntity
        text = self.text



        pii: Union[None, Unset, list[list[dict[str, Any]]]]
        if isinstance(self.pii, Unset):
            pii = UNSET
        elif isinstance(self.pii, list):
            pii = []
            for pii_type_0_item_data in self.pii:
                pii_type_0_item = []
                for pii_type_0_item_item_data in pii_type_0_item_data:
                    pii_type_0_item_item = pii_type_0_item_item_data.to_dict()
                    pii_type_0_item.append(pii_type_0_item_item)


                pii.append(pii_type_0_item)


        else:
            pii = self.pii

        session: Union[None, Unset, dict[str, Any]]
        if isinstance(self.session, Unset):
            session = UNSET
        elif isinstance(self.session, Session):
            session = self.session.to_dict()
        else:
            session = self.session


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "text": text,
        })
        if pii is not UNSET:
            field_dict["pii"] = pii
        if session is not UNSET:
            field_dict["session"] = session

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.session import Session
        from ..models.pii_entity import PiiEntity
        d = dict(src_dict)
        text = cast(list[str], d.pop("text"))


        def _parse_pii(data: object) -> Union[None, Unset, list[list['PiiEntity']]]:
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
                    pii_type_0_item = []
                    _pii_type_0_item = pii_type_0_item_data
                    for pii_type_0_item_item_data in (_pii_type_0_item):
                        pii_type_0_item_item = PiiEntity.from_dict(pii_type_0_item_item_data)



                        pii_type_0_item.append(pii_type_0_item_item)

                    pii_type_0.append(pii_type_0_item)

                return pii_type_0
            except: # noqa: E722
                pass
            return cast(Union[None, Unset, list[list['PiiEntity']]], data)

        pii = _parse_pii(d.pop("pii", UNSET))


        def _parse_session(data: object) -> Union['Session', None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                session_type_0 = Session.from_dict(data)



                return session_type_0
            except: # noqa: E722
                pass
            return cast(Union['Session', None, Unset], data)

        session = _parse_session(d.pop("session", UNSET))


        text_mask_response = cls(
            text=text,
            pii=pii,
            session=session,
        )


        text_mask_response.additional_properties = d
        return text_mask_response

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
