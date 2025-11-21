"""
Enhanced Multi-Search Internet Retriever
Combines the best of Open WebUI's implementation with custom scoring and filtering.

Key Features:
- LLM-powered query generation (from Open WebUI)
- Full page content loading with retry logic (from Open WebUI)
- Multi-provider parallel search (original strength)
- Sophisticated scoring: recency + quality + similarity (original strength)
- Date filtering for 2018+ content (original strength)
"""

import asyncio
import json
import logging
import time
import re
import math
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict
from itertools import chain
from difflib import SequenceMatcher
import concurrent.futures

import numpy as np
import aiohttp
from bs4 import BeautifulSoup
from dateutil.parser import parse
from langchain_core.documents import Document
from langchain.retrievers import BaseRetriever
from langchain.schema import QueryBundle
from llama_index.core.schema import NodeWithScore, Node

# Import your existing search clients
from tavily import TavilyClient
from langchain_community.utilities import GoogleSerperAPIWrapper, DuckDuckGoSearchAPIWrapper
from langchain_ollama import OllamaEmbeddings

# Your existing config (update these as needed)
from your_config import NICOMIND_BASE_URL, NICOMIND_API_KEY

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class EnhancedMultiSearchRetriever(BaseRetriever):
    """
    Enhanced multi-search retriever combining best practices from Open WebUI with custom scoring.

    NEW FEATURES FROM OPEN WEBUI:
    - LLM query generation for optimized searches
    - Full page content loading with BeautifulSoup
    - Robust retry logic and error handling

    RETAINED STRENGTHS:
    - Multi-provider parallel search
    - Sophisticated scoring (60% recency, 25% similarity, 15% quality)
    - 2018+ date filtering
    - Smart duplicate detection
    """

    tavily_client: TavilyClient
    serper_client: GoogleSerperAPIWrapper
    ddg_search: DuckDuckGoSearchAPIWrapper
    encoder: OllamaEmbeddings = None
    llm_client: any = None  # For query generation

    def __init__(
        self,
        tavily_client: TavilyClient,
        serper_client: GoogleSerperAPIWrapper,
        ddg_search: DuckDuckGoSearchAPIWrapper,
        llm_client: Optional[any] = None,  # Pass your Ollama/OpenAI client for query generation
    ):
        super().__init__()
        self.tavily_client = tavily_client
        self.serper_client = serper_client
        self.ddg_search = ddg_search
        self.llm_client = llm_client

        # Initialize embeddings with fallback
        try:
            self.encoder = OllamaEmbeddings(
                model="mxbai-embed-large:latest",
                base_url=NICOMIND_BASE_URL,
                client_kwargs={"headers": {"Authorization": f"Bearer {NICOMIND_API_KEY}"}}
            )
        except Exception as e:
            log.warning(f"Error loading embeddings: {e}. Falling back to text similarity")
            self.encoder = None

    # ==================== NEW: LLM QUERY GENERATION ====================

    def _generate_search_queries(self, user_query: str, conversation_context: Optional[List[str]] = None) -> List[str]:
        """
        Generate 1-3 optimized search queries using LLM (inspired by Open WebUI).
        Falls back to original query if generation fails.
        """
        if not self.llm_client:
            log.info("No LLM client provided, using original query")
            return [user_query]

        try:
            # Build context from conversation if available
            context = "\n".join(conversation_context) if conversation_context else user_query

            prompt = f"""### Task:
Generate 1-3 optimized search queries to find the most relevant and recent information for this request.

### Guidelines:
- Return ONLY a JSON object with a "queries" array
- Each query should be distinct and focused
- Prioritize queries that will find recent (2018+) technical information
- If the query is already optimal, return it as-is
- Today's date is: {datetime.now().strftime('%Y-%m-%d')}

### User Request:
{user_query}

### Output Format:
{{"queries": ["query1", "query2", "query3"]}}
"""

            # Call your LLM (adjust this based on your LLM client)
            response = self.llm_client.generate(prompt, max_tokens=200, temperature=0.3)

            # Parse JSON response
            try:
                # Extract JSON from response
                content = response if isinstance(response, str) else response.get("content", "")
                bracket_start = content.find("{")
                bracket_end = content.rfind("}") + 1

                if bracket_start == -1 or bracket_end == -1:
                    raise ValueError("No JSON found")

                json_str = content[bracket_start:bracket_end]
                queries_data = json.loads(json_str)
                queries = queries_data.get("queries", [])

                if queries and len(queries) > 0:
                    log.info(f"✅ Generated {len(queries)} optimized queries: {queries}")
                    return queries[:3]  # Max 3 queries
            except Exception as e:
                log.warning(f"Failed to parse LLM response: {e}")

        except Exception as e:
            log.warning(f"Query generation failed: {e}")

        # Fallback to original query
        return [user_query]

    # ==================== NEW: FULL PAGE CONTENT LOADING ====================

    async def _load_full_page_content(self, url: str, retries: int = 3) -> Optional[str]:
        """
        Load full page content using aiohttp and BeautifulSoup (inspired by Open WebUI).
        Includes retry logic for robustness.
        """
        for attempt in range(retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=10),
                        headers={"User-Agent": "Mozilla/5.0"}
                    ) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')

                            # Remove script and style elements
                            for script in soup(["script", "style", "nav", "footer", "header"]):
                                script.decompose()

                            # Extract text
                            text = soup.get_text(separator='\n', strip=True)

                            # Clean up text
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            clean_text = '\n'.join(lines)

                            return clean_text if len(clean_text) > 200 else None
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    log.warning(f"Failed to load {url} after {retries} attempts: {e}")

        return None

    def _load_full_pages_sync(self, urls: List[str]) -> Dict[str, str]:
        """Synchronous wrapper for loading multiple pages in parallel."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        tasks = [self._load_full_page_content(url) for url in urls]
        results = loop.run_until_complete(asyncio.gather(*tasks))

        return {url: content for url, content in zip(urls, results) if content}

    # ==================== ENHANCED: SEARCH WITH FULL CONTENT ====================

    def _get_tavily_documents(self, query: str, load_full_content: bool = True) -> List[Document]:
        """Enhanced Tavily search with optional full page loading."""
        try:
            enhanced_query = query  # Now using LLM-generated queries
            response = self.tavily_client.search(query=enhanced_query, max_results=10)
            results = response.get("results", [])

            documents = []
            urls_to_load = []

            for res in results[:10]:
                if len(res.get("content", "")) < 100:
                    continue

                url = res.get("url", "")

                # Apply date filtering
                if self._is_content_recent(res.get("content", ""), url):
                    # Store URL for full content loading
                    if load_full_content:
                        urls_to_load.append((url, res))
                    else:
                        # Use snippet
                        doc = Document(text=res.get("content", ""))
                        doc.metadata = {
                            "source": url,
                            "title": res.get("title", ""),
                            "provider": "Tavily",
                            "orig_order": len(documents),
                            "date_filtered": "2018+",
                        }
                        documents.append(doc)

                    if len(documents) >= 5:
                        break

            # Load full page content if enabled
            if load_full_content and urls_to_load:
                log.info(f"🔄 Loading full content for {len(urls_to_load)} Tavily results...")
                full_contents = self._load_full_pages_sync([url for url, _ in urls_to_load])

                for url, res in urls_to_load:
                    full_content = full_contents.get(url)
                    if full_content:
                        doc = Document(text=full_content)
                        doc.metadata = {
                            "source": url,
                            "title": res.get("title", ""),
                            "provider": "Tavily",
                            "orig_order": len(documents),
                            "date_filtered": "2018+",
                            "full_content": True,
                        }
                        documents.append(doc)

                        if len(documents) >= 5:
                            break

            log.info(f"✅ Tavily: {len(documents)} results after filtering")
            return documents

        except Exception as e:
            log.error(f"Error getting Tavily results: {e}")
            return []

    def _get_serper_documents(self, query: str, load_full_content: bool = True) -> List[Document]:
        """Enhanced Serper search with optional full page loading."""
        try:
            raw_results = self.serper_client.results(query)
            results = raw_results.get("organic", [])

            documents = []
            urls_to_load = []

            for res in results[:10]:
                if len(res.get("snippet", "")) < 100:
                    continue

                url = res.get("link", "")

                if self._is_content_recent(res.get("snippet", ""), url):
                    if load_full_content:
                        urls_to_load.append((url, res))
                    else:
                        doc = Document(text=res.get("snippet", ""))
                        doc.metadata = {
                            "source": url,
                            "title": res.get("title", ""),
                            "provider": "Google Serper",
                            "orig_order": len(documents),
                            "date_filtered": "2018+",
                        }
                        documents.append(doc)

                    if len(documents) >= 5:
                        break

            # Load full page content
            if load_full_content and urls_to_load:
                log.info(f"🔄 Loading full content for {len(urls_to_load)} Serper results...")
                full_contents = self._load_full_pages_sync([url for url, _ in urls_to_load])

                for url, res in urls_to_load:
                    full_content = full_contents.get(url)
                    if full_content:
                        doc = Document(text=full_content)
                        doc.metadata = {
                            "source": url,
                            "title": res.get("title", ""),
                            "provider": "Google Serper",
                            "orig_order": len(documents),
                            "date_filtered": "2018+",
                            "full_content": True,
                        }
                        documents.append(doc)

                        if len(documents) >= 5:
                            break

            log.info(f"✅ Serper: {len(documents)} results after filtering")
            return documents

        except Exception as e:
            log.error(f"Error getting Serper results: {e}")
            return []

    # ==================== RETAINED: ORIGINAL SCORING LOGIC ====================

    def _extract_date(self, content: str) -> datetime:
        """Extract date from content using regex patterns."""
        date_patterns = [
            r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{4}/\d{2}/\d{2}',
            r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2},?\s+\d{4}'
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, content.lower(), re.IGNORECASE)
            if matches:
                try:
                    return parse(matches[0])
                except (ValueError, TypeError):
                    continue
        return None

    def _get_source_quality_score(self, url: str) -> float:
        """Calculate quality score based on domain reputation."""
        high_quality_domains = [
            'nicomatic.com', 'ieee.org', 'iec.ch', 'en.wikipedia.org',
            'iso.org', 'nist.gov', 'electronics-tutorials.ws',
            'researchgate.net', 'scholar.google.com'
        ]

        medium_quality_domains = [
            '.edu', '.gov', '.org', 'arxiv.org', 'stackexchange.com',
            'techcrunch.com', 'electronicspoint.com'
        ]

        if any(domain in url.lower() for domain in high_quality_domains):
            return 1.0
        elif any(domain in url.lower() for domain in medium_quality_domains):
            return 0.8
        else:
            return 0.5

    def _is_content_recent(self, content: str, url: str) -> bool:
        """Check if content is from 2018 or later."""
        # Try URL first
        url_year_match = re.search(r'/(\d{4})/', url)
        if url_year_match:
            try:
                year = int(url_year_match.group(1))
                if year >= 2018:
                    return True
                elif year < 2018:
                    return False
            except ValueError:
                pass

        # Extract from content
        extracted_date = self._extract_date(content)
        if extracted_date:
            return extracted_date.year >= 2018

        return True  # Default to allowing if no date found

    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings."""
        return SequenceMatcher(None, content1.lower()[:500], content2.lower()[:500]).ratio()

    def _remove_smart_duplicates(self, documents: List[Document]) -> List[Document]:
        """Remove duplicates based on URL and content similarity."""
        if not documents:
            return documents

        unique_docs = []
        seen_urls = set()

        for doc in documents:
            url = doc.metadata.get("source", "")

            if url in seen_urls:
                continue

            is_duplicate = False
            for existing_doc in unique_docs:
                similarity = self._calculate_content_similarity(doc.text, existing_doc.text)
                if similarity > 0.85:
                    existing_quality = self._get_source_quality_score(existing_doc.metadata.get("source", ""))
                    new_quality = self._get_source_quality_score(url)

                    if new_quality > existing_quality:
                        unique_docs.remove(existing_doc)
                        seen_urls.discard(existing_doc.metadata.get("source", ""))
                        break
                    else:
                        is_duplicate = True
                        break

            if not is_duplicate:
                unique_docs.append(doc)
                seen_urls.add(url)

        return unique_docs

    def _compute_scores(self, query: str, documents: List[Document]) -> List[tuple]:
        """
        Compute sophisticated multi-factor scores: 25% similarity + 60% recency + 15% quality.
        This is your original excellent scoring system!
        """
        if not documents:
            return []

        current_date = datetime.now()

        try:
            if self.encoder is not None:
                query_embedding = self.encoder.embed_query(query)
                doc_embeddings = self.encoder.embed_documents([doc.text for doc in documents])

                query_embedding = np.array(query_embedding)
                doc_embeddings = np.array(doc_embeddings)

                similarities = np.dot(doc_embeddings, query_embedding) / (
                    np.linalg.norm(doc_embeddings, axis=1) * np.linalg.norm(query_embedding)
                )
            else:
                similarities = [
                    SequenceMatcher(None, query.lower(), doc.text.lower()).ratio()
                    for doc in documents
                ]
                similarities = np.array(similarities)

            scored_docs = []
            for doc, similarity in zip(documents, similarities):
                doc_date = self._extract_date(doc.text)

                if doc_date:
                    days_old = (current_date - doc_date).days
                    recency_score = math.exp(-max(0, days_old) / 365)
                else:
                    recency_score = 0.1  # Penalize missing dates

                quality_score = self._get_source_quality_score(doc.metadata.get("source", ""))

                # YOUR ORIGINAL EXCELLENT FORMULA
                combined_score = (0.25 * float(similarity)) + (0.60 * recency_score) + (0.15 * quality_score)

                scored_docs.append((doc, combined_score))

                # Add scores to metadata
                doc.metadata["similarity_score"] = float(similarity)
                doc.metadata["recency_score"] = float(recency_score)
                doc.metadata["combined_score"] = float(combined_score)
                doc.metadata["quality_score"] = float(quality_score)

            return sorted(scored_docs, key=lambda x: x[1], reverse=True)

        except Exception as e:
            log.error(f"Error computing scores: {e}")
            return list(zip(documents, [1.0] * len(documents)))

    # ==================== MAIN RETRIEVAL LOGIC ====================

    def _get_relevant_documents(self, query: str, use_llm_generation: bool = True) -> List[Document]:
        """
        Main retrieval function with LLM query generation and full content loading.

        Args:
            query: User query
            use_llm_generation: Whether to use LLM for query generation (default True)
        """
        # Step 1: Generate optimized queries using LLM
        if use_llm_generation:
            queries = self._generate_search_queries(query)
            log.info(f"🧠 Generated {len(queries)} optimized queries: {queries}")
        else:
            queries = [query]

        all_documents = []

        # Step 2: Search with each query
        for search_query in queries:
            log.info(f"\n🔍 Searching for: '{search_query}'")

            # Parallel search across providers
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                tavily_future = executor.submit(self._get_tavily_documents, search_query, load_full_content=True)
                serper_future = executor.submit(self._get_serper_documents, search_query, load_full_content=True)

                try:
                    tavily_docs = tavily_future.result(timeout=10)
                except Exception as e:
                    log.warning(f"⚠️ Tavily search error: {e}")
                    tavily_docs = []

                try:
                    serper_docs = serper_future.result(timeout=10)
                except Exception as e:
                    log.warning(f"⚠️ Serper search error: {e}")
                    serper_docs = []

            all_documents.extend(tavily_docs)
            all_documents.extend(serper_docs)

        # Step 3: Filter, deduplicate, and score
        filtered_docs = [doc for doc in all_documents if len(doc.text) >= 200]
        unique_docs = self._remove_smart_duplicates(filtered_docs)

        log.info(f"📊 Total: {len(all_documents)} → Filtered: {len(filtered_docs)} → Unique: {len(unique_docs)}")

        # Step 4: Score and rank using your excellent algorithm
        reranked_docs = self._compute_scores(query, unique_docs)

        # Return top 10
        final_docs = [doc for doc, score in reranked_docs[:10]]

        log.info(f"✅ Returning {len(final_docs)} top-scored documents")
        return final_docs

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """LlamaIndex integration."""
        query_str = query_bundle.query_str if isinstance(query_bundle, QueryBundle) else str(query_bundle)
        docs = self._get_relevant_documents(query_str)

        nodes_with_scores = []
        for i, doc in enumerate(docs):
            node = Node(text=doc.text, metadata=doc.metadata)
            score = doc.metadata.get("combined_score", 1.0 - (i * 0.1))
            nodes_with_scores.append(NodeWithScore(node=node, score=score))

        return nodes_with_scores

    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """Async version."""
        return self._get_relevant_documents(query)


# ==================== USAGE EXAMPLE ====================

if __name__ == "__main__":
    from tavily import TavilyClient
    from langchain_community.utilities import GoogleSerperAPIWrapper, DuckDuckGoSearchAPIWrapper

    # Initialize clients
    tavily = TavilyClient(api_key="your_tavily_key")
    serper = GoogleSerperAPIWrapper(serper_api_key="your_serper_key")
    ddg = DuckDuckGoSearchAPIWrapper()

    # Optional: Add LLM client for query generation
    # llm_client = YourOllamaClient()

    # Create enhanced retriever
    retriever = EnhancedMultiSearchRetriever(
        tavily_client=tavily,
        serper_client=serper,
        ddg_search=ddg,
        # llm_client=llm_client  # Uncomment to enable LLM query generation
    )

    # Search
    results = retriever._get_relevant_documents(
        "What are the latest developments in electric vehicle battery technology?"
    )

    print(f"\n📋 Found {len(results)} results:")
    for i, doc in enumerate(results, 1):
        print(f"\n{i}. {doc.metadata['title']}")
        print(f"   URL: {doc.metadata['source']}")
        print(f"   Provider: {doc.metadata['provider']}")
        print(f"   Score: {doc.metadata.get('combined_score', 'N/A'):.3f}")
        print(f"   Recency: {doc.metadata.get('recency_score', 'N/A'):.3f}")
        print(f"   Quality: {doc.metadata.get('quality_score', 'N/A'):.3f}")
        print(f"   Content length: {len(doc.text)} chars")
