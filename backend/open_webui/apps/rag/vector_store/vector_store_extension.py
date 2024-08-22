from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore


class VectorStoreExtension(VectorStore):
    def get_documents(self) -> list[Document]:
        """
        Fetch all the documents from the collection.

        This method can be overridden with a specific implementation for the
        given VectorStore to optimize the execution.
        """
        return self.similarity_search(query="", k=1000000)

    def delete_collection(self) -> None:
        """Delete collection."""
        raise NotImplementedError

    def delete(self, ids: list[str]) -> None:
        """Delete data by ids."""
        raise NotImplementedError

    def is_collection_empty(self) -> bool:
        """
        Check if the collection is empty or not.

        This method can be overridden with a specific implementation for the
        given VectorStore to optimize the execution.
        """
        return len(self.similarity_search(query="", k=1)) == 0

    def reset(self) -> bool:
        """Reset VectorStore by deleting all collections."""
        raise NotImplementedError
