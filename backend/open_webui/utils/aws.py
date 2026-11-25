import asyncio
import re
from functools import lru_cache

import aiohttp
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

# An Authorization header with this value and no signature asks sign_aws_request for one.
AWS_SIGV4 = 'AWS4-HMAC-SHA256'

BEDROCK_HOST_PATTERN = re.compile(
    r'(?:^|\.)(bedrock-runtime|bedrock-mantle)(?:-fips)?\.([a-z0-9-]+)\.'
    r'(?:vpce\.)?(?:amazonaws\.com|amazonaws\.com\.cn|amazonaws\.eu|api\.aws)$'
)


@lru_cache(maxsize=1)
def get_aws_session() -> boto3.Session:
    return boto3.Session()


def get_aws_sigv4_headers(method: str, url: str, headers: dict, body: bytes, service: str, region: str) -> dict:
    credentials = get_aws_session().get_credentials()
    if credentials:
        credentials = credentials.get_frozen_credentials()

    request = AWSRequest(method=method, url=url, headers=headers, data=body)
    # Raises NoCredentialsError when the default credential chain finds nothing.
    SigV4Auth(credentials, service, region).add_auth(request)
    return dict(request.headers.items())


async def sign_aws_request(
    request: aiohttp.ClientRequest, handler: aiohttp.ClientHandlerType
) -> aiohttp.ClientResponse:
    """aiohttp client middleware: the signature covers the URL and body, so it is added to the final request."""
    if request.headers.get('Authorization') == AWS_SIGV4:
        match = BEDROCK_HOST_PATTERN.search(request.url.host or '')
        if not match:
            raise ValueError(f'AWS SigV4 authentication only supports Amazon Bedrock URLs, not {request.url.host}')

        endpoint, region = match.groups()
        signed_headers = await asyncio.to_thread(
            get_aws_sigv4_headers,
            request.method,
            str(request.url),
            # Other headers may be changed by a proxy on the way, which would break the signature.
            {k: v for k, v in request.headers.items() if k.lower() == 'content-type' or k.lower().startswith('x-amz-')},
            await request.body.as_bytes() if request.body else b'',
            'bedrock' if endpoint == 'bedrock-runtime' else endpoint,
            region,
        )
        request.headers.update(signed_headers)

    return await handler(request)
