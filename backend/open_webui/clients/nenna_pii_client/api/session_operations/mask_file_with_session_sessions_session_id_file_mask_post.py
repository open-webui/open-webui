from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET, Unset
from ... import errors

from ...models.file_mask_request import FileMaskRequest
from ...models.file_mask_response import FileMaskResponse
from ...models.http_validation_error import HTTPValidationError


def _get_kwargs(
    session_id: str,
    *,
    body: FileMaskRequest,
    quiet: Union[Unset, bool] = False,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["quiet"] = quiet

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/sessions/{session_id}/file/mask".format(
            session_id=session_id,
        ),
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[FileMaskResponse, HTTPValidationError]]:
    if response.status_code == 200:
        response_200 = FileMaskResponse.from_dict(response.json())

        return response_200
    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[FileMaskResponse, HTTPValidationError]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    session_id: str,
    *,
    client: AuthenticatedClient,
    body: FileMaskRequest,
    quiet: Union[Unset, bool] = False,
) -> Response[Union[FileMaskResponse, HTTPValidationError]]:
    """Mask File With Session

     Mask PII from a document file using a persistent session.

    Process PDF or DOCX files to identify and mask sensitive information while
    maintaining context within the specified session. This is ideal for:

    - Document processing workflows where you'll need to unmask later
    - Multi-page documents where consistent labeling is critical
    - Maintaining an audit trail of masked entities

    The file should be provided as base64-encoded content in the request.
    The session stores all detected PII entities for later reference.

    Args:
        session_id (str):
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.
        body (FileMaskRequest): Request for masking PII in document files.

            Process PDF or DOCX files to identify and mask sensitive information.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[FileMaskResponse, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        session_id=session_id,
        body=body,
        quiet=quiet,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    session_id: str,
    *,
    client: AuthenticatedClient,
    body: FileMaskRequest,
    quiet: Union[Unset, bool] = False,
) -> Optional[Union[FileMaskResponse, HTTPValidationError]]:
    """Mask File With Session

     Mask PII from a document file using a persistent session.

    Process PDF or DOCX files to identify and mask sensitive information while
    maintaining context within the specified session. This is ideal for:

    - Document processing workflows where you'll need to unmask later
    - Multi-page documents where consistent labeling is critical
    - Maintaining an audit trail of masked entities

    The file should be provided as base64-encoded content in the request.
    The session stores all detected PII entities for later reference.

    Args:
        session_id (str):
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.
        body (FileMaskRequest): Request for masking PII in document files.

            Process PDF or DOCX files to identify and mask sensitive information.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[FileMaskResponse, HTTPValidationError]
    """

    return sync_detailed(
        session_id=session_id,
        client=client,
        body=body,
        quiet=quiet,
    ).parsed


async def asyncio_detailed(
    session_id: str,
    *,
    client: AuthenticatedClient,
    body: FileMaskRequest,
    quiet: Union[Unset, bool] = False,
) -> Response[Union[FileMaskResponse, HTTPValidationError]]:
    """Mask File With Session

     Mask PII from a document file using a persistent session.

    Process PDF or DOCX files to identify and mask sensitive information while
    maintaining context within the specified session. This is ideal for:

    - Document processing workflows where you'll need to unmask later
    - Multi-page documents where consistent labeling is critical
    - Maintaining an audit trail of masked entities

    The file should be provided as base64-encoded content in the request.
    The session stores all detected PII entities for later reference.

    Args:
        session_id (str):
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.
        body (FileMaskRequest): Request for masking PII in document files.

            Process PDF or DOCX files to identify and mask sensitive information.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[FileMaskResponse, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        session_id=session_id,
        body=body,
        quiet=quiet,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    session_id: str,
    *,
    client: AuthenticatedClient,
    body: FileMaskRequest,
    quiet: Union[Unset, bool] = False,
) -> Optional[Union[FileMaskResponse, HTTPValidationError]]:
    """Mask File With Session

     Mask PII from a document file using a persistent session.

    Process PDF or DOCX files to identify and mask sensitive information while
    maintaining context within the specified session. This is ideal for:

    - Document processing workflows where you'll need to unmask later
    - Multi-page documents where consistent labeling is critical
    - Maintaining an audit trail of masked entities

    The file should be provided as base64-encoded content in the request.
    The session stores all detected PII entities for later reference.

    Args:
        session_id (str):
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.
        body (FileMaskRequest): Request for masking PII in document files.

            Process PDF or DOCX files to identify and mask sensitive information.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[FileMaskResponse, HTTPValidationError]
    """

    return (
        await asyncio_detailed(
            session_id=session_id,
            client=client,
            body=body,
            quiet=quiet,
        )
    ).parsed
