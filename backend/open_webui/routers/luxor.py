import logging
import aiohttp
import os
import json
from typing import Optional, Union
from fastapi import (
    HTTPException,
)
from open_webui.env import (
    SRC_LOG_LEVELS,
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


async def generate_chat_completion(form_data: dict):
    url = os.environ['LIVE_URL']
    log.info(f"URL: {url}") 
    return await send_post_request(
        url=url,
        payload=json.dumps(form_data),
    )

# CGH TODO Support Streaming
async def send_post_request(
        url: str,
        payload: Union[str, bytes],
):
    r = None
    try:
        session = aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        )
        r = await session.post(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
            },
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )
        # CGH Todo remove code accounting for lack of aws gateway
        if r.ok is False:
            try:
                res = await r.json()
                await cleanup_response(r, session)
                if "error" in res:
                    raise HTTPException(status_code=r.status, detail=res["error"])
            except HTTPException as e:
                raise e  # Re-raise HTTPException to be handled by FastAPI
            except Exception as e:
                log.error(f"Failed to parse error response: {e}")
                raise HTTPException(
                    status_code=r.status,
                    detail=f"Open WebUI: Server Connection Error",
                )
            
        raw_body = await r.text()

        log.info(f"RAW BODY: {raw_body}")

        r.raise_for_status()  # Raises an error for bad responses (4xx, 5xx)\
        
        try:
            res = json.loads(raw_body)  # works when Lambda returns JSON
            log.info("LAMBDA")
        except json.JSONDecodeError:
            log.info("DOCKER")
            res = {"statusCode": r.status, "body": raw_body}

        log.info(f"RES: {res}")
        if isinstance(res, dict) and "body" in res:
            body = res["body"]
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    body = {"txt_answer": body}
            elif not isinstance(body, dict):
                body = {"txt_answer": str(body)}
            res["data"] = body 
            
        log.info(f"RES: {res}")
        return res      
    except HTTPException as e:
        raise e  # Re-raise HTTPException to be handled by FastAPI
    except Exception as e:
        detail = f"Luxor: {e}"

        raise HTTPException(
            status_code=r.status if r else 500,
            detail=detail if e else "Open WebUI: Server Connection Error",
        )
    finally:
        await cleanup_response(r, session)


async def cleanup_response(
    response: Optional[aiohttp.ClientResponse],
    session: Optional[aiohttp.ClientSession],
):
    if response:
        response.close()
    if session:
        await session.close()

    


    
    
