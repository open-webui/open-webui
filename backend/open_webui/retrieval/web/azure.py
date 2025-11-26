import logging
from typing import Optional
from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

"""
Azure AI Search integration for Open WebUI.
Documentation: https://learn.microsoft.com/en-us/python/api/overview/azure/search-documents-readme?view=azure-python

Required package: azure-search-documents
Install: pip install azure-search-documents
"""


def search_azure(
    api_key: str,
    endpoint: str,
    index_name: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
) -> list[SearchResult]:
    """
    Search using Azure AI Search.

    Args:
        api_key: Azure Search API key (query key or admin key)
        endpoint: Azure Search service endpoint (e.g., https://myservice.search.windows.net)
        index_name: Name of the search index to query
        query: Search query string
        count: Number of results to return
        filter_list: Optional list of domains to filter results

    Returns:
        List of SearchResult objects with link, title, and snippet
    """
    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient
    except ImportError:
        log.error(
            "azure-search-documents package is not installed. "
            "Install it with: pip install azure-search-documents"
        )
        raise ImportError(
            "azure-search-documents is required for Azure AI Search. "
            "Install it with: pip install azure-search-documents"
        )

    try:
        # Create search client with API key authentication
        credential = AzureKeyCredential(api_key)
        search_client = SearchClient(
            endpoint=endpoint, index_name=index_name, credential=credential
        )

        # Perform the search
        results = search_client.search(search_text=query, top=count)

        # Convert results to list and extract fields
        search_results = []
        for result in results:
            # Azure AI Search returns documents with custom schemas
            # We need to extract common fields that might represent URL, title, and content
            # Common field names to look for:
            result_dict = dict(result)

            # Try to find URL field (common names)
            link = (
                result_dict.get("url")
                or result_dict.get("link")
                or result_dict.get("uri")
                or result_dict.get("metadata_storage_path")
                or ""
            )

            # Try to find title field (common names)
            title = (
                result_dict.get("title")
                or result_dict.get("name")
                or result_dict.get("metadata_title")
                or result_dict.get("metadata_storage_name")
                or None
            )

            # Try to find content/snippet field (common names)
            snippet = (
                result_dict.get("content")
                or result_dict.get("snippet")
                or result_dict.get("description")
                or result_dict.get("summary")
                or result_dict.get("text")
                or None
            )

            # Truncate snippet if too long
            if snippet and len(snippet) > 500:
                snippet = snippet[:497] + "..."

            if link:  # Only add if we found a valid link
                search_results.append(
                    {
                        "link": link,
                        "title": title,
                        "snippet": snippet,
                    }
                )

        # Apply domain filtering if specified
        if filter_list:
            search_results = get_filtered_results(search_results, filter_list)

        # Convert to SearchResult objects
        return [
            SearchResult(
                link=result["link"],
                title=result.get("title"),
                snippet=result.get("snippet"),
            )
            for result in search_results
        ]

    except Exception as ex:
        log.error(f"Azure AI Search error: {ex}")
        raise ex
