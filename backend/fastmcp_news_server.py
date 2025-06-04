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

def search_everything(
    q: str,
    language: str = 'en',
    sort_by: str = 'publishedAt',
    page_size: int = 10
) -> Dict:
    """
    Search through millions of articles using NewsAPI everything endpoint
    
    Args:
        q: Keywords or phrases to search for
        language: Language to restrict articles to (default: 'en')
        sort_by: Sort order ('relevancy', 'popularity', 'publishedAt')
        page_size: Number of articles to return (default: 10, max: 100)
    
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
    
    base_url = "https://newsapi.org/v2/everything"
    params = {
        'q': q,
        'language': language,
        'sortBy': sort_by,
        'pageSize': min(page_size, 100),  # API limit is 100
        'apiKey': api_key
    }
    
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

@mcp.tool()
def search_news(
    q: str,
    language: str = 'en',
    sort_by: str = 'publishedAt',
    page_size: int = 10
) -> str:
    """Search for news articles across all sources using NewsAPI
    
    Args:
        q: Keywords or phrases to search for (required)
        language: Language code (e.g., 'en', 'es', 'fr', 'de', 'it')
        sort_by: Sort articles by 'relevancy', 'popularity', or 'publishedAt'
        page_size: Number of articles to return (1-100, default: 10)
    
    Returns:
        Formatted string with search results including articles and metadata
    """
    try:
        if not q.strip():
            return "Error: Search query (q) is required and cannot be empty."
        
        result = search_everything(q, language, sort_by, page_size)
        
        if result['status'] == 'error':
            return f"Error searching news: {result['message']}"
        
        articles = result['articles']
        if not articles:
            return f"No news articles found for query: '{q}'"
        
        # Format the response
        response_lines = [
            f"🔍 News Search Results for: '{q}'",
            f"📊 Found {result['totalResults']} total results",
            f"🌐 Language: {language.upper()}",
            f"📈 Sorted by: {sort_by}",
            f"🕒 Searched at: {result['fetched_at']}",
            "─" * 50
        ]
        
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
        return f"Error searching news: {str(e)}"

@mcp.tool()
def get_news_sources(
    category: str = None,
    language: str = 'en',
    country: str = 'us'
) -> str:
    """Get available news sources from NewsAPI
    
    Args:
        category: Filter by category (business, entertainment, general, health, science, sports, technology)
        language: Filter by language (e.g., 'en', 'es', 'fr')
        country: Filter by country (2-letter ISO code)
    
    Returns:
        Formatted string with available news sources
    """
    try:
        api_key = os.getenv('NEWS_API_KEY')
        if not api_key:
            return "Error: NEWS_API_KEY environment variable not set"
        
        base_url = "https://newsapi.org/v2/sources"
        params = {'apiKey': api_key}
        
        if category:
            params['category'] = category
        if language:
            params['language'] = language
        if country:
            params['country'] = country
        
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 'ok':
            sources = data.get('sources', [])
            if not sources:
                return "No news sources found for the specified criteria."
            
            response_lines = [
                f"📰 Available News Sources ({len(sources)} found)",
                f"🌐 Language: {language.upper()}",
                f"🌍 Country: {country.upper()}",
            ]
            
            if category:
                response_lines.append(f"📂 Category: {category.title()}")
            
            response_lines.append("─" * 50)
            
            for i, source in enumerate(sources, 1):
                response_lines.extend([
                    f"\n{i}. 📰 {source.get('name', 'Unknown')}",
                    f"   🆔 ID: {source.get('id', 'N/A')}",
                    f"   📄 {source.get('description', 'No description')}",
                    f"   📂 Category: {source.get('category', 'general').title()}",
                    f"   🌐 Language: {source.get('language', 'unknown').upper()}",
                    f"   🌍 Country: {source.get('country', 'unknown').upper()}",
                    f"   🔗 {source.get('url', 'No URL')}",
                ])
            
            return "\n".join(response_lines)
        else:
            return f"Error: {data.get('message', 'Unknown API error')}"
            
    except Exception as e:
        return f"Error getting news sources: {str(e)}"

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
