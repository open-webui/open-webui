from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.session import Session
from ...models.session_create import SessionCreate
from typing import cast



def _get_kwargs(
    *,
    body: SessionCreate,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/sessions",
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[Union[HTTPValidationError, Session]]:
    if response.status_code == 201:
        response_201 = Session.from_dict(response.json())



        return response_201
    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[Union[HTTPValidationError, Session]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: SessionCreate,

) -> Response[Union[HTTPValidationError, Session]]:
    r""" Create Session

     Create a new session for consistent PII masking and unmasking operations.

    Sessions allow you to maintain consistent PII labeling across multiple API calls.
    For example, if you mask a document and later want to unmask specific parts,
    the session ensures that masked entities are properly tracked and can be unmasked
    correctly.

    - **TTL (Time To Live)**: Specify how long the session should remain active
            (\"24h\", \"7d\", etc.)
    - **Description**: Optional note to help identify the session's purpose

    Args:
        body (SessionCreate): Parameters for creating a new masking/unmasking session.

            Sessions maintain context between multiple API calls, allowing consistent
            masking and unmasking of entities across different operations.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, Session]]
     """


    kwargs = _get_kwargs(
        body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient,
    body: SessionCreate,

) -> Optional[Union[HTTPValidationError, Session]]:
    r""" Create Session

     Create a new session for consistent PII masking and unmasking operations.

    Sessions allow you to maintain consistent PII labeling across multiple API calls.
    For example, if you mask a document and later want to unmask specific parts,
    the session ensures that masked entities are properly tracked and can be unmasked
    correctly.

    - **TTL (Time To Live)**: Specify how long the session should remain active
            (\"24h\", \"7d\", etc.)
    - **Description**: Optional note to help identify the session's purpose

    Args:
        body (SessionCreate): Parameters for creating a new masking/unmasking session.

            Sessions maintain context between multiple API calls, allowing consistent
            masking and unmasking of entities across different operations.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, Session]
     """


    return sync_detailed(
        client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: SessionCreate,

) -> Response[Union[HTTPValidationError, Session]]:
    r""" Create Session

     Create a new session for consistent PII masking and unmasking operations.

    Sessions allow you to maintain consistent PII labeling across multiple API calls.
    For example, if you mask a document and later want to unmask specific parts,
    the session ensures that masked entities are properly tracked and can be unmasked
    correctly.

    - **TTL (Time To Live)**: Specify how long the session should remain active
            (\"24h\", \"7d\", etc.)
    - **Description**: Optional note to help identify the session's purpose

    Args:
        body (SessionCreate): Parameters for creating a new masking/unmasking session.

            Sessions maintain context between multiple API calls, allowing consistent
            masking and unmasking of entities across different operations.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, Session]]
     """


    kwargs = _get_kwargs(
        body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient,
    body: SessionCreate,

) -> Optional[Union[HTTPValidationError, Session]]:
    r""" Create Session

     Create a new session for consistent PII masking and unmasking operations.

    Sessions allow you to maintain consistent PII labeling across multiple API calls.
    For example, if you mask a document and later want to unmask specific parts,
    the session ensures that masked entities are properly tracked and can be unmasked
    correctly.

    - **TTL (Time To Live)**: Specify how long the session should remain active
            (\"24h\", \"7d\", etc.)
    - **Description**: Optional note to help identify the session's purpose

    Args:
        body (SessionCreate): Parameters for creating a new masking/unmasking session.

            Sessions maintain context between multiple API calls, allowing consistent
            masking and unmasking of entities across different operations.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, Session]
     """


    return (await asyncio_detailed(
        client=client,
body=body,

    )).parsed
