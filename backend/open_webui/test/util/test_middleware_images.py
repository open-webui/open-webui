import asyncio

from open_webui.utils.chat_image_payload import append_chat_file_images_to_user_messages


def test_append_chat_file_images_to_user_messages_injects_image_parts():
    form_data = {"messages": [{"role": "user", "content": "Describe this image"}]}
    messages_map = {
        "msg-1": {
            "id": "msg-1",
            "role": "user",
            "content": "Describe this image",
            "parentId": None,
            "files": [
                {
                    "id": "file-1",
                    "url": "file-1",
                    "content_type": "image/png",
                    "type": "file",
                }
            ],
        }
    }

    updated = asyncio.run(
        append_chat_file_images_to_user_messages(
            form_data=form_data,
            messages_map=messages_map,
            parent_message_id="msg-1",
            image_loader=lambda _: "data:image/png;base64,abc123",
        )
    )

    content = updated["messages"][0]["content"]
    assert isinstance(content, list)
    assert content[0] == {"type": "text", "text": "Describe this image"}
    assert content[1] == {
        "type": "image_url",
        "image_url": {"url": "data:image/png;base64,abc123"},
    }


def test_append_chat_file_images_to_user_messages_skips_when_content_has_images():
    existing_content = [
        {"type": "text", "text": "Already has image"},
        {
            "type": "image_url",
            "image_url": {"url": "data:image/png;base64,existing"},
        },
    ]
    form_data = {"messages": [{"role": "user", "content": list(existing_content)}]}
    messages_map = {
        "msg-1": {
            "id": "msg-1",
            "role": "user",
            "content": "Already has image",
            "parentId": None,
            "files": [
                {
                    "id": "file-1",
                    "url": "file-1",
                    "content_type": "image/png",
                    "type": "file",
                }
            ],
        }
    }

    updated = asyncio.run(
        append_chat_file_images_to_user_messages(
            form_data=form_data,
            messages_map=messages_map,
            parent_message_id="msg-1",
            image_loader=lambda _: "data:image/png;base64,abc123",
        )
    )

    assert updated["messages"][0]["content"] == existing_content


def test_append_chat_file_images_to_user_messages_ignores_non_image_files():
    form_data = {"messages": [{"role": "user", "content": "Use this PDF"}]}
    messages_map = {
        "msg-1": {
            "id": "msg-1",
            "role": "user",
            "content": "Use this PDF",
            "parentId": None,
            "files": [
                {
                    "id": "file-1",
                    "url": "file-1",
                    "content_type": "application/pdf",
                    "type": "file",
                }
            ],
        }
    }

    updated = asyncio.run(
        append_chat_file_images_to_user_messages(
            form_data=form_data,
            messages_map=messages_map,
            parent_message_id="msg-1",
            image_loader=lambda _: "data:image/png;base64,abc123",
        )
    )

    assert updated["messages"][0]["content"] == "Use this PDF"


def test_append_chat_file_images_to_user_messages_no_parent_id_no_changes():
    form_data = {"messages": [{"role": "user", "content": "Hi"}]}

    updated = asyncio.run(
        append_chat_file_images_to_user_messages(
            form_data=form_data,
            messages_map={},
            parent_message_id=None,
            image_loader=lambda _: "data:image/png;base64,abc123",
        )
    )

    assert updated == form_data
