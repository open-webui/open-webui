#!/usr/bin/env python3
"""
FastMCP News Server
A FastMCP server implementation for fetching the latest news using NewsAPI
"""

import os
import requests
from datetime import datetime
from typing import List, Dict, Optional
from fastmcp import FastMCP

# Create FastMCP server
mcp = FastMCP("news-server")

def fetch_latest_headlines(
    category: Optional[str] = None, 
    country: str = 'us', 
    page_size: int = 10,
    q: Optional[str] = None
) -> Dict:
    """
    Fetch latest news headlines using NewsAPI
    
    Args:
        category: News category (business, entertainment, general, health, science, sports, technology)
        country: 2-letter ISO 3166-1 country code (default: 'us')
        page_size: Number of headlines to return (default: 10, max: 100)
        q: Keywords or phrases to search for in the article title and body
    
    Returns:
        Dict containing articles and metadata
    """
    api_key = os.getenv('NEWS_API_KEY')
    if not api_key:
        return {
            "status": "error",
            "message": "NEWS_API_KEY environment variable not set",
            "articles": []
        }
    
    base_url = "https://newsapi.org/v2/top-headlines"
    params = {
        'country': country,
        'pageSize': min(page_size, 100),  # API limit is 100
        'apiKey': api_key
    }
    
    if category:
        params['category'] = category
    if q:
        params['q'] = q
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 'ok':
            # Format articles for better readability
            formatted_articles = []
            for article in data.get('articles', []):
                formatted_article = {
                    "title": article.get('title', 'No title'),
                    "description": article.get('description', 'No description'),
                    "source": article.get('source', {}).get('name', 'Unknown source'),
                    "url": article.get('url', ''),
                    "publishedAt": article.get('publishedAt', ''),
                    "author": article.get('author', 'Unknown author')
                }
                formatted_articles.append(formatted_article)
            
            return {
                "status": "ok",
                "totalResults": data.get('totalResults', 0),
                "articles": formatted_articles,
                "fetched_at": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": data.get('message', 'Unknown API error'),
                "articles": []
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"Network error: {str(e)}",
            "articles": []
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "articles": []
        }

@mcp.tool()
def get_top_headlines(
    category: str = None, 
    country: str = 'us', 
    page_size: int = 10,
    q: str = None
) -> str:
    """Get latest news headlines from NewsAPI
    
    Args:
        category: News category - one of: business, entertainment, general, health, science, sports, technology
        country: 2-letter ISO 3166-1 country code (e.g., 'us', 'gb', 'ca', 'au', 'in')
        page_size: Number of headlines to return (1-100, default: 10)
        q: Keywords or phrases to search for in headlines
    
    Returns:
        Formatted string with news headlines, descriptions, sources, and URLs
    """
    try:
        result = fetch_latest_headlines(category, country, page_size, q)
        
        if result['status'] == 'error':
            return f"Error fetching news: {result['message']}"
        
        articles = result['articles']
        if not articles:
            return "No news articles found for the specified criteria."
        
        # Format the response
        response_lines = [
            f"📰 Latest News Headlines ({result['totalResults']} total results)",
            f"🕒 Fetched at: {result['fetched_at']}"
        ]
        
        if category:
            response_lines.append(f"📂 Category: {category.title()}")
        if country:
            response_lines.append(f"🌍 Country: {country.upper()}")
        if q:
            response_lines.append(f"🔍 Search: {q}")
        
        response_lines.append("─" * 50)
        
        for i, article in enumerate(articles, 1):
            response_lines.extend([
                f"\n{i}. 📰 {article['title']}",
                f"   📅 {article['publishedAt']}",
                f"   📰 Source: {article['source']}",
                f"   👤 Author: {article['author']}",
                f"   📄 {article['description']}",
                f"   🔗 {article['url']}",
            ])
        
        return "\n".join(response_lines)
        
    except Exception as e:
        return f"Error getting news headlines: {str(e)}"

if __name__ == "__main__":
    import sys
    
    # Check if we should run with HTTP transport
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8084
        print(f"Starting FastMCP News server on SSE port {port}")
        mcp.run(transport="sse", port=port)
    else:
        # Run with stdio transport (standard MCP)
        print("Starting FastMCP News server with stdio transport")
        mcp.run()
