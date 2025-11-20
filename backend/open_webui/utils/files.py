from open_webui.routers.images import (
    get_image_data,
    upload_image,
)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    UploadFile,
)

from open_webui.routers.files import upload_file_handler

import mimetypes
import base64
import io


def get_image_url_from_base64(request, base64_image_string, metadata, user):
    if "data:image/png;base64" in base64_image_string:
        image_url = ""
        # Extract base64 image data from the line
        image_data, content_type = get_image_data(base64_image_string)
        if image_data is not None:
            image_url = upload_image(
                request,
                image_data,
                content_type,
                metadata,
                user,
            )
        return image_url
    return None


def load_b64_audio_data(b64_str):
    try:
        if "," in b64_str:
            header, b64_data = b64_str.split(",", 1)
        else:
            b64_data = b64_str
            header = "data:audio/wav;base64"
        audio_data = base64.b64decode(b64_data)
        content_type = (
            header.split(";")[0].split(":")[1] if ";" in header else "audio/wav"
        )
        return audio_data, content_type
    except Exception as e:
        print(f"Error decoding base64 audio data: {e}")
        return None, None


def upload_audio(request, audio_data, content_type, metadata, user):
    audio_format = mimetypes.guess_extension(content_type)
    file = UploadFile(
        file=io.BytesIO(audio_data),
        filename=f"generated-{audio_format}",  # will be converted to a unique ID on upload_file
        headers={
            "content-type": content_type,
        },
    )
    file_item = upload_file_handler(
        request,
        file=file,
        metadata=metadata,
        process=False,
        user=user,
    )
    url = request.app.url_path_for("get_file_content_by_id", id=file_item.id)
    return url


def get_audio_url_from_base64(request, base64_audio_string, metadata, user):
    if "data:audio/wav;base64" in base64_audio_string:
        audio_url = ""
        # Extract base64 audio data from the line
        audio_data, content_type = load_b64_audio_data(base64_audio_string)
        if audio_data is not None:
            audio_url = upload_audio(
                request,
                audio_data,
                content_type,
                metadata,
                user,
            )
        return audio_url
    return None


def get_file_url_from_base64(request, base64_file_string, metadata, user):
    if "data:image/png;base64" in base64_file_string:
        return get_image_url_from_base64(request, base64_file_string, metadata, user)
    elif "data:audio/wav;base64" in base64_file_string:
        return get_audio_url_from_base64(request, base64_file_string, metadata, user)
    return None
