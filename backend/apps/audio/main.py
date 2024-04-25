import os
import logging
import tempfile
from fastapi import (
    FastAPI,
    Request,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel

from constants import ERROR_MESSAGES
from utils.utils import (
    decode_token,
    get_current_user,
    get_verified_user,
    get_admin_user,
)
from utils.misc import calculate_sha256
import requests
from config import (
    SRC_LOG_LEVELS,
    UPLOAD_DIR,
    WHISPER_MODEL,
    WHISPER_MODEL_DIR,
    HEADERS,
    NEXTCLOUD_USERNAME,
    NEXTCLOUD_PASSWORD
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["AUDIO"])

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/transcribe")
def transcribe(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    log.info(f"file.content_type: {file.content_type}")

    if file.content_type not in ["audio/mpeg", "audio/wav"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_NOT_SUPPORTED,
        )

    try:
        filename = file.filename
        file_path = f"{UPLOAD_DIR}/{filename}"
        contents = file.file.read()
        with tempfile.NamedTemporaryFile(mode='w', delete= False) as temp_file:
            temp_file.write(contents)
            temp_file.close()

        model = WhisperModel(
            WHISPER_MODEL,
            device="auto",
            compute_type="int8",
            download_root=WHISPER_MODEL_DIR,
        )

        segments, info = model.transcribe(temp_file.name, beam_size=5)
        log.info(
            "Detected language '%s' with probability %f"
            % (info.language, info.language_probability)
        )

        transcript = "".join([segment.text for segment in list(segments)])

        text = {"text": transcript.strip()}
        
        response = requests.put(file_path, data=text, auth=(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD), headers=HEADERS)
        if 200 <= response.status_code <= 299:
            log.info("Transcript uploaded successfully.")
        else:
            print(f"Failed to upload transcript. Status code: {response.status_code}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to upload transcript. Status code: {response.status_code}"
            )
        return {"text": transcript.strip()}

    except Exception as e:
        log.exception(e)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )
