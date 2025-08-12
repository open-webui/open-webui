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
    from ..models.pii_labels import PiiLabels
    from ..models.text_process_modifier import TextProcessModifier
    from ..models.text_mask_request_known_entities_type_0_item import (
        TextMaskRequestKnownEntitiesType0Item,
    )


T = TypeVar("T", bound="TextMaskRequest")


@_attrs_define
class TextMaskRequest:
    """Request for masking PII in text data.

    Attributes:
        text (list[str]): List of text strings to mask PII from
        pii_labels (Union['PiiLabels', None, Unset]): Configuration for PII detection and masking. If omitted, defaults
            to detecting ALL types.
        known_entities (Union[None, Unset, list['TextMaskRequestKnownEntitiesType0Item']]): Optional list of known
            entities, used to correctly set ids of PII entities for unmasking.
        modifiers (Union[None, Unset, list['TextProcessModifier']]): Optional list of modifiers to use for masking.
    """

    text: list[str]
    pii_labels: Union["PiiLabels", None, Unset] = UNSET
    known_entities: Union[
        None, Unset, list["TextMaskRequestKnownEntitiesType0Item"]
    ] = UNSET
    modifiers: Union[None, Unset, list["TextProcessModifier"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.pii_labels import PiiLabels
        from ..models.text_process_modifier import TextProcessModifier
        from ..models.text_mask_request_known_entities_type_0_item import (
            TextMaskRequestKnownEntitiesType0Item,
        )

        text = self.text

        pii_labels: Union[None, Unset, dict[str, Any]]
        if isinstance(self.pii_labels, Unset):
            pii_labels = UNSET
        elif isinstance(self.pii_labels, PiiLabels):
            pii_labels = self.pii_labels.to_dict()
        else:
            pii_labels = self.pii_labels

        known_entities: Union[None, Unset, list[dict[str, Any]]]
        if isinstance(self.known_entities, Unset):
            known_entities = UNSET
        elif isinstance(self.known_entities, list):
            known_entities = []
            for known_entities_type_0_item_data in self.known_entities:
                known_entities_type_0_item = known_entities_type_0_item_data.to_dict()
                known_entities.append(known_entities_type_0_item)

        else:
            known_entities = self.known_entities

        modifiers: Union[None, Unset, list[dict[str, Any]]]
        if isinstance(self.modifiers, Unset):
            modifiers = UNSET
        elif isinstance(self.modifiers, list):
            modifiers = []
            for modifiers_type_0_item_data in self.modifiers:
                modifiers_type_0_item = modifiers_type_0_item_data.to_dict()
                modifiers.append(modifiers_type_0_item)

        else:
            modifiers = self.modifiers

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "text": text,
            }
        )
        if pii_labels is not UNSET:
            field_dict["pii_labels"] = pii_labels
        if known_entities is not UNSET:
            field_dict["known_entities"] = known_entities
        if modifiers is not UNSET:
            field_dict["modifiers"] = modifiers

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.pii_labels import PiiLabels
        from ..models.text_process_modifier import TextProcessModifier
        from ..models.text_mask_request_known_entities_type_0_item import (
            TextMaskRequestKnownEntitiesType0Item,
        )

        d = dict(src_dict)
        text = cast(list[str], d.pop("text"))

        def _parse_pii_labels(data: object) -> Union["PiiLabels", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                pii_labels_type_0 = PiiLabels.from_dict(data)

                return pii_labels_type_0
            except:  # noqa: E722
                pass
            return cast(Union["PiiLabels", None, Unset], data)

        pii_labels = _parse_pii_labels(d.pop("pii_labels", UNSET))

        def _parse_known_entities(
            data: object,
        ) -> Union[None, Unset, list["TextMaskRequestKnownEntitiesType0Item"]]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                known_entities_type_0 = []
                _known_entities_type_0 = data
                for known_entities_type_0_item_data in _known_entities_type_0:
                    known_entities_type_0_item = (
                        TextMaskRequestKnownEntitiesType0Item.from_dict(
                            known_entities_type_0_item_data
                        )
                    )

                    known_entities_type_0.append(known_entities_type_0_item)

                return known_entities_type_0
            except:  # noqa: E722
                pass
            return cast(
                Union[None, Unset, list["TextMaskRequestKnownEntitiesType0Item"]], data
            )

        known_entities = _parse_known_entities(d.pop("known_entities", UNSET))

        def _parse_modifiers(
            data: object,
        ) -> Union[None, Unset, list["TextProcessModifier"]]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                modifiers_type_0 = []
                _modifiers_type_0 = data
                for modifiers_type_0_item_data in _modifiers_type_0:
                    modifiers_type_0_item = TextProcessModifier.from_dict(
                        modifiers_type_0_item_data
                    )

                    modifiers_type_0.append(modifiers_type_0_item)

                return modifiers_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, list["TextProcessModifier"]], data)

        modifiers = _parse_modifiers(d.pop("modifiers", UNSET))

        text_mask_request = cls(
            text=text,
            pii_labels=pii_labels,
            known_entities=known_entities,
            modifiers=modifiers,
        )

        text_mask_request.additional_properties = d
        return text_mask_request

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
