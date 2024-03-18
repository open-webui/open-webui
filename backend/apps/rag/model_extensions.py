from chromadb import Documents, EmbeddingFunction, Embeddings
from langchain_community.embeddings import OllamaEmbeddings

embeddings = OllamaEmbeddings(model="SFR-embeddings-mistral")


class SfrEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        return embeddings.embed_documents(input)
