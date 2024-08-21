from typing import List, Union, Generator, Iterator
from schemas import OpenAIChatMessage
import subprocess
import requests
import os

MATN_CHARGE_API = os.getenv("MATN_CHARGE_API", "http://127.0.0.1:5000/dashboard/manage_chat")

class Pipeline:
    def __init__(self):
        # Optionally, you can set the id and name of the pipeline.
        # Best practice is to not specify the id so that it can be automatically inferred from the filename, so that users can install multiple versions of the same pipeline.
        # The identifier must be unique across all pipelines.
        # The identifier must be an alphanumeric string that can include underscores or hyphens. It cannot contain spaces, special characters, slashes, or backslashes.
        # self.id = "python_code_pipeline"
        self.name = "Matn Charge Management"
        pass

    async def on_startup(self):
        # This function is called when the server is started.
        print(f"on_startup:{__name__}")
        pass

    async def on_shutdown(self):
        # This function is called when the server is stopped.
        print(f"on_shutdown:{__name__}")
        pass


    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        # This is where you can add your custom pipelines like RAG.
        print(f"pipe:{__name__}")

        user_id = None
        words = None
        model = None
        if "user" in body:
            user_id = body["user"]["id"]
            words = len(str(user_message).split())
            model = "gpt-4o"
        payload = {"model": model, "chat_user_id": user_id, "words": words}
        print(payload)
        r = requests.post(
            url=f"{MATN_CHARGE_API}",
            json=payload,
        )
        print(r)
        r.raise_for_status()

        if body["stream"]:
            return r.iter_lines()
        else:
            return r.json()
            