from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.response_delete_session_sessions_session_id_delete import ResponseDeleteSessionSessionsSessionIdDelete
from typing import cast



def _get_kwargs(
    session_id: str,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/sessions/{session_id}".format(session_id=session_id,),
    }


    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[Union[HTTPValidationError, ResponseDeleteSessionSessionsSessionIdDelete]]:
    if response.status_code == 200:
        response_200 = ResponseDeleteSessionSessionsSessionIdDelete.from_dict(response.json())



        return response_200
    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[Union[HTTPValidationError, ResponseDeleteSessionSessionsSessionIdDelete]]:
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

) -> Response[Union[HTTPValidationError, ResponseDeleteSessionSessionsSessionIdDelete]]:
    """ Delete Session

     Delete a session and all associated data.

    When you're done with a session, it's a good practice to delete it to free up
    resources and ensure sensitive data isn't retained unnecessarily. This operation
    permanently removes the session and any PII entities stored within it.

    Args:
        session_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, ResponseDeleteSessionSessionsSessionIdDelete]]
     """


    kwargs = _get_kwargs(
        session_id=session_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    session_id: str,
    *,
    client: AuthenticatedClient,

) -> Optional[Union[HTTPValidationError, ResponseDeleteSessionSessionsSessionIdDelete]]:
    """ Delete Session

     Delete a session and all associated data.

    When you're done with a session, it's a good practice to delete it to free up
    resources and ensure sensitive data isn't retained unnecessarily. This operation
    permanently removes the session and any PII entities stored within it.

    Args:
        session_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, ResponseDeleteSessionSessionsSessionIdDelete]
     """


    return sync_detailed(
        session_id=session_id,
client=client,

    ).parsed

async def asyncio_detailed(
    session_id: str,
    *,
    client: AuthenticatedClient,

) -> Response[Union[HTTPValidationError, ResponseDeleteSessionSessionsSessionIdDelete]]:
    """ Delete Session

     Delete a session and all associated data.

    When you're done with a session, it's a good practice to delete it to free up
    resources and ensure sensitive data isn't retained unnecessarily. This operation
    permanently removes the session and any PII entities stored within it.

    Args:
        session_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, ResponseDeleteSessionSessionsSessionIdDelete]]
     """


    kwargs = _get_kwargs(
        session_id=session_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    session_id: str,
    *,
    client: AuthenticatedClient,

) -> Optional[Union[HTTPValidationError, ResponseDeleteSessionSessionsSessionIdDelete]]:
    """ Delete Session

     Delete a session and all associated data.

    When you're done with a session, it's a good practice to delete it to free up
    resources and ensure sensitive data isn't retained unnecessarily. This operation
    permanently removes the session and any PII entities stored within it.

    Args:
        session_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, ResponseDeleteSessionSessionsSessionIdDelete]
     """


    return (await asyncio_detailed(
        session_id=session_id,
client=client,

    )).parsed
