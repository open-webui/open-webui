from fastapi import HTTPException
from open_webui.utils.auth import create_token, decode_token, get_verified_user_by_id


def browser_ticket(server_id, user_id, chat_id, session, headers=None, cookies=None):
    from open_webui.utils.oauth import encrypt_data

    relay = encrypt_data(
        {
            'authorization': (headers or {}).get('Authorization'),
            'cookies': cookies or {},
        }
    )
    return create_token(
        {
            'purpose': 'terminal-browser',
            'server': server_id,
            'user': user_id,
            'chat': chat_id,
            'session': session['id'],
            'capability': session['token'],
            'relay': relay,
        },
    )


async def browser_access(server_id, sid, ticket):
    data = decode_token(ticket)
    if (
        not data
        or data.get('purpose') != 'terminal-browser'
        or data.get('server') != server_id
        or data.get('session') != sid
    ):
        raise HTTPException(401, 'Browser session expired')
    user = await get_verified_user_by_id(data.get('user'))
    if user is None:
        raise HTTPException(401, 'Browser session expired')
    from open_webui.utils.oauth import decrypt_data

    data['relay'] = decrypt_data(data['relay'])
    return user, data
