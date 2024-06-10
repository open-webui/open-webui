from typing import List, Union, Generator, Iterator
from schemas import OpenAIChatMessage
from youtube_transcript_api import YouTubeTranscriptApi
import requests, os

from langchain.chains.summarize import load_summarize_chain
from langchain_community.document_loaders import WebBaseLoader
from langchain_openai import ChatOpenAI
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema.document import Document


def get_text_chunks_langchain(text):
    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    docs = [Document(page_content=x) for x in text_splitter.split_text(text)]
    return docs


class Pipeline:
    def __init__(self):
        # Optionally, you can set the id and name of the pipeline.
        # Best practice is to not specify the id so that it can be automatically inferred from the filename, so that users can install multiple versions of the same pipeline.
        # The identifier must be unique across all pipelines.
        # The identifier must be an alphanumeric string that can include underscores or hyphens. It cannot contain spaces, special characters, slashes, or backslashes.
        # self.id = "ollama_pipeline"
        self.name = "Web Summarization"
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

        if "user" in body:
            print("######################################")
            print(f'# User: {body["user"]["name"]} ({body["user"]["id"]})')
            print(f"# Message: {user_message}")
            print("######################################")

        docs = None
        if "https://www.youtube.com/watch?v=" in user_message:
            str_id = user_message.split("https://www.youtube.com/watch?v=")[1].split(
                "&"
            )[0]

            # str_id = user_message.split("https://www.youtube.com/watch?v=")#iz_SJ5TpLJ0
            transcript = YouTubeTranscriptApi.get_transcript(str_id)

            full_text = ""
            for excerpt in transcript:
                full_text = "\n".join([full_text, excerpt["text"]])
            text = full_text

            docs = get_text_chunks_langchain(text)
            print(docs)
        else:
            loader = WebBaseLoader(user_message)
            docs = loader.load()

        OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL")  # "http://ollama:11434"
        MODEL = "llama3"

        # OLLAMA_BASE_URL = "http://localhost:11434"
        llm = ChatOpenAI(
            model_name="llama3",
            openai_api_base=OLLAMA_BASE_URL + "/v1",  # "http://localhost:11434/v1",
            openai_api_key="NA",
            max_tokens=2048,
            temperature=0.7,
        )

        chain = load_summarize_chain(llm, chain_type="stuff")

        result = chain.invoke(docs)

        return result["output_text"]


"""
        try:
            r = requests.post(
                url=f"{OLLAMA_BASE_URL}/v1/chat/completions",
                json={**body, "model": MODEL},
                stream=True,
            )

            r.raise_for_status()

            if body["stream"]:
                return r.iter_lines()
            else:
                return r.json()
        except Exception as e:
            return f"Error: {e}"
"""
