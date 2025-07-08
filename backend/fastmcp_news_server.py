#!/usr/bin/env python3
"""
FastMCP News Server - Clean Version
Fetches news articles from Azure Blob Storage with clean, user-friendly formatting.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from azure.storage.blob import BlobServiceClient
from fastmcp import FastMCP

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("news-server")


def fetch_latest_articles_from_azure(
    days_back: int = 1,
    max_articles: int = 5,
    publication_filter: Optional[str] = None,
) -> Dict:
    """
    Fetch latest news articles from Azure Blob Storage (NewsDesk)
    """
    try:
        # Get Azure connection string from environment variable
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            return {
                "status": "error",
                "message": "AZURE_STORAGE_CONNECTION_STRING environment variable not set",
                "articles": [],
            }

        # Initialize Azure Blob Service Client
        blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )
        container_name = os.getenv("AZURE_BLOB_CONTAINER_NAME", "articles")

        # Verify container exists
        container_client = blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            return {
                "status": "error",
                "message": f"Container '{container_name}' not found",
                "articles": [],
            }

        # Get recent articles
        all_articles = []

        # Check the last few days for articles
        for day_offset in range(days_back):
            check_date = datetime.now() - timedelta(days=day_offset)

            # Try different date formats
            date_formats = [
                check_date.strftime("%Y/%m/%d"),
                check_date.strftime("%Y-%m-%d"),
                check_date.strftime("%Y%m%d"),
            ]

            for date_prefix in date_formats:
                try:
                    blob_list = container_client.list_blobs(
                        name_starts_with=date_prefix
                    )

                    for blob in blob_list:
                        if blob.name.endswith(".json"):
                            try:
                                blob_client = blob_service_client.get_blob_client(
                                    container=container_name, blob=blob.name
                                )
                                blob_data = blob_client.download_blob().readall()
                                json_data = json.loads(blob_data.decode("utf-8"))

                                if "articles" in json_data:
                                    for article in json_data["articles"]:
                                        # Apply publication filter if specified
                                        if publication_filter:
                                            source_name = ""
                                            if "publication" in article:
                                                if isinstance(
                                                    article["publication"], dict
                                                ):
                                                    source_name = article[
                                                        "publication"
                                                    ].get("name", "")
                                                else:
                                                    source_name = str(
                                                        article["publication"]
                                                    )
                                            elif "source" in article:
                                                if isinstance(article["source"], dict):
                                                    source_name = article["source"].get(
                                                        "name", ""
                                                    )
                                                else:
                                                    source_name = str(article["source"])

                                            if (
                                                publication_filter.lower()
                                                not in source_name.lower()
                                            ):
                                                continue

                                        # Extract source name
                                        source_name = "Unknown"
                                        if "publication" in article:
                                            if isinstance(article["publication"], dict):
                                                source_name = article[
                                                    "publication"
                                                ].get("name", "Unknown")
                                            else:
                                                source_name = str(
                                                    article["publication"]
                                                )
                                        elif "source" in article:
                                            if isinstance(article["source"], dict):
                                                source_name = article["source"].get(
                                                    "name", "Unknown"
                                                )
                                            else:
                                                source_name = str(article["source"])

                                        # Format article - capture ALL possible URL fields
                                        formatted_article = {
                                            "title": article.get("title", "No title"),
                                            "source": source_name,
                                            "url": article.get("url", ""),
                                            "infomedia_url": article.get(
                                                "infomedia_url", ""
                                            ),
                                            "articleUrl": article.get("articleUrl", ""),
                                            "originalArticleUrl": article.get(
                                                "originalArticleUrl", ""
                                            ),
                                            "original_url": article.get(
                                                "original_url", ""
                                            ),
                                            "source_url": article.get("source_url", ""),
                                            "link": article.get("link", ""),
                                            "href": article.get("href", ""),
                                            "publishedAt": article.get(
                                                "published_at",
                                                article.get(
                                                    "publicationDate",
                                                    article.get(
                                                        "publicationDateFormatted", ""
                                                    ),
                                                ),
                                            ),
                                            "lead": article.get("lead", ""),
                                            "subtitle": article.get("subtitle", ""),
                                        }
                                        all_articles.append(formatted_article)

                                        # Only break if we have enough articles
                                        if len(all_articles) >= max_articles:
                                            break

                                    # Don't break here - continue looking for more articles
                                    # if len(all_articles) > 0:
                                    #     break

                            except Exception as e:
                                continue

                    # Don't break here either - let it continue searching
                    # if len(all_articles) > 0:
                    #     break

                except Exception as e:
                    continue

            if len(all_articles) >= max_articles:
                break

        # Sort by publication date
        all_articles.sort(key=lambda x: x.get("publishedAt", ""), reverse=True)

        return {
            "status": "ok",
            "totalResults": len(all_articles[:max_articles]),
            "articles": all_articles[:max_articles],
            "fetched_at": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error fetching articles: {str(e)}",
            "articles": [],
        }


@mcp.tool()
def get_top_headlines(
    days_back: int = 1, max_articles: int = 5, publication_filter: str = None
) -> str:
    """Get latest news headlines with clean formatting"""
    try:
        # Add logging for debugging
        logger.info(f"Starting get_top_headlines with days_back={days_back}, max_articles={max_articles}")
        
        # Validate inputs
        days_back = max(1, min(days_back, 7))
        max_articles = max(1, min(max_articles, 20))

        result = fetch_latest_articles_from_azure(
            days_back, max_articles, publication_filter
        )

        if result["status"] == "error":
            logger.error(f"Error in fetch_latest_articles_from_azure: {result['message']}")
            return f"Error fetching news: {result['message']}"

        articles = result["articles"]
        if not articles:
            logger.warning("No articles found")
            return "No news articles found."

        # Clean formatting
        response_lines = [
            f"Here are the current top headlines retrieved from NewsDesk (from the past {days_back} day{'s' if days_back > 1 else ''}):",
            "",
        ]

        for i, article in enumerate(articles, 1):
            title = article["title"]
            source = article["source"]
            pub_date = article.get("publishedAt", "(Information not provided)")

            # Format each article cleanly
            response_lines.append(f"\n📰 {title}")
            response_lines.append(f"📅 Published: {pub_date}")
            response_lines.append(f"📰 Source: {source}")

            # Add ALL available URLs - prioritize original article URLs
            urls_found = []

            # InfoMedia URLs first
            if article.get("url"):
                urls_found.append(f"🔗 InfoMedia: {article['url']}")
            if article.get("infomedia_url"):
                urls_found.append(f"🔗 InfoMedia: {article['infomedia_url']}")

            # Article URLs
            if article.get("articleUrl"):
                urls_found.append(f"🔗 Article URL: {article['articleUrl']}")

            # ORIGINAL ARTICLE URLS - CHECK ALL POSSIBLE FIELDS
            original_urls = []
            if article.get("originalArticleUrl"):
                original_urls.append(article["originalArticleUrl"])
            if article.get("original_url"):
                original_urls.append(article["original_url"])
            if article.get("source_url"):
                original_urls.append(article["source_url"])
            if article.get("link"):
                original_urls.append(article["link"])
            if article.get("href"):
                original_urls.append(article["href"])

            # Remove duplicates and add to display
            seen_urls = set()
            for orig_url in original_urls:
                if orig_url and orig_url not in seen_urls:
                    urls_found.append(f"🌐 Original Article: {orig_url}")
                    seen_urls.add(orig_url)

            # Add the URLs we found
            for url_line in urls_found:
                response_lines.append(url_line)

            # Add lead content (cleaned up)
            if article.get("lead"):
                import re

                lead_text = re.sub(r"<[^>]+>", "", article["lead"])  # Remove HTML tags
                # Don't truncate - show full lead
                response_lines.append(f"📄 Lead: {lead_text}")

            # Add subtitle if available
            if article.get("subtitle"):
                response_lines.append(f"Additional Note: {article['subtitle']}")

            # Add spacing between articles
            response_lines.append("")

        final_response = "\n".join(response_lines)
        logger.info(f"Successfully generated response with {len(articles)} articles")
        return final_response

    except Exception as e:
        logger.error(f"Error in get_top_headlines: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return f"Error getting news headlines: {str(e)}"


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8084
        print(f"Starting FastMCP News server on SSE port {port}")
        mcp.run(transport="sse", port=port)
    else:
        print("Starting FastMCP News server with stdio transport")
        mcp.run()
