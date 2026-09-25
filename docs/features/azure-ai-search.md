# Azure AI Search vector backend

The Azure AI Search backend is selected with `VECTOR_DB=azure-ai-search`.

Required settings:

- `AZURE_SEARCH_ENDPOINT`: Azure AI Search service endpoint.
- `AZURE_SEARCH_ADMIN_KEY`: key with index and document CRUD permissions.

Optional settings:

- `AZURE_SEARCH_API_VERSION`: SDK API version; defaults to `2024-07-01`.
- `AZURE_SEARCH_TYPE`: `vector`, `fulltext`, `hybrid`, or `semantic`; defaults to `hybrid`.
- `AZURE_ENABLE_SEMANTIC_SEARCH`: enable Azure semantic configuration when set to `true`.
- `AZURE_SEARCH_NAMESPACE_MODE`: use shared indexes with collection filters when set to `true`.

The backend creates indexes from the first vector dimension it receives and maps
Open WebUI collections to Azure AI Search indexes. In namespace mode, knowledge
bases, files, and memories are isolated with a `collection_key` filter.
