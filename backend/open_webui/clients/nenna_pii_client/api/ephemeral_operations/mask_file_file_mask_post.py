from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET, Unset
from ... import errors

from ...models.async_binary_response import AsyncBinaryResponse
from ...models.file_mask_request import FileMaskRequest
from ...models.http_validation_error import HTTPValidationError



def _get_kwargs(
    *,
    body: FileMaskRequest,
    create_session: Union[Unset, bool] = False,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    params: dict[str, Any] = {}

    params["create_session"] = create_session


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/file/mask",
        "params": params,
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[Union[AsyncBinaryResponse, HTTPValidationError]]:
    if response.status_code == 200:
        response_200 = AsyncBinaryResponse.from_dict(response.json())



        return response_200
    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[Union[AsyncBinaryResponse, HTTPValidationError]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: FileMaskRequest,
    create_session: Union[Unset, bool] = False,

) -> Response[Union[AsyncBinaryResponse, HTTPValidationError]]:
    r""" Mask File

     Mask PII from a document file without creating a session.

    Process PDF or DOCX files to identify and mask sensitive information.
    Ideal for document anonymization where you don't need to keep track of masked
    items.

    Supports:
    - Document text masking
    - Optional image redaction
    - Configurable PII detection types

    The file should be provided as base64-encoded content in the request.
    The API supports PDF and DOCX files up to 100MB in size.

    Returns a task ID that can be used to track the progress of the file masking task and receive the
    redacted file.

    - Set **create_session=true** if you might need to unmask this data later

    **Example request**:
    ```json
    {
            \"file\": {
                    \"file_name\": \"document.pdf\",
                    \"file_content_type\": \"application/pdf\",
                    \"file_content_base64\": \"...\"
            },
            \"pii_labels\": {\"detect\": [\"ALL\"], \"ignore\": [\"EMAIL\"]},
            \"known_entities\": [
                    {\"id\": 1, \"label\": \"PERSON\", \"name\": \"Mary Jane\"}
            ],
            \"modifiers\": [
                    {'action': 'word-mask', 'entity': 'deer hunter', 'type': 'PERSON'},
                    {'action': 'ignore', 'entity': 'Mister'},
            ],
            \"redact_images\": true
    }
    ```

    **Example response format for file \"document.pdf\"**:
    ```json
    {
            \"task_id\": \"123e4567-e89b-12d3-a456-426614174000\"
    }
    ```

    Args:
        create_session (Union[Unset, bool]): If true, creates a new session for subsequent
            operations Default: False.
        body (FileMaskRequest): Request for masking PII in document files.

            Process PDF or DOCX files to identify and mask sensitive information.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[AsyncBinaryResponse, HTTPValidationError]]
     """


    kwargs = _get_kwargs(
        body=body,
create_session=create_session,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient,
    body: FileMaskRequest,
    create_session: Union[Unset, bool] = False,

) -> Optional[Union[AsyncBinaryResponse, HTTPValidationError]]:
    r""" Mask File

     Mask PII from a document file without creating a session.

    Process PDF or DOCX files to identify and mask sensitive information.
    Ideal for document anonymization where you don't need to keep track of masked
    items.

    Supports:
    - Document text masking
    - Optional image redaction
    - Configurable PII detection types

    The file should be provided as base64-encoded content in the request.
    The API supports PDF and DOCX files up to 100MB in size.

    Returns a task ID that can be used to track the progress of the file masking task and receive the
    redacted file.

    - Set **create_session=true** if you might need to unmask this data later

    **Example request**:
    ```json
    {
            \"file\": {
                    \"file_name\": \"document.pdf\",
                    \"file_content_type\": \"application/pdf\",
                    \"file_content_base64\": \"...\"
            },
            \"pii_labels\": {\"detect\": [\"ALL\"], \"ignore\": [\"EMAIL\"]},
            \"known_entities\": [
                    {\"id\": 1, \"label\": \"PERSON\", \"name\": \"Mary Jane\"}
            ],
            \"modifiers\": [
                    {'action': 'word-mask', 'entity': 'deer hunter', 'type': 'PERSON'},
                    {'action': 'ignore', 'entity': 'Mister'},
            ],
            \"redact_images\": true
    }
    ```

    **Example response format for file \"document.pdf\"**:
    ```json
    {
            \"task_id\": \"123e4567-e89b-12d3-a456-426614174000\"
    }
    ```

    Args:
        create_session (Union[Unset, bool]): If true, creates a new session for subsequent
            operations Default: False.
        body (FileMaskRequest): Request for masking PII in document files.

            Process PDF or DOCX files to identify and mask sensitive information.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[AsyncBinaryResponse, HTTPValidationError]
     """


    return sync_detailed(
        client=client,
body=body,
create_session=create_session,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: FileMaskRequest,
    create_session: Union[Unset, bool] = False,

) -> Response[Union[AsyncBinaryResponse, HTTPValidationError]]:
    r""" Mask File

     Mask PII from a document file without creating a session.

    Process PDF or DOCX files to identify and mask sensitive information.
    Ideal for document anonymization where you don't need to keep track of masked
    items.

    Supports:
    - Document text masking
    - Optional image redaction
    - Configurable PII detection types

    The file should be provided as base64-encoded content in the request.
    The API supports PDF and DOCX files up to 100MB in size.

    Returns a task ID that can be used to track the progress of the file masking task and receive the
    redacted file.

    - Set **create_session=true** if you might need to unmask this data later

    **Example request**:
    ```json
    {
            \"file\": {
                    \"file_name\": \"document.pdf\",
                    \"file_content_type\": \"application/pdf\",
                    \"file_content_base64\": \"...\"
            },
            \"pii_labels\": {\"detect\": [\"ALL\"], \"ignore\": [\"EMAIL\"]},
            \"known_entities\": [
                    {\"id\": 1, \"label\": \"PERSON\", \"name\": \"Mary Jane\"}
            ],
            \"modifiers\": [
                    {'action': 'word-mask', 'entity': 'deer hunter', 'type': 'PERSON'},
                    {'action': 'ignore', 'entity': 'Mister'},
            ],
            \"redact_images\": true
    }
    ```

    **Example response format for file \"document.pdf\"**:
    ```json
    {
            \"task_id\": \"123e4567-e89b-12d3-a456-426614174000\"
    }
    ```

    Args:
        create_session (Union[Unset, bool]): If true, creates a new session for subsequent
            operations Default: False.
        body (FileMaskRequest): Request for masking PII in document files.

            Process PDF or DOCX files to identify and mask sensitive information.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[AsyncBinaryResponse, HTTPValidationError]]
     """


    kwargs = _get_kwargs(
        body=body,
create_session=create_session,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient,
    body: FileMaskRequest,
    create_session: Union[Unset, bool] = False,

) -> Optional[Union[AsyncBinaryResponse, HTTPValidationError]]:
    r""" Mask File

     Mask PII from a document file without creating a session.

    Process PDF or DOCX files to identify and mask sensitive information.
    Ideal for document anonymization where you don't need to keep track of masked
    items.

    Supports:
    - Document text masking
    - Optional image redaction
    - Configurable PII detection types

    The file should be provided as base64-encoded content in the request.
    The API supports PDF and DOCX files up to 100MB in size.

    Returns a task ID that can be used to track the progress of the file masking task and receive the
    redacted file.

    - Set **create_session=true** if you might need to unmask this data later

    **Example request**:
    ```json
    {
            \"file\": {
                    \"file_name\": \"document.pdf\",
                    \"file_content_type\": \"application/pdf\",
                    \"file_content_base64\": \"...\"
            },
            \"pii_labels\": {\"detect\": [\"ALL\"], \"ignore\": [\"EMAIL\"]},
            \"known_entities\": [
                    {\"id\": 1, \"label\": \"PERSON\", \"name\": \"Mary Jane\"}
            ],
            \"modifiers\": [
                    {'action': 'word-mask', 'entity': 'deer hunter', 'type': 'PERSON'},
                    {'action': 'ignore', 'entity': 'Mister'},
            ],
            \"redact_images\": true
    }
    ```

    **Example response format for file \"document.pdf\"**:
    ```json
    {
            \"task_id\": \"123e4567-e89b-12d3-a456-426614174000\"
    }
    ```

    Args:
        create_session (Union[Unset, bool]): If true, creates a new session for subsequent
            operations Default: False.
        body (FileMaskRequest): Request for masking PII in document files.

            Process PDF or DOCX files to identify and mask sensitive information.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[AsyncBinaryResponse, HTTPValidationError]
     """


    return (await asyncio_detailed(
        client=client,
body=body,
create_session=create_session,

    )).parsed
