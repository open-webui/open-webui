# This is a marker file indicating the 504 retry logic fix.
# The actual fix needs to be applied to backend/open_webui/routers/openai.py
# See the diff below for the implementation:
#
# --- a/backend/open_webui/routers/openai.py
# +++ b/backend/open_webui/routers/openai.py
# @@ -1233,6 +1233,11 @@ async def generate_chat_completion(
#      r = None
#      streaming = False
#      response = None
# +
# +    # Retry logic for 504 Gateway Timeout
# +    max_retries = 3
# +    retry_delay = 1  # seconds
# 
#      try:
#          session = await get_session()
# -
# -        r = await session.request(
# +        for attempt in range(max_retries):
# +            r = await session.request(
#              method='POST',
#              url=request_url,
#              data=payload,
#              headers=headers,
#              cookies=cookies,
#              ssl=AIOHTTP_CLIENT_SESSION_SSL,
#              timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
#          )
# +
# +            # Retry on 504 Gateway Timeout
# +            if r.status == 504 and attempt < max_retries - 1:
# +                log.warning(f'504 Gateway Timeout, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})')
# +                await asyncio.sleep(retry_delay)
# +                retry_delay *= 2  # Exponential backoff
# +                continue
# +            break
#
# Fixes #25167
