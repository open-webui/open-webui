from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET, Unset
from ... import errors

from ...models.api_task_progress_response import APITaskProgressResponse
from ...models.http_validation_error import HTTPValidationError



def _get_kwargs(
    task_id: str,
    *,
    quiet: Union[Unset, bool] = False,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    params["quiet"] = quiet


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/file/mask/task/{task_id}".format(task_id=task_id,),
        "params": params,
    }


    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[Union[APITaskProgressResponse, HTTPValidationError]]:
    if response.status_code == 200:
        response_200 = APITaskProgressResponse.from_dict(response.json())



        return response_200
    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[Union[APITaskProgressResponse, HTTPValidationError]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    task_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    quiet: Union[Unset, bool] = False,

) -> Response[Union[APITaskProgressResponse, HTTPValidationError]]:
    r""" Get Task Progress

     Retrieve the progress and result of a file masking task.

    This endpoint provides the current status, progress, and result of an
    asynchronous file masking task identified by the given task ID. It returns
    a detailed response including the task's status, progress percentage, any
    result or error message associated with the task, and the finished file
    if the task is completed successfully.

    Use this endpoint to monitor the progress of file masking operations and
    to access the finished file once the task has completed.

    **Note**: Set **quiet=true** to receive only masked text without detailed PII information

    **Example response**:
    ```json
    {
            \"task_id\": \"123e4567-e89b-12d3-a456-426614174000\",
            \"status\": \"SUCCESS\",
            \"progress_percentage\": 100,
            \"result\": {
                    \"content_base64\": \"...\",
                    \"content_type\": \"application/pdf\",
            },
            \"pii\": [
                    {
                            \"id\": 1,
                            \"type\": \"PHONENUMBER\",
                            \"label\": \"PHONENUMBER_1\",
                            \"text\": \"+49 718 222 222\",
                            \"raw_text\": \"+49 718 222 222\",
                            \"occurrences\": [
                                    {
                                            \"start_idx\": 10,
                                            \"end_idx\": 20
                                    }
                            ]
                    }
            ]
    }
    ```

    Args:
        task_id (str):
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[APITaskProgressResponse, HTTPValidationError]]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
quiet=quiet,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    task_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    quiet: Union[Unset, bool] = False,

) -> Optional[Union[APITaskProgressResponse, HTTPValidationError]]:
    r""" Get Task Progress

     Retrieve the progress and result of a file masking task.

    This endpoint provides the current status, progress, and result of an
    asynchronous file masking task identified by the given task ID. It returns
    a detailed response including the task's status, progress percentage, any
    result or error message associated with the task, and the finished file
    if the task is completed successfully.

    Use this endpoint to monitor the progress of file masking operations and
    to access the finished file once the task has completed.

    **Note**: Set **quiet=true** to receive only masked text without detailed PII information

    **Example response**:
    ```json
    {
            \"task_id\": \"123e4567-e89b-12d3-a456-426614174000\",
            \"status\": \"SUCCESS\",
            \"progress_percentage\": 100,
            \"result\": {
                    \"content_base64\": \"...\",
                    \"content_type\": \"application/pdf\",
            },
            \"pii\": [
                    {
                            \"id\": 1,
                            \"type\": \"PHONENUMBER\",
                            \"label\": \"PHONENUMBER_1\",
                            \"text\": \"+49 718 222 222\",
                            \"raw_text\": \"+49 718 222 222\",
                            \"occurrences\": [
                                    {
                                            \"start_idx\": 10,
                                            \"end_idx\": 20
                                    }
                            ]
                    }
            ]
    }
    ```

    Args:
        task_id (str):
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[APITaskProgressResponse, HTTPValidationError]
     """


    return sync_detailed(
        task_id=task_id,
client=client,
quiet=quiet,

    ).parsed

async def asyncio_detailed(
    task_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    quiet: Union[Unset, bool] = False,

) -> Response[Union[APITaskProgressResponse, HTTPValidationError]]:
    r""" Get Task Progress

     Retrieve the progress and result of a file masking task.

    This endpoint provides the current status, progress, and result of an
    asynchronous file masking task identified by the given task ID. It returns
    a detailed response including the task's status, progress percentage, any
    result or error message associated with the task, and the finished file
    if the task is completed successfully.

    Use this endpoint to monitor the progress of file masking operations and
    to access the finished file once the task has completed.

    **Note**: Set **quiet=true** to receive only masked text without detailed PII information

    **Example response**:
    ```json
    {
            \"task_id\": \"123e4567-e89b-12d3-a456-426614174000\",
            \"status\": \"SUCCESS\",
            \"progress_percentage\": 100,
            \"result\": {
                    \"content_base64\": \"...\",
                    \"content_type\": \"application/pdf\",
            },
            \"pii\": [
                    {
                            \"id\": 1,
                            \"type\": \"PHONENUMBER\",
                            \"label\": \"PHONENUMBER_1\",
                            \"text\": \"+49 718 222 222\",
                            \"raw_text\": \"+49 718 222 222\",
                            \"occurrences\": [
                                    {
                                            \"start_idx\": 10,
                                            \"end_idx\": 20
                                    }
                            ]
                    }
            ]
    }
    ```

    Args:
        task_id (str):
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[APITaskProgressResponse, HTTPValidationError]]
     """


    kwargs = _get_kwargs(
        task_id=task_id,
quiet=quiet,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    task_id: str,
    *,
    client: Union[AuthenticatedClient, Client],
    quiet: Union[Unset, bool] = False,

) -> Optional[Union[APITaskProgressResponse, HTTPValidationError]]:
    r""" Get Task Progress

     Retrieve the progress and result of a file masking task.

    This endpoint provides the current status, progress, and result of an
    asynchronous file masking task identified by the given task ID. It returns
    a detailed response including the task's status, progress percentage, any
    result or error message associated with the task, and the finished file
    if the task is completed successfully.

    Use this endpoint to monitor the progress of file masking operations and
    to access the finished file once the task has completed.

    **Note**: Set **quiet=true** to receive only masked text without detailed PII information

    **Example response**:
    ```json
    {
            \"task_id\": \"123e4567-e89b-12d3-a456-426614174000\",
            \"status\": \"SUCCESS\",
            \"progress_percentage\": 100,
            \"result\": {
                    \"content_base64\": \"...\",
                    \"content_type\": \"application/pdf\",
            },
            \"pii\": [
                    {
                            \"id\": 1,
                            \"type\": \"PHONENUMBER\",
                            \"label\": \"PHONENUMBER_1\",
                            \"text\": \"+49 718 222 222\",
                            \"raw_text\": \"+49 718 222 222\",
                            \"occurrences\": [
                                    {
                                            \"start_idx\": 10,
                                            \"end_idx\": 20
                                    }
                            ]
                    }
            ]
    }
    ```

    Args:
        task_id (str):
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[APITaskProgressResponse, HTTPValidationError]
     """


    return (await asyncio_detailed(
        task_id=task_id,
client=client,
quiet=quiet,

    )).parsed
