from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET, Unset
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.text_mask_request import TextMaskRequest
from ...models.text_mask_response import TextMaskResponse



def _get_kwargs(
    session_id: str,
    *,
    body: TextMaskRequest,
    quiet: Union[Unset, bool] = False,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}


    

    params: dict[str, Any] = {}

    params["quiet"] = quiet


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/sessions/{session_id}/text/mask".format(session_id=session_id,),
        "params": params,
    }

    _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[Union[HTTPValidationError, TextMaskResponse]]:
    if response.status_code == 200:
        response_200 = TextMaskResponse.from_dict(response.json())



        return response_200
    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[Union[HTTPValidationError, TextMaskResponse]]:
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
    body: TextMaskRequest,
    quiet: Union[Unset, bool] = False,

) -> Response[Union[HTTPValidationError, TextMaskResponse]]:
    """ Mask Text With Session

     Mask PII from text using a persistent session.

    This endpoint masks sensitive information in text data and stores the context
    within the specified session. Use session-based masking when you need to:

    - Maintain consistent PII labels across multiple texts
    - Unmask the data later using the same session
    - Process data as part of a multi-step workflow

    The session keeps track of all masked entities, allowing for precise unmasking
    even across different API calls.

    Args:
        session_id (str):
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.
        body (TextMaskRequest): Request for masking PII in text data.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, TextMaskResponse]]
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
    body: TextMaskRequest,
    quiet: Union[Unset, bool] = False,

) -> Optional[Union[HTTPValidationError, TextMaskResponse]]:
    """ Mask Text With Session

     Mask PII from text using a persistent session.

    This endpoint masks sensitive information in text data and stores the context
    within the specified session. Use session-based masking when you need to:

    - Maintain consistent PII labels across multiple texts
    - Unmask the data later using the same session
    - Process data as part of a multi-step workflow

    The session keeps track of all masked entities, allowing for precise unmasking
    even across different API calls.

    Args:
        session_id (str):
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.
        body (TextMaskRequest): Request for masking PII in text data.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, TextMaskResponse]
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
    body: TextMaskRequest,
    quiet: Union[Unset, bool] = False,

) -> Response[Union[HTTPValidationError, TextMaskResponse]]:
    """ Mask Text With Session

     Mask PII from text using a persistent session.

    This endpoint masks sensitive information in text data and stores the context
    within the specified session. Use session-based masking when you need to:

    - Maintain consistent PII labels across multiple texts
    - Unmask the data later using the same session
    - Process data as part of a multi-step workflow

    The session keeps track of all masked entities, allowing for precise unmasking
    even across different API calls.

    Args:
        session_id (str):
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.
        body (TextMaskRequest): Request for masking PII in text data.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, TextMaskResponse]]
     """


    kwargs = _get_kwargs(
        session_id=session_id,
body=body,
quiet=quiet,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    session_id: str,
    *,
    client: AuthenticatedClient,
    body: TextMaskRequest,
    quiet: Union[Unset, bool] = False,

) -> Optional[Union[HTTPValidationError, TextMaskResponse]]:
    """ Mask Text With Session

     Mask PII from text using a persistent session.

    This endpoint masks sensitive information in text data and stores the context
    within the specified session. Use session-based masking when you need to:

    - Maintain consistent PII labels across multiple texts
    - Unmask the data later using the same session
    - Process data as part of a multi-step workflow

    The session keeps track of all masked entities, allowing for precise unmasking
    even across different API calls.

    Args:
        session_id (str):
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.
        body (TextMaskRequest): Request for masking PII in text data.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, TextMaskResponse]
     """


    return (await asyncio_detailed(
        session_id=session_id,
client=client,
body=body,
quiet=quiet,

    )).parsed
