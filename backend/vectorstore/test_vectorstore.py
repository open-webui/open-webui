import os
import unittest
import uuid
from unittest import mock

from langchain_core.documents import Document

import config

class VectorStoreTestCase(unittest.TestCase):

    @mock.patch.dict(os.environ, dict(), clear=True)
    def test_chroma_default(self):
        coll_name = str(uuid.uuid4())
        from vectorstore import create_vector_store
        import config
        config.CHROMA_CLIENT = create_vector_store()
        self.index_then_search(coll_name)
        config.CHROMA_CLIENT.delete_collection(coll_name)

    def index_then_search(self, collection_name: str):
        from apps.rag.main import store_data_in_vector_db
        docs = [Document(page_content="lorem ipsum", metadata={"alfa": 1, "beta": "gamma"}),
                Document(page_content="dolor sit amet", metadata={"delta": 2, "phi": "thetta"})]
        ok = store_data_in_vector_db(docs, collection_name=collection_name, overwrite=False)  # TODO overwrite
        self.assertTrue(ok)
        # it seems it never adds docs
        # ok = store_data_in_vector_db([Document(page_content="foo bar", metadata={"a": 0, "b": "c"})],
        #                             collection_name=self.coll_name, overwrite=False)  # TODO overwrite
        # self.assertTrue(ok)  # add assertion here
        collection = config.CHROMA_CLIENT.get_collection(collection_name)
        self.assertEqual(collection_name, collection.name)
        all_docs = config.CHROMA_CLIENT.get_all(collection_name)

        for i in range(len(docs)):
            idx_found = all_docs["documents"].index(docs[i].page_content)
            self.assertTrue(idx_found >= 0)

            self.assertEqual(type(all_docs["ids"][idx_found]), str)
            self.assertTrue(len(all_docs["ids"][idx_found]) > 0)
            self.assertTrue(set(docs[i].metadata).issubset(all_docs["metadatas"][idx_found]))

        from apps.rag.utils import query_doc
        import sentence_transformers
        sentence_transformer_ef = sentence_transformers.SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        embedding_function = lambda query: sentence_transformer_ef.encode(query).tolist()
        found = query_doc(collection_name, "lorem ipsum dolor sit amet", embedding_function, 5)
        self.assertEqual(len(docs), len(found["distances"][0]))
        self.assertEqual(len(docs), len(found["ids"][0]))
        self.assertEqual(len(docs), len(found["metadatas"][0]))
        self.assertEqual(len(docs), len(found["documents"][0]))
        for i in range(len(docs)):
            idx_found = found["documents"][0].index(docs[i].page_content)
            self.assertTrue(idx_found >= 0)

            self.assertEqual(type(found["ids"][0][idx_found]), str)
            self.assertTrue(len(found["ids"][0][idx_found]) > 0)
            self.assertTrue(set(docs[i].metadata).issubset(found["metadatas"][0][idx_found]))
            self.assertEqual(type(found["distances"][0][idx_found]), float)
            self.assertTrue(found["distances"][0][idx_found] > 0.0)
        print(found)

    @mock.patch.dict(os.environ, {"QDRANT_LOCATION": ":memory:"}, clear=True)
    def test_qdrant_in_memory(self):
        from vectorstore import create_vector_store
        import config
        config.CHROMA_CLIENT = create_vector_store()
        self.index_then_search(str(uuid.uuid4()))

if __name__ == '__main__':
    unittest.main()
