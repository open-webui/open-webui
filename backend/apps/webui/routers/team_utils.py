from pathlib import Path
import site

from apps.webui.models.users import Team_User as Users

from fastapi import APIRouter, UploadFile, File, Response
from fastapi import Depends, HTTPException, status
from starlette.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from io import StringIO
import csv
from fpdf import FPDF
import markdown
import black


from utils.utils import get_admin_user
from utils.misc import calculate_sha256, get_gravatar_url

from config import OLLAMA_BASE_URLS, DATA_DIR, UPLOAD_DIR, ENABLE_ADMIN_EXPORT
from constants import ERROR_MESSAGES
from typing import List

router = APIRouter()


@router.get("/db/downloadMembers")
async def download_members(user=Depends(get_admin_user)):
    if not ENABLE_ADMIN_EXPORT:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    if not isinstance(DB, SqliteDatabase):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DB_NOT_SQLITE,
        )

    def iter_csv():
        output = StringIO()
        writer = csv.writer(output)

        # Get the field names from the User model
        field_names = [field.name for field in Users._meta.sorted_fields]
        writer.writerow(field_names)

        # set default parameters for the get_users method
        users = Users.get_users()
        for user in users:
            writer.writerow([getattr(user, field) for field in field_names])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    response = StreamingResponse(iter_csv(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=users.csv"
    return response
