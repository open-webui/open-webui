from fastapi import Response
from fastapi import Depends, FastAPI, HTTPException, status
from datetime import datetime, timedelta
from typing import List, Union

from fastapi import APIRouter
from pydantic import BaseModel
import time
import uuid
import os

import requests
import json

from apps.web.models.auths import (
    SigninForm,
    SignupForm,
    UserResponse,
    SigninResponse,
    Auths,
)
from apps.web.models.users import Users


from utils.utils import (
    get_password_hash,
    bearer_scheme,
    create_token,
)
from utils.misc import get_gravatar_url
from constants import ERROR_MESSAGES


router = APIRouter()

############################
# GetSessionUser
############################


@router.get("/", response_model=UserResponse)
async def get_session_user(cred=Depends(bearer_scheme)):
    token = cred.credentials
    user = Users.get_user_by_token(token)
    if user:
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "profile_image_url": user.profile_image_url,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.INVALID_TOKEN,
        )


############################
# SignIn
############################


@router.post("/signin", response_model=SigninResponse)
async def signin(form_data: SigninForm):
    user = Auths.authenticate_user(form_data.email.lower(), form_data.password)
    if user:
        token = create_token(data={"email": user.email})

        return {
            "token": token,
            "token_type": "Bearer",
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "profile_image_url": user.profile_image_url,
        }
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)


############################
# SignUp
############################

# Allows users to register straight away without admin approval
initial_role = os.environ.get("INITIAL_ROLE", "user")
initial_credits = os.environ.get("INITIAL_CREDITS", 5)

@router.post("/signup", response_model=SigninResponse)
async def signup(form_data: SignupForm):
    if not Users.get_user_by_email(form_data.email.lower()):
        try:
            role = "admin" if Users.get_num_users() == 0 else initial_role
            hashed = get_password_hash(form_data.password)
            user = Auths.insert_new_auth(
                form_data.email.lower(), hashed, form_data.name, role
            )

            if user:
                token = create_token(data={"email": user.email})
                
                print(f"user {user.email} created")
                # Create user in Meteron and top them up with initial credits
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + os.environ["METERON_API_KEY"]
                }
                requests.put("https://app.meteron.ai/api/credits", headers=headers, data=json.dumps({
                    "user": user.email,
                    "amount": initial_credits
                }))
                                

                return {
                    "token": token,
                    "token_type": "Bearer",
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "profile_image_url": user.profile_image_url,
                }
            else:
                raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_USER_ERROR)
        except Exception as err:
            raise HTTPException(500, detail=ERROR_MESSAGES.DEFAULT(err))
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)
