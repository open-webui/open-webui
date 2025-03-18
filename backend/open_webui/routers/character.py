from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Request
import logging

from open_webui.models.character import (
    CharacterUserModel,
    CharacterUserResponse,
    Character,
    Characters,
    CharacterForm
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_access, has_permission


from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.models import Models, ModelForm


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


############################
# GetKnowledgeList
############################

@router.get("/list", response_model=list[CharacterUserResponse])
async def get_characters():
    characters = Characters.get_characters()
    
    # if user.role == 'admin':
    #     characters = Character.get_characters()
    # else:
    #     characters = Characters.get_characters_by_user_id(user.id)

    return characters


############################
# CreateNewKnowledge
############################


@router.post("/create", response_model=Optional[CharacterUserModel])
async def create_new_character(
    request: Request, form_data: CharacterForm, user=Depends(get_verified_user)
):
    print('!!!!creating new character')
    
    character = Characters.insert_new_character(user.id, form_data.title, form_data.system_prompt)

    if character:
        return character
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_EXISTS,
        )


@router.delete('/{id}/delete', response_model=bool)
async def delete_knowledge_by_id(id: str, user=Depends(get_verified_user)):
    character = Characters.get_character_by_id(id=id)
    if not character:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    result = Characters.delete_character_by_id(id=id)
    return result