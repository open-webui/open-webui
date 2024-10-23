from typing import Optional, Union

import requests

from open_webui.apps.ollama.main import (
    generate_ollama_batch_embeddings,
    GenerateEmbedForm,
)


def get_embedding_function(
    embedding_engine,
    embedding_model,
    embedding_function,
    openai_key,
    openai_url,
    embedding_batch_size,
):
    if embedding_engine == "":
        return lambda query: embedding_function.encode(query).tolist()
    elif embedding_engine in ["ollama", "openai"]:
        func = lambda query: generate_embeddings(
            engine=embedding_engine,
            model=embedding_model,
            text=query,
            key=openai_key if embedding_engine == "openai" else "",
            url=openai_url if embedding_engine == "openai" else "",
        )

        def generate_multiple(query, func):
            if isinstance(query, list):
                embeddings = []
                for i in range(0, len(query), embedding_batch_size):
                    embeddings.extend(func(query[i : i + embedding_batch_size]))
                return embeddings
            else:
                return func(query)

        return lambda query: generate_multiple(query, func)


def generate_embeddings(engine: str, model: str, text: Union[str, list[str]], **kwargs):
    if engine == "ollama":
        if isinstance(text, list):
            embeddings = generate_ollama_batch_embeddings(
                GenerateEmbedForm(**{"model": model, "input": text})
            )
        else:
            embeddings = generate_ollama_batch_embeddings(
                GenerateEmbedForm(**{"model": model, "input": [text]})
            )
        return (
            embeddings["embeddings"][0]
            if isinstance(text, str)
            else embeddings["embeddings"]
        )
    elif engine == "openai":
        key = kwargs.get("key", "")
        url = kwargs.get("url", "https://api.openai.com/v1")

        if isinstance(text, list):
            embeddings = generate_openai_batch_embeddings(model, text, key, url)
        else:
            embeddings = generate_openai_batch_embeddings(model, [text], key, url)

        return embeddings[0] if isinstance(text, str) else embeddings


def generate_openai_batch_embeddings(
    model: str, texts: list[str], key: str, url: str = "https://api.openai.com/v1"
) -> Optional[list[list[float]]]:
    try:
        r = requests.post(
            f"{url}/embeddings",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            json={"input": texts, "model": model},
        )
        r.raise_for_status()
        data = r.json()
        if "data" in data:
            return [elem["embedding"] for elem in data["data"]]
        else:
            raise "Something went wrong :/"
    except Exception as e:
        print(e)
        return None
