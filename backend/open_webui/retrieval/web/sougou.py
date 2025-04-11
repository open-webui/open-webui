import logging
import json
from typing import Optional, List


from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_sougou(
    sougou_api_sid: str,
    sougou_api_sk: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
) -> List[SearchResult]:
    from tencentcloud.common.common_client import CommonClient
    from tencentcloud.common import credential
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
        TencentCloudSDKException,
    )
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile

    try:
        cred = credential.Credential(sougou_api_sid, sougou_api_sk)
        http_profile = HttpProfile()
        http_profile.endpoint = "tms.tencentcloudapi.com"
        client_profile = ClientProfile()
        client_profile.http_profile = http_profile
        params = json.dumps({"Query": query, "Cnt": 20})
        common_client = CommonClient(
            "tms", "2020-12-29", cred, "", profile=client_profile
        )
        results = [
            json.loads(page)
            for page in common_client.call_json("SearchPro", json.loads(params))[
                "Response"
            ]["Pages"]
        ]
        sorted_results = sorted(
            results, key=lambda x: x.get("scour", 0.0), reverse=True
        )
        if filter_list:
            sorted_results = get_filtered_results(sorted_results, filter_list)

        return [
            SearchResult(
                link=result.get("url"),
                title=result.get("title"),
                snippet=result.get("passage"),
            )
            for result in sorted_results[:count]
        ]
    except TencentCloudSDKException as err:
        log.error(f"Error in Sougou search: {err}")
        return []
