#!/usr/bin/env python3
"""
FastMCP News Server - Updated Version
Fetches news articles from Azure Blob Storage with support for the new JSON structure.
Supports language filtering (English/French) and clean, user-friendly formatting.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from azure.storage.blob import BlobServiceClient
from fastmcp import FastMCP

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("news-server")

# Localization dictionary for UI labels
LABELS = {
    "E": {  # English
        "content": "📄 Content",
        "word_count": "📊 Word count",
        "sentiment": "🎭 Sentiment",
        "no_articles": "No recent articles found matching your criteria.",
        "source": "📰 Source",
        "published": "📅 Published",
    },
    "F": {  # French
        "content": "📄 Contenu",
        "word_count": "📊 Nombre de mots",
        "sentiment": "🎭 Sentiment",
        "no_articles": "Aucun article récent trouvé correspondant à vos critères.",
        "source": "📰 Source",
        "published": "📅 Publié",
    },
}


def fetch_latest_articles_from_azure(
    days_back: int = 1,
    max_articles: int = 5,
    publication_filter: Optional[str] = None,
    language: str = "E",
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
                                        # Filter by language (default to English "E")
                                        article_language = article.get("language", "E")
                                        if language.upper() != article_language.upper():
                                            continue

                                        # Apply publication filter if specified
                                        if publication_filter:
                                            # Check publication field (new structure)
                                            publication_name = ""
                                            if "publication" in article:
                                                publication_name = str(
                                                    article["publication"]
                                                )

                                            if (
                                                publication_filter.lower()
                                                not in publication_name.lower()
                                            ):
                                                continue

                                        # Format article using new structure
                                        formatted_article = {
                                            "id": article.get("id", ""),
                                            "title": article.get("title", "No title"),
                                            "subtitle": article.get("subtitle", ""),
                                            "body": article.get("body", ""),
                                            "summary": article.get("summary", ""),
                                            "url": article.get("url", ""),
                                            "byline": article.get("byline", ""),
                                            "publication": article.get(
                                                "publication", "Unknown"
                                            ),
                                            "publication_date": article.get(
                                                "publication_date", ""
                                            ),
                                            "language": article.get("language", "E"),
                                            "wordcount": article.get("wordcount", 0),
                                            "nlp_sentiment": article.get(
                                                "nlp_sentiment", 0.0
                                            ),
                                            "provider": article.get("provider", ""),
                                            "media": article.get("media", ""),
                                        }
                                        all_articles.append(formatted_article)

                                        # Only break if we have enough articles
                                        if len(all_articles) >= max_articles:
                                            break

                                    # Don't break here - continue looking for more articles
                                    # if len(all_articles) > 0:
                                    #     break

                            except Exception:
                                continue

                    # Don't break here either - let it continue searching
                    # if len(all_articles) > 0:
                    #     break

                except Exception:
                    continue

            if len(all_articles) >= max_articles:
                break

        # Sort by publication date
        all_articles.sort(key=lambda x: x.get("publication_date", ""), reverse=True)

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
    days_back: int = 1,
    max_articles: int = 5,
    publication_filter: str = None,
    language: str = "english",
) -> str:
    """Get latest news headlines with clean formatting

    Args:
        days_back: Number of days back to search (1-7)
        max_articles: Maximum number of articles to return (1-20)
        publication_filter: Filter by publication name (optional)
        language: Language filter - "english", "french", or language code like "E", "F" (default: "english")
    """
    try:
        # Add logging for debugging
        logger.info(
            f"Starting get_top_headlines with days_back={days_back}, max_articles={max_articles}, language={language}"
        )

        # Validate inputs
        days_back = max(1, min(days_back, 7))
        max_articles = max(1, min(max_articles, 20))

        # Convert language to code
        language_code = "E"  # Default to English
        if language.lower() in ["french", "français", "fr", "f"]:
            language_code = "F"
        elif language.lower() in ["english", "en", "e"]:
            language_code = "E"
        elif language.upper() in ["E", "F"]:
            language_code = language.upper()

        result = fetch_latest_articles_from_azure(
            days_back, max_articles, publication_filter, language_code
        )

        if result["status"] == "error":
            logger.error(
                f"Error in fetch_latest_articles_from_azure: {result['message']}"
            )
            return f"Error fetching news: {result['message']}"

        articles = result["articles"]
        if not articles:
            logger.warning("No articles found")
            # Use localized "no articles" message
            labels = LABELS.get(language_code, LABELS["E"])
            return labels["no_articles"]

        # Clean formatting
        language_display = "English" if language_code == "E" else "French"
        response_lines = [
            f"Here are the current top headlines in {language_display} retrieved from NewsDesk (from the past {days_back} day{'s' if days_back > 1 else ''}):",
            "",
        ]

        # Get localized labels for the current language
        labels = LABELS.get(language_code, LABELS["E"])

        for i, article in enumerate(articles, 1):
            title = article["title"]
            publication = article["publication"]
            pub_date = article.get("publication_date", "(Information not provided)")
            byline = article.get("byline", "")

            # Format each article cleanly
            response_lines.append(f"---\n### 📰 {title}")
            if article.get("subtitle"):
                response_lines.append(f"🗞️ Subtitle: {article['subtitle']}")
            response_lines.append(f"{labels['published']}: {pub_date}")
            response_lines.append(f"🔎 Source: {publication}")
            if byline:
                response_lines.append(f"✍️ By: {byline}")

            # Add URL if available
            if article.get("url"):
                response_lines.append(f"🔗 Link: {article['url']}")

            # Add summary or body content (cleaned up)
            content = ""
            if article.get("summary"):
                content = article["summary"]
            elif article.get("body"):
                content = article["body"]

            if content:
                import re

                # Remove HTML tags
                content_text = re.sub(r"<[^>]+>", "", content)
                # Limit length for readability
                if len(content_text) > 300:
                    content_text = content_text[:300] + "..."
                response_lines.append(f"{labels['content']}: {content_text}")

            # Add word count and sentiment if available
            if article.get("wordcount"):
                response_lines.append(f"{labels['word_count']}: {article['wordcount']}")

            if article.get("nlp_sentiment") is not None:
                sentiment = article["nlp_sentiment"]
                sentiment_emoji = (
                    "😊" if sentiment > 0.1 else "😐" if sentiment > -0.1 else "😞"
                )
                response_lines.append(
                    f"{labels['sentiment']}: {sentiment_emoji} ({sentiment:.2f})"
                )

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
