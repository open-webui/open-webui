from open_webui.routers.images import (
    load_b64_image_data,
    upload_image,
)


def get_image_url_from_base64(request, base64_image_string, metadata, user):
    if "data:image/png;base64" in base64_image_string:
        image_url = ""
        # Extract base64 image data from the line
        image_data, content_type = load_b64_image_data(base64_image_string)
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
