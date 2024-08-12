from pathlib import Path
import site

from apps.webui.models.users import Users

from apps.webui.internal.db import engine
from peewee import SqliteDatabase

from fastapi import APIRouter, UploadFile, File, Response
from fastapi import Depends, HTTPException, status
from starlette.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from io import StringIO
import csv
from utils.utils import get_admin_user
from config import ENABLE_ADMIN_EXPORT
from constants import ERROR_MESSAGES

router = APIRouter()


@router.get("/db/downloadMembers")
async def download_members(user=Depends(get_admin_user)):
    if not ENABLE_ADMIN_EXPORT:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    def iter_csv():
        output = StringIO()
        writer = csv.writer(output)

        # Get the field names from the Team_User model
        field_names = Users.get_user_field_names()
        writer.writerow(field_names)

        # Fetch users
        users = Users.get_users()
        for user in users:
            writer.writerow([getattr(user, field) for field in field_names])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    response = StreamingResponse(iter_csv(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=users.csv"
    return response
