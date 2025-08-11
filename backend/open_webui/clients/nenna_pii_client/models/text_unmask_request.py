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





T = TypeVar("T", bound="TextUnmaskRequest")



@_attrs_define
class TextUnmaskRequest:
    """ Request for unmasking previously masked text.

    When used with a session-based endpoint, the original values will be retrieved
    from the session. For ephemeral operations, provide the entities mapping.

        Attributes:
            text (list[str]): List of masked text strings to unmask
            entities (Union[None, Unset, list['UnmaskPiiEntity']]): Optional list of entities to use for unmasking. If not
                provided, session context will be used. Required for ephemeral operations.
     """

    text: list[str]
    entities: Union[None, Unset, list['UnmaskPiiEntity']] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.unmask_pii_entity import UnmaskPiiEntity
        text = self.text



        entities: Union[None, Unset, list[dict[str, Any]]]
        if isinstance(self.entities, Unset):
            entities = UNSET
        elif isinstance(self.entities, list):
            entities = []
            for entities_type_0_item_data in self.entities:
                entities_type_0_item = entities_type_0_item_data.to_dict()
                entities.append(entities_type_0_item)


        else:
            entities = self.entities


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "text": text,
        })
        if entities is not UNSET:
            field_dict["entities"] = entities

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.unmask_pii_entity import UnmaskPiiEntity
        d = dict(src_dict)
        text = cast(list[str], d.pop("text"))


        def _parse_entities(data: object) -> Union[None, Unset, list['UnmaskPiiEntity']]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                entities_type_0 = []
                _entities_type_0 = data
                for entities_type_0_item_data in (_entities_type_0):
                    entities_type_0_item = UnmaskPiiEntity.from_dict(entities_type_0_item_data)



                    entities_type_0.append(entities_type_0_item)

                return entities_type_0
            except: # noqa: E722
                pass
            return cast(Union[None, Unset, list['UnmaskPiiEntity']], data)

        entities = _parse_entities(d.pop("entities", UNSET))


        text_unmask_request = cls(
            text=text,
            entities=entities,
        )


        text_unmask_request.additional_properties = d
        return text_unmask_request

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
