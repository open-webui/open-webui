import base64
import io
import json
import logging
import os
from typing import Optional, List

import requests

from fastapi import Request

from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.utils.headers import include_user_info_headers
from open_webui.env import FORWARD_SESSION_INFO_HEADER_CHAT_ID

from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

log = logging.getLogger(__name__)


def xml_element_contents_to_string(element: Element) -> str:
    buffer = [element.text if element.text else ""]

    for child in element:
        buffer.append(xml_element_contents_to_string(child))

    buffer.append(element.tail if element.tail else "")

    return "".join(buffer)


def search_yandex(
    request: Request,
    yandex_search_url: str,
    yandex_search_api_key: str,
    yandex_search_config: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
    user=None,
) -> List[SearchResult]:
    try:
        headers = {
            "User-Agent": "Open WebUI (https://github.com/open-webui/open-webui) RAG Bot",
            "Authorization": f"Api-Key {yandex_search_api_key}",
        }

        if user is not None:
            headers = include_user_info_headers(headers, user)

        chat_id = getattr(request.state, "chat_id", None)
        if chat_id:
            headers[FORWARD_SESSION_INFO_HEADER_CHAT_ID] = str(chat_id)

        payload = {} if yandex_search_config == "" else json.loads(yandex_search_config)

        if type(payload.get("query", None)) != dict:
            payload["query"] = {}

        if "searchType" not in payload["query"]:
            payload["query"]["searchType"] = "SEARCH_TYPE_RU"

        payload["query"]["queryText"] = query

        if type(payload.get("groupSpec", None)) != dict:
            payload["groupSpec"] = {}

        if "groupMode" not in payload["groupSpec"]:
            payload["groupSpec"]["groupMode"] = "GROUP_MODE_DEEP"

        payload["groupSpec"]["groupsOnPage"] = count
        payload["groupSpec"]["docsInGroup"] = 1

        response = requests.post(
            (
                "https://searchapi.api.cloud.yandex.net/v2/web/search"
                if yandex_search_url == ""
                else yandex_search_url
            ),
            headers=headers,
            json=payload,
        )

        response.raise_for_status()

        response_body = response.json()
        if "rawData" not in response_body:
            raise Exception(f"No `rawData` in response body: {response_body}")

        search_result_body_bytes = base64.decodebytes(
            bytes(response_body["rawData"], "utf-8")
        )

        doc_root = ET.parse(io.BytesIO(search_result_body_bytes))

        results = []

        for group in doc_root.findall("response/results/grouping/group"):
            results.append(
                {
                    "url": xml_element_contents_to_string(group.find("doc/url")).strip(
                        "\n"
                    ),
                    "title": xml_element_contents_to_string(
                        group.find("doc/title")
                    ).strip("\n"),
                    "snippet": xml_element_contents_to_string(
                        group.find("doc/passages/passage")
                    ),
                }
            )

        results = get_filtered_results(results, filter_list)

        results = [
            SearchResult(
                link=result.get("url"),
                title=result.get("title"),
                snippet=result.get("snippet"),
            )
            for result in results[:count]
        ]

        log.info(f"Yandex search results: {results}")

        return results
    except Exception as e:
        log.error(f"Error in search: {e}")

        return []


if __name__ == "__main__":
    from starlette.datastructures import Headers
    from fastapi import FastAPI

    result = search_yandex(
        Request(
            {
                "type": "http",
                "asgi.version": "3.0",
                "asgi.spec_version": "2.0",
                "method": "GET",
                "path": "/internal",
                "query_string": b"",
                "headers": Headers({}).raw,
                "client": ("127.0.0.1", 12345),
                "server": ("127.0.0.1", 80),
                "scheme": "http",
                "app": FastAPI(),
            },
            None,
        ),
        os.environ.get("YANDEX_WEB_SEARCH_URL", ""),
        os.environ.get("YANDEX_WEB_SEARCH_API_KEY", ""),
        os.environ.get(
            "YANDEX_WEB_SEARCH_CONFIG", '{"query": {"searchType": "SEARCH_TYPE_COM"}}'
        ),
        "TOP movies of the past year",
        3,
    )

    print(result)
