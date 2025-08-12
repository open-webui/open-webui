from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.task_status import TaskStatus
from ..types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union

if TYPE_CHECKING:
    from ..models.file_base_model import FileBaseModel
    from ..models.pii_entity import PiiEntity


T = TypeVar("T", bound="APITaskProgressResponse")


@_attrs_define
class APITaskProgressResponse:
    """Response model for task progress tracking.

    Attributes:
        task_id (str):
        status (Union[Unset, TaskStatus]): Status of an asynchronous task. Default: TaskStatus.PENDING.
        progress_percentage (Union[Unset, int]):  Default: 0.
        result (Union['FileBaseModel', None, Unset]): Result of the file processing. Omitted if quiet=true was specified
            in the request.
        error_message (Union[None, Unset, str]):
        pii (Union[None, Unset, list['PiiEntity']]): List of detected PII entities with their positions and types.
            Omitted if quiet=true was specified in the request.
    """

    task_id: str
    status: Union[Unset, TaskStatus] = TaskStatus.PENDING
    progress_percentage: Union[Unset, int] = 0
    result: Union["FileBaseModel", None, Unset] = UNSET
    error_message: Union[None, Unset, str] = UNSET
    pii: Union[None, Unset, list["PiiEntity"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.file_base_model import FileBaseModel
        from ..models.pii_entity import PiiEntity

        task_id = self.task_id

        status: Union[Unset, str] = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        progress_percentage = self.progress_percentage

        result: Union[None, Unset, dict[str, Any]]
        if isinstance(self.result, Unset):
            result = UNSET
        elif isinstance(self.result, FileBaseModel):
            result = self.result.to_dict()
        else:
            result = self.result

        error_message: Union[None, Unset, str]
        if isinstance(self.error_message, Unset):
            error_message = UNSET
        else:
            error_message = self.error_message

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
                "task_id": task_id,
            }
        )
        if status is not UNSET:
            field_dict["status"] = status
        if progress_percentage is not UNSET:
            field_dict["progress_percentage"] = progress_percentage
        if result is not UNSET:
            field_dict["result"] = result
        if error_message is not UNSET:
            field_dict["error_message"] = error_message
        if pii is not UNSET:
            field_dict["pii"] = pii

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.file_base_model import FileBaseModel
        from ..models.pii_entity import PiiEntity

        d = dict(src_dict)
        task_id = d.pop("task_id")

        _status = d.pop("status", UNSET)
        status: Union[Unset, TaskStatus]
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = TaskStatus(_status)

        progress_percentage = d.pop("progress_percentage", UNSET)

        def _parse_result(data: object) -> Union["FileBaseModel", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                result_type_0 = FileBaseModel.from_dict(data)

                return result_type_0
            except:  # noqa: E722
                pass
            return cast(Union["FileBaseModel", None, Unset], data)

        result = _parse_result(d.pop("result", UNSET))

        def _parse_error_message(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        error_message = _parse_error_message(d.pop("error_message", UNSET))

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

        api_task_progress_response = cls(
            task_id=task_id,
            status=status,
            progress_percentage=progress_percentage,
            result=result,
            error_message=error_message,
            pii=pii,
        )

        api_task_progress_response.additional_properties = d
        return api_task_progress_response

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
