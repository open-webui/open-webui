from http import HTTPStatus
from typing import Any, Optional, Union, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET, Unset
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.text_unmask_request import TextUnmaskRequest
from ...models.text_unmask_response import TextUnmaskResponse


def _get_kwargs(
    *,
    body: TextUnmaskRequest,
    quiet: Union[Unset, bool] = False,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["quiet"] = quiet

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/text/unmask",
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, TextUnmaskResponse]]:
    if response.status_code == 200:
        response_200 = TextUnmaskResponse.from_dict(response.json())

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
) -> Response[Union[HTTPValidationError, TextUnmaskResponse]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: TextUnmaskRequest,
    quiet: Union[Unset, bool] = False,
) -> Response[Union[HTTPValidationError, TextUnmaskResponse]]:
    r"""Unmask Text

     Unmask previously masked text without using a session.

    Use this when you need to reveal original PII in masked text without a session.
    Since ephemeral calls don't store context, you must provide the entities
    for unmasking in your request.

    **Note**: For consistent unmasking, especially across multiple calls,
    session-based endpoints are recommended.

    **Example request**:
    ```json
    {
            \"text\": [\"[{PERSON_1}]'s phone is [{PHONENUMBER_2}]\"],
            \"entities\": [
                    {\"label\": \"PERSON_1\", \"text\": \"John Doe\"},
                    {\"label\": \"PHONENUMBER_2\", \"text\": \"+49 718 222 222\"}
            ]
    }
    ```

    Args:
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.
        body (TextUnmaskRequest): Request for unmasking previously masked text.

            When used with a session-based endpoint, the original values will be retrieved
            from the session. For ephemeral operations, provide the entities mapping.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, TextUnmaskResponse]]
    """

    kwargs = _get_kwargs(
        body=body,
        quiet=quiet,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: TextUnmaskRequest,
    quiet: Union[Unset, bool] = False,
) -> Optional[Union[HTTPValidationError, TextUnmaskResponse]]:
    r"""Unmask Text

     Unmask previously masked text without using a session.

    Use this when you need to reveal original PII in masked text without a session.
    Since ephemeral calls don't store context, you must provide the entities
    for unmasking in your request.

    **Note**: For consistent unmasking, especially across multiple calls,
    session-based endpoints are recommended.

    **Example request**:
    ```json
    {
            \"text\": [\"[{PERSON_1}]'s phone is [{PHONENUMBER_2}]\"],
            \"entities\": [
                    {\"label\": \"PERSON_1\", \"text\": \"John Doe\"},
                    {\"label\": \"PHONENUMBER_2\", \"text\": \"+49 718 222 222\"}
            ]
    }
    ```

    Args:
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.
        body (TextUnmaskRequest): Request for unmasking previously masked text.

            When used with a session-based endpoint, the original values will be retrieved
            from the session. For ephemeral operations, provide the entities mapping.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, TextUnmaskResponse]
    """

    return sync_detailed(
        client=client,
        body=body,
        quiet=quiet,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: TextUnmaskRequest,
    quiet: Union[Unset, bool] = False,
) -> Response[Union[HTTPValidationError, TextUnmaskResponse]]:
    r"""Unmask Text

     Unmask previously masked text without using a session.

    Use this when you need to reveal original PII in masked text without a session.
    Since ephemeral calls don't store context, you must provide the entities
    for unmasking in your request.

    **Note**: For consistent unmasking, especially across multiple calls,
    session-based endpoints are recommended.

    **Example request**:
    ```json
    {
            \"text\": [\"[{PERSON_1}]'s phone is [{PHONENUMBER_2}]\"],
            \"entities\": [
                    {\"label\": \"PERSON_1\", \"text\": \"John Doe\"},
                    {\"label\": \"PHONENUMBER_2\", \"text\": \"+49 718 222 222\"}
            ]
    }
    ```

    Args:
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.
        body (TextUnmaskRequest): Request for unmasking previously masked text.

            When used with a session-based endpoint, the original values will be retrieved
            from the session. For ephemeral operations, provide the entities mapping.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, TextUnmaskResponse]]
    """

    kwargs = _get_kwargs(
        body=body,
        quiet=quiet,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: TextUnmaskRequest,
    quiet: Union[Unset, bool] = False,
) -> Optional[Union[HTTPValidationError, TextUnmaskResponse]]:
    r"""Unmask Text

     Unmask previously masked text without using a session.

    Use this when you need to reveal original PII in masked text without a session.
    Since ephemeral calls don't store context, you must provide the entities
    for unmasking in your request.

    **Note**: For consistent unmasking, especially across multiple calls,
    session-based endpoints are recommended.

    **Example request**:
    ```json
    {
            \"text\": [\"[{PERSON_1}]'s phone is [{PHONENUMBER_2}]\"],
            \"entities\": [
                    {\"label\": \"PERSON_1\", \"text\": \"John Doe\"},
                    {\"label\": \"PHONENUMBER_2\", \"text\": \"+49 718 222 222\"}
            ]
    }
    ```

    Args:
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.
        body (TextUnmaskRequest): Request for unmasking previously masked text.

            When used with a session-based endpoint, the original values will be retrieved
            from the session. For ephemeral operations, provide the entities mapping.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, TextUnmaskResponse]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            quiet=quiet,
        )
    ).parsed
