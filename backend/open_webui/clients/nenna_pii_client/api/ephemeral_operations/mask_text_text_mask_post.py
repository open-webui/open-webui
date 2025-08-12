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
    *,
    body: TextMaskRequest,
    create_session: Union[Unset, bool] = False,
    quiet: Union[Unset, bool] = False,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["create_session"] = create_session

    params["quiet"] = quiet

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/text/mask",
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[HTTPValidationError, TextMaskResponse]]:
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


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[HTTPValidationError, TextMaskResponse]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: TextMaskRequest,
    create_session: Union[Unset, bool] = False,
    quiet: Union[Unset, bool] = False,
) -> Response[Union[HTTPValidationError, TextMaskResponse]]:
    r"""Mask Text

     Mask PII from text immediately without creating a session.

    Ideal for one-time anonymization needs where you don't need to unmask later.
    Quickly process text data to identify and mask PII elements like names, phone
    numbers, addresses, and more.

    - Set **quiet=true** to receive only masked text without detailed PII information
    - Set **create_session=true** if you might need to unmask this data later

    **Example request**:
    ```json
    {
            \"text\": [\"John Doe's phone number is +49 718 222 222\"],
            \"pii_labels\": {\"detect\": [\"ALL\"], \"ignore\": [\"EMAIL\"]},
            \"known_entities\": [
                    {\"id\": 1, \"label\": \"PERSON\", \"name\": \"Mary Jane\"}
            ],
            \"modifiers\": [
                    {'action': 'word-mask', 'entity': 'deer hunter', 'type': 'PERSON'},
                    {'action': 'ignore', 'entity': 'Mister'},
            ]
    }
    ```

    **Example response format for text \"John Doe's phone is +49 718 222 222\"**:
    ```json
    {
            \"text\": [\"[{PERSON_1}]'s phone number is [{PHONE_NUMBER_2}]\"],
            \"pii\": [
                    {
                            \"id\": 1,
                            \"type\": \"PHONENUMBER\",
                            \"label\": \"PHONENUMBER_1\",
                            \"text\": \"+49 718 222 222\",
                            \"raw_text\": \"+49 718 222 222\",
                            \"occurrences\": [
                                    {
                                            \"start_idx\": 27,
                                            \"end_idx\": 42
                                    }
                            ]
                    },
                    {
                            \"id\": 2,
                            \"type\": \"PERSON\",
                            \"label\": \"PERSON_2\",
                            \"text\": \"john doe\",
                            \"raw_text\": \"John Doe\",
                            \"occurrences\": [
                                    {
                                            \"start_idx\": 0,
                                            \"end_idx\": 8
                                    }
                            ]
                    }
            ]
    }
    ```

    Args:
        create_session (Union[Unset, bool]): If true, creates a new session for subsequent
            operations Default: False.
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
        body=body,
        create_session=create_session,
        quiet=quiet,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: TextMaskRequest,
    create_session: Union[Unset, bool] = False,
    quiet: Union[Unset, bool] = False,
) -> Optional[Union[HTTPValidationError, TextMaskResponse]]:
    r"""Mask Text

     Mask PII from text immediately without creating a session.

    Ideal for one-time anonymization needs where you don't need to unmask later.
    Quickly process text data to identify and mask PII elements like names, phone
    numbers, addresses, and more.

    - Set **quiet=true** to receive only masked text without detailed PII information
    - Set **create_session=true** if you might need to unmask this data later

    **Example request**:
    ```json
    {
            \"text\": [\"John Doe's phone number is +49 718 222 222\"],
            \"pii_labels\": {\"detect\": [\"ALL\"], \"ignore\": [\"EMAIL\"]},
            \"known_entities\": [
                    {\"id\": 1, \"label\": \"PERSON\", \"name\": \"Mary Jane\"}
            ],
            \"modifiers\": [
                    {'action': 'word-mask', 'entity': 'deer hunter', 'type': 'PERSON'},
                    {'action': 'ignore', 'entity': 'Mister'},
            ]
    }
    ```

    **Example response format for text \"John Doe's phone is +49 718 222 222\"**:
    ```json
    {
            \"text\": [\"[{PERSON_1}]'s phone number is [{PHONE_NUMBER_2}]\"],
            \"pii\": [
                    {
                            \"id\": 1,
                            \"type\": \"PHONENUMBER\",
                            \"label\": \"PHONENUMBER_1\",
                            \"text\": \"+49 718 222 222\",
                            \"raw_text\": \"+49 718 222 222\",
                            \"occurrences\": [
                                    {
                                            \"start_idx\": 27,
                                            \"end_idx\": 42
                                    }
                            ]
                    },
                    {
                            \"id\": 2,
                            \"type\": \"PERSON\",
                            \"label\": \"PERSON_2\",
                            \"text\": \"john doe\",
                            \"raw_text\": \"John Doe\",
                            \"occurrences\": [
                                    {
                                            \"start_idx\": 0,
                                            \"end_idx\": 8
                                    }
                            ]
                    }
            ]
    }
    ```

    Args:
        create_session (Union[Unset, bool]): If true, creates a new session for subsequent
            operations Default: False.
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
        client=client,
        body=body,
        create_session=create_session,
        quiet=quiet,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: TextMaskRequest,
    create_session: Union[Unset, bool] = False,
    quiet: Union[Unset, bool] = False,
) -> Response[Union[HTTPValidationError, TextMaskResponse]]:
    r"""Mask Text

     Mask PII from text immediately without creating a session.

    Ideal for one-time anonymization needs where you don't need to unmask later.
    Quickly process text data to identify and mask PII elements like names, phone
    numbers, addresses, and more.

    - Set **quiet=true** to receive only masked text without detailed PII information
    - Set **create_session=true** if you might need to unmask this data later

    **Example request**:
    ```json
    {
            \"text\": [\"John Doe's phone number is +49 718 222 222\"],
            \"pii_labels\": {\"detect\": [\"ALL\"], \"ignore\": [\"EMAIL\"]},
            \"known_entities\": [
                    {\"id\": 1, \"label\": \"PERSON\", \"name\": \"Mary Jane\"}
            ],
            \"modifiers\": [
                    {'action': 'word-mask', 'entity': 'deer hunter', 'type': 'PERSON'},
                    {'action': 'ignore', 'entity': 'Mister'},
            ]
    }
    ```

    **Example response format for text \"John Doe's phone is +49 718 222 222\"**:
    ```json
    {
            \"text\": [\"[{PERSON_1}]'s phone number is [{PHONE_NUMBER_2}]\"],
            \"pii\": [
                    {
                            \"id\": 1,
                            \"type\": \"PHONENUMBER\",
                            \"label\": \"PHONENUMBER_1\",
                            \"text\": \"+49 718 222 222\",
                            \"raw_text\": \"+49 718 222 222\",
                            \"occurrences\": [
                                    {
                                            \"start_idx\": 27,
                                            \"end_idx\": 42
                                    }
                            ]
                    },
                    {
                            \"id\": 2,
                            \"type\": \"PERSON\",
                            \"label\": \"PERSON_2\",
                            \"text\": \"john doe\",
                            \"raw_text\": \"John Doe\",
                            \"occurrences\": [
                                    {
                                            \"start_idx\": 0,
                                            \"end_idx\": 8
                                    }
                            ]
                    }
            ]
    }
    ```

    Args:
        create_session (Union[Unset, bool]): If true, creates a new session for subsequent
            operations Default: False.
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
        body=body,
        create_session=create_session,
        quiet=quiet,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: TextMaskRequest,
    create_session: Union[Unset, bool] = False,
    quiet: Union[Unset, bool] = False,
) -> Optional[Union[HTTPValidationError, TextMaskResponse]]:
    r"""Mask Text

     Mask PII from text immediately without creating a session.

    Ideal for one-time anonymization needs where you don't need to unmask later.
    Quickly process text data to identify and mask PII elements like names, phone
    numbers, addresses, and more.

    - Set **quiet=true** to receive only masked text without detailed PII information
    - Set **create_session=true** if you might need to unmask this data later

    **Example request**:
    ```json
    {
            \"text\": [\"John Doe's phone number is +49 718 222 222\"],
            \"pii_labels\": {\"detect\": [\"ALL\"], \"ignore\": [\"EMAIL\"]},
            \"known_entities\": [
                    {\"id\": 1, \"label\": \"PERSON\", \"name\": \"Mary Jane\"}
            ],
            \"modifiers\": [
                    {'action': 'word-mask', 'entity': 'deer hunter', 'type': 'PERSON'},
                    {'action': 'ignore', 'entity': 'Mister'},
            ]
    }
    ```

    **Example response format for text \"John Doe's phone is +49 718 222 222\"**:
    ```json
    {
            \"text\": [\"[{PERSON_1}]'s phone number is [{PHONE_NUMBER_2}]\"],
            \"pii\": [
                    {
                            \"id\": 1,
                            \"type\": \"PHONENUMBER\",
                            \"label\": \"PHONENUMBER_1\",
                            \"text\": \"+49 718 222 222\",
                            \"raw_text\": \"+49 718 222 222\",
                            \"occurrences\": [
                                    {
                                            \"start_idx\": 27,
                                            \"end_idx\": 42
                                    }
                            ]
                    },
                    {
                            \"id\": 2,
                            \"type\": \"PERSON\",
                            \"label\": \"PERSON_2\",
                            \"text\": \"john doe\",
                            \"raw_text\": \"John Doe\",
                            \"occurrences\": [
                                    {
                                            \"start_idx\": 0,
                                            \"end_idx\": 8
                                    }
                            ]
                    }
            ]
    }
    ```

    Args:
        create_session (Union[Unset, bool]): If true, creates a new session for subsequent
            operations Default: False.
        quiet (Union[Unset, bool]): If true, omits PII details from response for reduced verbosity
            Default: False.
        body (TextMaskRequest): Request for masking PII in text data.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, TextMaskResponse]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            create_session=create_session,
            quiet=quiet,
        )
    ).parsed
