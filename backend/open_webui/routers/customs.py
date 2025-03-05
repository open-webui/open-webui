import uuid
import time
import datetime
import logging
from functools import wraps

from open_webui.models.auths import (
    Auths,
    UserModel,
)
from open_webui.models.groups import GroupForm, GroupUpdateForm
from open_webui.models.users import Users
from open_webui.models.groups import Groups

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import (
    WEBUI_AUTH_COOKIE_SAME_SITE,
    WEBUI_AUTH_COOKIE_SECURE,
)
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from open_webui.utils.misc import parse_duration
from open_webui.utils.auth import (
    create_token,
)


router = APIRouter()


def _exception_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logging.error(str(e))
            raise HTTPException(status_code=500, detail=str(e))

    return wrapper


@router.get("/")
@_exception_handler
def custom_index():
    return {"message": "This is KOSCOM Custom API"}


@router.post("/auths/signin")
@_exception_handler
async def custom_signin(request: Request, response: Response):
    data = await request.json()
    name = data.get("name")
    email = data.get("email")
    image = data.get("image")
    groups = data.get("groups")

    user = Users.get_user_by_email(email)

    # Clear any existing cookie token
    response.delete_cookie("token")

    def generate_and_set_cookie(user):
        expires_delta = parse_duration(request.app.state.config.JWT_EXPIRES_IN)
        token = create_token(data={"id": user.id}, expires_delta=expires_delta)
        expires_at = int(time.time()) + int(expires_delta.total_seconds()) if expires_delta else None
        datetime_expires_at = (
            datetime.datetime.fromtimestamp(expires_at, datetime.timezone.utc)
            if expires_at
            else None
        )
        response.set_cookie(
            key="token",
            value=token,
            expires=datetime_expires_at,
            httponly=True,
            samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
            secure=WEBUI_AUTH_COOKIE_SECURE,
        )
        return token, expires_at

    if not isinstance(user, UserModel):
        role = "admin" if Users.get_num_users() == 0 else request.app.state.config.DEFAULT_USER_ROLE
        user = Auths.insert_new_auth(email.lower(), str(uuid.uuid4()), name, image, role)

        try:
            if not user:
                raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_USER_ERROR)

            if groups:
                # Process groups: create new ones or update existing
                existing_groups = {grp.name: grp for grp in Groups.get_groups()}
                for group_name in groups:
                    if group_name not in existing_groups:
                        group_form = GroupForm(name=group_name, description="", permissions={})
                        new_group = Groups.insert_new_group(user.id, group_form)
                        existing_groups[group_name] = new_group

                    updated_user_ids = list(set(existing_groups[group_name].user_ids + [user.id]))
                    update_form = GroupUpdateForm(
                        name=existing_groups[group_name].name,
                        description=existing_groups[group_name].description,
                        user_ids=updated_user_ids,
                        permissions=existing_groups[group_name].permissions,
                    )
                    Groups.update_group_by_id(id=existing_groups[group_name].id, form_data=update_form)

            token, expires_at = generate_and_set_cookie(user)

        except Exception as e:
            Auths.delete_auth_by_id(user.id)
            response.delete_cookie("token")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        token, expires_at = generate_and_set_cookie(user)

    return {
        "token": token,
        "token_type": "Bearer",
        "expires_at": expires_at,
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "profile_image_url": user.profile_image_url,
    }
