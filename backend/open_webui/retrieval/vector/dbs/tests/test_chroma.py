from open_webui.retrieval.vector.dbs.chroma import ChromaClient


class FakeChromaClient:
    def __init__(self, existing_names):
        self.existing_names = set(existing_names)

    def list_collections(self):
        raise KeyError('_type')

    def get_collection(self, name):
        if name not in self.existing_names:
            raise ValueError('collection not found')

        return object()


def test_has_collection_checks_target_collection_without_listing():
    client = ChromaClient.__new__(ChromaClient)
    client.client = FakeChromaClient({'web-search-example'})

    assert client.has_collection('web-search-example') is True
    assert client.has_collection('missing') is False
