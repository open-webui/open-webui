import base64
import logging
from typing import Iterator, AsyncIterator
import aiohttp
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document
from pydantic import BaseModel
import asyncio
from feddersen.config import GEMINI_PDF_EXCTRACTION_PROMPT, LITELLM_GEMINI_NAME
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class Transcription(BaseModel):
    markdown_transcription: str


class GeminiLoader(BaseLoader):
    """
    This class creates a loader for extracting information from PDF files using Google's Gemini model.
    Args:
        base_url (str): The base URL for the API endpoint.
        api_key (str): The API key for authentication.
        model_name (str, optional): The name of the model to use. Defaults to LITELLM_GEMINI_NAME.
        prompt (str, optional): The prompt to use for extraction. Defaults to GEMINI_PDF_EXCTRACTION_PROMPT.
        file_path (str, optional): Path to the PDF file. Must provide either this or bytes_source.
        bytes_source (bytes, optional): The PDF data as bytes. Must provide either this or file_path.
    Raises:
        AssertionError: If neither file_path nor bytes_source is provided.
    Note:
        If the base_url does not end with "chat/completions", it will be appended automatically.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model_name: str = LITELLM_GEMINI_NAME,
        prompt: str = GEMINI_PDF_EXCTRACTION_PROMPT,
        file_path: str = None,
        bytes_source: bytes = None,
    ) -> None:
        assert (
            file_path is not None or bytes_source is not None
        ), "Either file_path or bytes_source must be specified"

        self.file_path = file_path
        self.bytes_source = bytes_source

        if base_url.endswith("chat/completions"):
            base_url += f"{base_url}/chat/completions"
        self.endpoint = f"{base_url}/chat/completions"
        self.api_key = api_key
        self.model_name = model_name
        self.prompt = prompt
        self.temperature = 0.2

    def lazy_load(self) -> Iterator[Document]:
        """
        Converts the asynchronous lazy_load method to a synchronous iterator.

        Returns:
            Iterator[Document]: An iterator over extracted documents.
        """

        # Run the async generator and collect all documents
        async def get_all_documents():
            documents = []
            async for document in self.alazy_load():
                documents.append(document)
            return documents

        # Return documents from the synchronous iterator
        for document in asyncio.run(get_all_documents()):
            yield document

    async def alazy_load(self) -> AsyncIterator[Document]:
        """
        Asynchronously extracts text from a file using a specified model and API endpoint.

        Returns:
            str: The extracted text from the file.

        Raises:
            ValueError: If the response does not contain the expected data.
        """
        if self.file_path is not None:
            with open(self.file_path, "rb") as f:
                file_data = f.read()
        else:
            file_data = self.bytes_source

        encoded_file = base64.b64encode(file_data).decode("utf-8")

        data = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": f"data:application/pdf;base64,{encoded_file}",
                        },
                        {
                            "type": "text",
                            "text": self.prompt,
                        },
                    ],
                }
            ],
            "response_format": Transcription.model_json_schema(),
            "temperature": self.temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        log.info(f"Sending async request to {self.endpoint}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=self.endpoint, json=data, headers=headers, timeout=60
            ) as response:
                response_data = await response.json()

                yield Document(
                    page_content=response_data.get("choices")[0]
                    .get("message")
                    .get("content")
                )
