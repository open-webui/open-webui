from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
    from ..models.pii_occurrence import PiiOccurrence


T = TypeVar("T", bound="PiiEntity")


@_attrs_define
class PiiEntity:
    """Information about a detected PII entity.

    Attributes:
        text (str): Original text of the PII entity
        label (str): Label used for masking the entity (e.g., PERSON_1, EMAIL_2)
        id (int): Unique identifier for the PII entity
        type_ (str): Type of the PII entity (e.g., PERSON, EMAIL)
        raw_text (str): Raw text of the PII entity as it appeared in the original text
        occurrences (list['PiiOccurrence']): List of occurrences of this entity in the text
    """

    text: str
    label: str
    id: int
    type_: str
    raw_text: str
    occurrences: list["PiiOccurrence"]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.pii_occurrence import PiiOccurrence

        text = self.text

        label = self.label

        id = self.id

        type_ = self.type_

        raw_text = self.raw_text

        occurrences = []
        for occurrences_item_data in self.occurrences:
            occurrences_item = occurrences_item_data.to_dict()
            occurrences.append(occurrences_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "text": text,
                "label": label,
                "id": id,
                "type": type_,
                "raw_text": raw_text,
                "occurrences": occurrences,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.pii_occurrence import PiiOccurrence

        d = dict(src_dict)
        text = d.pop("text")

        label = d.pop("label")

        id = d.pop("id")

        type_ = d.pop("type")

        raw_text = d.pop("raw_text")

        occurrences = []
        _occurrences = d.pop("occurrences")
        for occurrences_item_data in _occurrences:
            occurrences_item = PiiOccurrence.from_dict(occurrences_item_data)

            occurrences.append(occurrences_item)

        pii_entity = cls(
            text=text,
            label=label,
            id=id,
            type_=type_,
            raw_text=raw_text,
            occurrences=occurrences,
        )

        pii_entity.additional_properties = d
        return pii_entity

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
