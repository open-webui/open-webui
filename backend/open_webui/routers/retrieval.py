import json
import logging
import mimetypes
import os
import shutil
import asyncio
import time

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Union

from fastapi import (
    Depends,
    FastAPI,
    Query,
    File,
    Form,
    HTTPException,
    UploadFile,
    Request,
    status,
    APIRouter,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
import tiktoken


from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    TokenTextSplitter,
    MarkdownHeaderTextSplitter,
)
from langchain_core.documents import Document

from open_webui.models.files import FileModel, FileUpdateForm, Files
from open_webui.utils.access_control.files import has_access_to_file
from open_webui.models.knowledge import Knowledges
from open_webui.storage.provider import Storage
from open_webui.internal.db import get_async_db, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession


from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT

# Document loaders

from open_webui.retrieval.loaders.youtube import YoutubeLoader

# Web search engines
from open_webui.retrieval.web.main import SearchResult
from open_webui.retrieval.web.utils import get_web_loader
from open_webui.retrieval.web.ollama import search_ollama_cloud
from open_webui.retrieval.web.perplexity_search import search_perplexity_search
from open_webui.retrieval.web.brave import search_brave
from open_webui.retrieval.web.brave_llm_context import search_brave_llm_context
from open_webui.retrieval.web.kagi import search_kagi
from open_webui.retrieval.web.mojeek import search_mojeek
from open_webui.retrieval.web.bocha import search_bocha
from open_webui.retrieval.web.duckduckgo import search_duckduckgo
from open_webui.retrieval.web.google_pse import search_google_pse
from open_webui.retrieval.web.jina_search import search_jina
from open_webui.retrieval.web.searchapi import search_searchapi
from open_webui.retrieval.web.serpapi import search_serpapi
from open_webui.retrieval.web.searxng import search_searxng
from open_webui.retrieval.web.yacy import search_yacy
from open_webui.retrieval.web.serper import search_serper
from open_webui.retrieval.web.serply import search_serply
from open_webui.retrieval.web.serpstack import search_serpstack
from open_webui.retrieval.web.tavily import search_tavily
from open_webui.retrieval.web.bing import search_bing
from open_webui.retrieval.web.azure import search_azure
from open_webui.retrieval.web.exa import search_exa
from open_webui.retrieval.web.perplexity import search_perplexity
from open_webui.retrieval.web.sougou import search_sougou
from open_webui.retrieval.web.firecrawl import search_firecrawl
from open_webui.retrieval.web.external import search_external
from open_webui.retrieval.web.yandex import search_yandex
from open_webui.retrieval.web.ydc import search_youcom

from open_webui.retrieval.utils import (
    build_loader_from_config,
    filter_accessible_collections,
    get_content_from_url,
    get_embedding_function,
    get_reranking_function,
    get_model_path,
    query_collection,
    query_collection_with_hybrid_search,
    query_doc,
    query_doc_with_hybrid_search,
)
from open_webui.retrieval.vector.utils import filter_metadata
from open_webui.utils.misc import (
    calculate_sha256_string,
    sanitize_text_for_db,
)
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_permission

from open_webui.config import (
    ENV,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
    RAG_RERANKING_MODEL_AUTO_UPDATE,
    RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
    UPLOAD_DIR,
    DEFAULT_LOCALE,
    RAG_EMBEDDING_CONTENT_PREFIX,
    RAG_EMBEDDING_QUERY_PREFIX,
    VECTOR_DB,
    # Video/Audio chunking config
    VIDEO_AUDIO_CHUNKING_STRATEGY,
    VIDEO_AUDIO_CHUNK_TARGET_DURATION,
    VIDEO_AUDIO_CHUNK_MAX_DURATION,
    VIDEO_AUDIO_CHUNK_OVERLAP_DURATION,
)
from open_webui.env import (
    DEVICE_TYPE,
    DOCKER,
    RAG_EMBEDDING_TIMEOUT,
    SENTENCE_TRANSFORMERS_BACKEND,
    SENTENCE_TRANSFORMERS_MODEL_KWARGS,
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND,
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS,
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_SIGMOID_ACTIVATION_FUNCTION,
)

from open_webui.constants import ERROR_MESSAGES

log = logging.getLogger(__name__)

##########################################
#
# Utility functions
# Give us this day our relevant chunks, and lead us
# not into hallucination, but deliver us from noise.
#
##########################################


def get_namespace_for_collection(collection_name: str) -> Optional[str]:
    """
    Get the appropriate namespace for a collection based on vector DB type.

    Pinecone Best Practice: Use human-readable namespace with collection name prefix.
    Format: "{sanitized-name}-{collection-id}" for easier identification.

    This provides better performance by limiting query scope to specific collections
    and prevents cross-collection interference.

    For other vector databases (Chroma, Qdrant, etc.), namespaces aren't used;
    instead, they rely on collection-based isolation.

    Args:
        collection_name: Name of the collection (e.g., "file-abc123", "494b175b-3672...")

    Returns:
        - For Pinecone: "{name}-{id}" (e.g., "fosd-494b175b-3672..." for knowledge bases)
        - For other DBs: None (use default behavior)

    Performance Impact:
        - Pinecone queries only scan the specific namespace
        - Reduces query latency for large deployments with many collections
        - Better scalability as collections grow
        - Human-readable namespaces easier to debug

    Example:
        namespace = get_namespace_for_collection("494b175b-3672-45a2-bb2a-ea21f3328818")
        # Returns: "my-knowledge-494b175b-3672-45a2-bb2a-ea21f3328818"

        VECTOR_DB_CLIENT.insert(
            collection_name="494b175b-3672-45a2-bb2a-ea21f3328818",
            items=vectors,
            namespace="my-knowledge-494b175b-3672-45a2-bb2a-ea21f3328818"
        )
    """
    # Extract actual value if VECTOR_DB is a PersistentConfig object
    vector_db_type = VECTOR_DB.value if hasattr(VECTOR_DB, "value") else VECTOR_DB

    if vector_db_type == "pinecone":
        # Try to get a human-readable name for the collection
        prefix = None

        # Check if this is a knowledge base (UUID format without prefix)
        if not collection_name.startswith(("file-", "user-memory-", "email-")):
            try:
                # Import here to avoid circular dependency
                from open_webui.models.knowledge import Knowledges

                knowledge = Knowledges.get_knowledge_by_id(collection_name)
                if knowledge and knowledge.name:
                    # Sanitize knowledge name for namespace
                    # Convert to lowercase, replace spaces/special chars with dashes
                    import re

                    sanitized = re.sub(r"[^a-z0-9]+", "-", knowledge.name.lower())
                    # Remove leading/trailing dashes
                    sanitized = sanitized.strip("-")
                    # Limit length to avoid overly long namespaces
                    if sanitized:
                        prefix = sanitized[:50]  # Max 50 chars for prefix
            except Exception as e:
                # If lookup fails, just use collection ID
                pass

        # Build namespace: "{prefix}-{collection_id}" or just "{collection_id}"
        if prefix:
            return f"{prefix}-{collection_name}"
        else:
            # For files, memories, or if name lookup failed, use collection name as-is
            # This maintains compatibility with email-{user_id} pattern
            return collection_name

    # Other vector DBs (Chroma, Qdrant, Milvus, etc.) use collections directly
    return None


def extract_enhanced_metadata(text: str, use_llm: bool = False) -> dict:
    """
    Extract comprehensive metadata from text for improved RAG retrieval.

    High-Impact Features:
    1. Chunk Summary & Title (helps users understand relevance)
    2. Enhanced Entity Extraction (people, orgs, locations)
    3. Question Generation (improves question-based retrieval)

    Args:
        text: Text to analyze
        use_llm: If True, use LLM for extraction (more accurate but slower)

    Returns:
        Dictionary with summary, title, topics, entities, keywords, questions
    """
    if not text or len(text.strip()) < 10:
        return {
            "chunk_summary": "",
            "chunk_title": "",
            "topics": [],
            "entities_people": [],
            "entities_organizations": [],
            "entities_locations": [],
            "keywords": [],
            "potential_questions": [],
        }

    # Compile regex patterns once (performance optimization)
    # These are stateless and can be reused
    text_length = len(text)

    # === FEATURE 1: CHUNK SUMMARY & TITLE ===
    chunk_summary, chunk_title = _generate_summary_and_title(text)

    # === FEATURE 2: ENHANCED ENTITY EXTRACTION ===
    entities = _extract_enhanced_entities(text)

    # === FEATURE 3: QUESTION GENERATION ===
    questions = _generate_potential_questions(text)

    # Extract keywords (words longer than 5 chars, frequent)
    # Performance: Use Counter for better performance than manual dict
    from collections import Counter

    words = re.findall(r"\b[a-z]{6,}\b", text.lower())
    word_freq = Counter(words)

    # Get top keywords by frequency (minimum 2 occurrences)
    keywords = [word for word, freq in word_freq.most_common(10) if freq > 1]

    # Extract potential topics (capitalized phrases) with comprehensive stopword filtering
    # Comprehensive English stopwords that should never be topics
    STOPWORDS = {
        # Articles & Demonstratives
        "A",
        "An",
        "The",
        "This",
        "That",
        "These",
        "Those",
        # Pronouns
        "I",
        "You",
        "He",
        "She",
        "It",
        "We",
        "They",
        "Me",
        "Him",
        "Her",
        "Us",
        "Them",
        "My",
        "Your",
        "His",
        "Her",
        "Its",
        "Our",
        "Their",
        "Mine",
        "Yours",
        "Hers",
        "Ours",
        "Theirs",
        "Myself",
        "Yourself",
        "Himself",
        "Herself",
        "Itself",
        "Ourselves",
        "Yourselves",
        "Themselves",
        # Conjunctions
        "And",
        "But",
        "Or",
        "Nor",
        "For",
        "Yet",
        "So",
        "Because",
        "Since",
        "Unless",
        "Although",
        "Though",
        # Prepositions
        "In",
        "On",
        "At",
        "To",
        "For",
        "Of",
        "From",
        "By",
        "With",
        "About",
        "Against",
        "Between",
        "Into",
        "Through",
        "During",
        "Before",
        "After",
        "Above",
        "Below",
        "Up",
        "Down",
        "Out",
        "Off",
        "Over",
        "Under",
        "Again",
        "Further",
        "Then",
        "Once",
        "Here",
        "There",
        "Where",
        "When",
        # Common Verbs
        "Am",
        "Is",
        "Are",
        "Was",
        "Were",
        "Be",
        "Been",
        "Being",
        "Have",
        "Has",
        "Had",
        "Having",
        "Do",
        "Does",
        "Did",
        "Doing",
        "Will",
        "Would",
        "Should",
        "Could",
        "Might",
        "May",
        "Can",
        "Must",
        "Shall",
        "Get",
        "Gets",
        "Got",
        "Getting",
        "Make",
        "Makes",
        "Made",
        "Making",
        "Go",
        "Goes",
        "Went",
        # Interrogatives
        "Who",
        "What",
        "Which",
        "When",
        "Where",
        "Why",
        "How",
        "Whose",
        "Whom",
        # Quantifiers & Adjectives
        "All",
        "Any",
        "Both",
        "Each",
        "Few",
        "More",
        "Most",
        "Other",
        "Some",
        "Such",
        "No",
        "Only",
        "Own",
        "Same",
        "Than",
        "Too",
        "Very",
        "Just",
        "Now",
        "Even",
        "Also",
        "Well",
        "Many",
        "Much",
        "Every",
        "Another",
        "Still",
        "Back",
        "New",
        "Old",
        "Good",
        "Bad",
        "Great",
        # Negations & Modals
        "Not",
        "Never",
        "Nothing",
        "Nobody",
        "None",
        "Neither",
        "Nowhere",
        # Common sentence starters
        "If",
        "Whether",
        "As",
        "Like",
        "Unlike",
    }

    # Extract all capitalized phrases
    topics_raw = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)

    # Apply comprehensive filtering
    topics_filtered = []
    for topic in topics_raw:
        # Skip if it's in stopwords
        if topic in STOPWORDS:
            continue
        # Skip very short words (likely not meaningful topics)
        if len(topic) <= 2:
            continue
        # Skip if it's a single letter followed by lowercase (e.g., "A" or "I")
        if len(topic) == 1:
            continue
        # Add to filtered list
        topics_filtered.append(topic)

    # Remove duplicates, sort for consistency, limit to top 5
    topics = sorted(set(topics_filtered))[:5]

    return {
        "chunk_summary": chunk_summary,
        "chunk_title": chunk_title,
        "topics": topics,
        "entities_people": entities["people"][:5],
        "entities_organizations": entities["organizations"][:5],
        "entities_locations": entities["locations"][:5],
        "keywords": keywords,
        "potential_questions": questions,
    }


def _generate_summary_and_title(text: str) -> tuple:
    """
    Generate a concise summary and title for a text chunk.
    Uses extractive summarization (first + important sentences).

    Returns:
        Tuple of (summary, title)
    """
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    if not sentences:
        return "", ""

    # Title: Extract from first sentence or use key phrases
    first_sentence = sentences[0]
    title_words = first_sentence.split()[:8]  # First 8 words
    title = " ".join(title_words)
    if len(first_sentence) > len(title):
        title += "..."

    # Summary: Use first sentence + most informative sentence
    summary = sentences[0]

    # Find sentence with most keywords/numbers (likely most informative)
    if len(sentences) > 1:
        scored_sentences = []
        for sent in sentences[1:4]:  # Check next 3 sentences
            # Score based on: numbers, question words, key phrases
            score = 0
            score += len(re.findall(r"\d+", sent)) * 2  # Numbers are informative
            score += len(re.findall(r"\b[A-Z][a-z]+\b", sent))  # Proper nouns
            if any(
                word in sent.lower()
                for word in [
                    "important",
                    "key",
                    "main",
                    "significant",
                    "shows",
                    "found",
                ]
            ):
                score += 3
            scored_sentences.append((score, sent))

        if scored_sentences:
            scored_sentences.sort(reverse=True, key=lambda x: x[0])
            best_sentence = scored_sentences[0][1]
            if best_sentence != summary:
                summary = f"{summary}. {best_sentence}"

    # Limit summary length
    if len(summary) > 250:
        summary = summary[:247] + "..."

    return summary, title


def _extract_enhanced_entities(text: str) -> dict:
    """
    Enhanced entity extraction using multiple patterns and heuristics.
    Extracts: people, organizations, locations.

    Returns:
        Dictionary with lists of entities by type
    """
    # Email-specific terms that should never be extracted as entities
    EMAIL_STOPWORDS = {
        # Email actions/prefixes
        "Re",
        "Fwd",
        "Fw",
        "Reply",
        "Forward",
        "Forwarded",
        "Help",
        "Thanks",
        "Thank",
        "Hello",
        "Hi",
        "Hey",
        "Dear",
        "Best",
        "Regards",
        "Sincerely",
        "Cheers",
        # Email metadata terms
        "Subject",
        "From",
        "To",
        "Cc",
        "Bcc",
        "Date",
        "Sent",
        "Received",
        "Inbox",
        "Outbox",
        "Draft",
        "Spam",
        "Trash",
        "Attachment",
        "Attachments",
        "Attached",
        "File",
        "Files",
        # Common email phrases
        "Please",
        "Kindly",
        "See",
        "Below",
        "Above",
        "Following",
        "Updated",
        "Update",
        "New",
        "Old",
        "Latest",
        "Recent",
        "Important",
        "Urgent",
        "Action",
        "Required",
        "Needed",
        "Meeting",
        "Call",
        "Reminder",
        "Notice",
        "Alert",
        "Invoice",
        "Receipt",
        "Order",
        "Confirmation",
        "Summary",
        # Calendar/scheduling
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
        "Today",
        "Tomorrow",
        "Weekly",
        "Monthly",
        "Daily",
        "Annual",
        "Quarterly",
        # Technical terms that look like names
        "Total",
        "Amount",
        "Due",
        "Balance",
        "Payment",
        "Status",
        "View",
        "Click",
        "Download",
        "Open",
        "Read",
        "More",
    }

    def is_valid_person_name(name: str) -> bool:
        """Check if extracted text is likely a real person name."""
        words = name.split()
        # All words must not be stopwords
        for word in words:
            if word in EMAIL_STOPWORDS:
                return False
        # At least one word should be longer than 2 chars
        if not any(len(w) > 2 for w in words):
            return False
        return True

    # ===== PEOPLE EXTRACTION =====
    people = set()

    # Pattern 1: Full names (First Last, First Middle Last)
    people.update(re.findall(r"\b[A-Z][a-z]+\s+(?:[A-Z][a-z]+\s+)?[A-Z][a-z]+\b", text))

    # Pattern 2: Names with titles (Dr., Mr., Ms., Prof., etc.)
    people.update(
        re.findall(
            r"\b(?:Dr|Mr|Ms|Mrs|Prof|Professor|Rev)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b",
            text,
        )
    )

    # ===== ORGANIZATION EXTRACTION =====
    organizations = set()

    # Pattern 1: Organizations with explicit keywords (combined into single regex for performance)
    org_suffix = r"(?:Inc|Corp|Corporation|Company|LLC|Ltd|Institute|Foundation|Organization|Association|University|College|Agency|Department|Bureau|Commission|Council|Center|Centre|Group|Team|Network|Alliance|Coalition|Initiative|Project|Program)"
    organizations.update(re.findall(rf"\b(?:The\s+)?[A-Z][A-Za-z\s&]+{org_suffix}\b", text))

    # Pattern 2: All-caps acronyms (3-6 letters, likely organizations)
    common_words = {
        "US",
        "UK",
        "EU",
        "UN",
        "OK",
        "PDF",
        "CEO",
        "CFO",
        "CTO",
        "AI",
        "IT",
        "HR",
        "FAQ",
        "DIY",
    }
    acronyms = [a for a in re.findall(r"\b[A-Z]{3,6}\b", text) if a not in common_words]
    organizations.update(acronyms)

    # Pattern 3: Media organizations
    media_suffix = (
        r"(?:Media|News|Press|Journal|Times|Post|Tribune|Herald|Gazette|Network|Channel|Radio|TV|Broadcasting)"
    )
    organizations.update(re.findall(rf"\b[A-Z][A-Za-z\s]+{media_suffix}\b", text))

    # ===== LOCATION EXTRACTION =====
    locations = set()

    # Pattern 1: City, State/Country patterns
    locations.update(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s+[A-Z]{2}\b", text))  # City, ST
    locations.update(re.findall(r"\b[A-Z][a-z]+,\s+[A-Z][a-z]+\b", text))  # City, Country

    # Pattern 2: Preposition + location (in/at/from/to Location)
    prep_locations = re.findall(r"\b(?:in|at|from|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", text)
    locations.update([loc for loc in prep_locations if len(loc) > 2])

    # Pattern 3: Geographic keywords
    geo_suffix = r"(?:City|County|State|Province|Region|District|Area|Zone|Bay|Valley|Mountain|River|Lake|Ocean|Sea|Island|Peninsula)"
    locations.update(re.findall(rf"\b[A-Z][a-z]+\s+{geo_suffix}\b", text))

    # ===== CLEANUP & FILTERING =====
    # Remove people names that appear in organizations (keep most specific)
    people_clean = [p for p in people if not any(p in org for org in organizations)]

    # Apply email stopword filtering to people
    people_filtered = [p for p in people_clean if is_valid_person_name(p)]

    # Filter by minimum length and convert to sorted lists for consistency
    return {
        "people": sorted([p.strip() for p in people_filtered if len(p.strip()) > 2]),
        "organizations": sorted([o.strip() for o in organizations if len(o.strip()) > 2]),
        "locations": sorted([loc.strip() for loc in locations if len(loc.strip()) > 2]),
    }


def _generate_potential_questions(text: str) -> list:
    """
    Generate potential questions that this text chunk could answer.
    Uses pattern matching and heuristics for 6 question types.

    Returns:
        List of up to 5 unique questions
    """
    questions = []

    # Extract and filter sentences once for reuse
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 10]

    if not sentences:
        return []

    # Pattern 1: Extract explicit questions from text (only if they're not rhetorical)
    # Filter out rhetorical questions like "guess what?", "you know what?", "right?"
    rhetorical_patterns = [
        r"guess what\?",
        r"you know what\?",
        r"know what\?",
        r"right\?",
        r"okay\?",
        r"yeah\?",
        r"see\?",
        r"get it\?",
    ]
    explicit_questions = re.findall(r"[A-Z][^.!?]*\?", text)
    for q in explicit_questions[:3]:
        # Skip if it's a rhetorical question or too short
        if len(q) > 15 and not any(re.search(pattern, q, re.IGNORECASE) for pattern in rhetorical_patterns):
            questions.append(q)

    # Limit sentence processing to first 5 for performance
    sentences_subset = sentences[:5]

    # Pattern 2: Generate questions from statements with numbers/statistics
    for sentence in sentences_subset:
        numbers = re.findall(r"\d+(?:\.\d+)?%?", sentence)
        if not numbers:
            continue

        for num in numbers[:2]:  # Limit to 2 numbers per sentence
            words = sentence.split()
            # Find word index containing the number
            num_idx = next((i for i, w in enumerate(words) if num in w), None)
            if num_idx is not None:
                # Extract context (3 words before and after)
                context_start = max(0, num_idx - 3)
                context_end = min(len(words), num_idx + 4)
                context = " ".join(words[context_start:context_end])

                question_type = "What percentage" if "%" in num else "What are the numbers related to"
                questions.append(f"{question_type} {context.lower()}?")

    # Pattern 3: Generate "What is..." questions for definitions
    for sentence in sentences_subset:
        sentence_lower = sentence.lower()
        if not any(word in sentence_lower for word in [" is ", " are ", " means ", " refers to "]):
            continue

        # Try to extract subject (the thing being defined)
        match = re.search(
            r"^((?:a|an|the)?\s*[A-Z][^,]+?)\s+(?:is|are|means|refers to)\s+",
            sentence,
            re.IGNORECASE,
        )
        if match:
            subject = match.group(1).strip()
            # Clean up articles and check length
            subject = re.sub(r"^(a|an|the)\s+", "", subject, flags=re.IGNORECASE).strip()
            # Check if subject is reasonable (proper noun or important term)
            if 3 < len(subject) < 50 and (
                subject[0].isupper()
                or any(word in subject.lower() for word in ["approach", "method", "process", "system", "model"])
            ):
                # Capitalize first letter for consistency
                subject = subject[0].upper() + subject[1:]
                questions.append(f"What is {subject}?")

    # Pattern 4: Generate "Who..." questions for people mentions
    people_names = re.findall(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", text)[:2]
    for name in people_names:
        # Find action verb following the name
        match = re.search(rf"{re.escape(name)}\s+([a-z]+(?:\s+[a-z]+){{0,4}})", text)
        if match:
            questions.append(f"Who {match.group(1)}?")

    # Pattern 5: Generate "How..." questions for process/method descriptions
    how_keywords = ["how", "process", "method", "way", "approach", "technique"]
    for sentence in sentences_subset:
        if any(word in sentence.lower() for word in how_keywords):
            verbs = re.findall(r"\b(?:to\s+)?([a-z]+(?:ing|ed)?)\b", sentence.lower())
            if verbs:
                questions.append(f"How to {verbs[0]}?")
                break  # Only one "how" question needed

    # Pattern 6: Generate "Why..." questions for causal/explanatory statements
    causal_keywords = ["because", "since", "reason", "cause", "due to", "result"]
    for sentence in sentences_subset:
        if any(word in sentence.lower() for word in causal_keywords):
            topic = " ".join(sentence.split()[:10])
            if len(topic) > 10:
                questions.append(f"Why {topic.lower()}?")
                break  # Only one "why" question needed

    # Deduplicate while preserving order and limit to 5 questions
    seen = set()
    unique_questions = []
    for q in questions:
        q_clean = q.strip()
        q_normalized = q_clean.lower()
        if q_normalized not in seen and 10 < len(q_clean) < 150:
            seen.add(q_normalized)
            unique_questions.append(q_clean)
            if len(unique_questions) >= 5:
                break

    return unique_questions


####################################
# Video/Audio Processing Utilities
####################################


def get_config_value(request, attr_name: str, fallback_config):
    """
    Safely get a config value from app state, handling PersistentConfig wrappers.

    Args:
        request: FastAPI request object
        attr_name: Name of the config attribute
        fallback_config: Fallback PersistentConfig or value if not in app state

    Returns:
        The actual config value (unwrapped from PersistentConfig if needed)
    """
    value = getattr(
        request.app.state.config,
        attr_name,
        fallback_config.value if hasattr(fallback_config, 'value') else fallback_config,
    )
    if hasattr(value, 'value'):
        value = value.value
    return value


def build_media_segment_urls(file_id: str, start: float, end: float, is_video: bool) -> dict:
    """
    Build media segment URLs for video/audio playback.

    Args:
        file_id: The file ID
        start: Start timestamp in seconds
        end: End timestamp in seconds
        is_video: Whether the source is a video file

    Returns:
        Dict with video_url, video_segment_url, and/or audio_segment_url
    """
    urls = {}

    if is_video:
        urls["video_url"] = f"/api/v1/files/{file_id}/video"
        urls["video_segment_url"] = f"/api/v1/audio/video/files/{file_id}/segment" f"?start={start}&end={end}"

    # Always provide audio URL (works for both audio and video files)
    urls["audio_segment_url"] = f"/api/v1/audio/files/{file_id}/segment" f"?start={start}&end={end}"

    return urls


def build_enriched_chunk_metadata(
    base_metadata: dict,
    enrichment: dict,
    chunk_index: int,
    total_chunks: int,
    timestamp_start: float = None,
    timestamp_end: float = None,
    duration: float = None,
    chunking_strategy: str = "semantic",
    has_overlap: bool = False,
    transcript_language: str = None,
    transcript_duration: float = None,
    media_urls: dict = None,
) -> dict:
    """
    Build standardized enriched metadata for video/audio chunks.

    This centralizes the metadata construction to avoid duplication
    between semantic and character-based chunking paths.

    Args:
        base_metadata: Base metadata dict (file info, filtered_meta)
        enrichment: Output from extract_enhanced_metadata()
        chunk_index: Index of this chunk
        total_chunks: Total number of chunks
        timestamp_start: Start timestamp in seconds
        timestamp_end: End timestamp in seconds
        duration: Duration of chunk in seconds
        chunking_strategy: "semantic" or "character"
        has_overlap: Whether this chunk has overlap from previous
        transcript_language: Detected language
        transcript_duration: Total transcript duration
        media_urls: Dict with video/audio segment URLs

    Returns:
        Complete enriched metadata dict
    """
    metadata = {
        **base_metadata,
        # High-Impact Features
        "chunk_summary": enrichment.get("chunk_summary", ""),
        "chunk_title": enrichment.get("chunk_title", ""),
        "potential_questions": enrichment.get("potential_questions", []),
        # Enhanced Entity Extraction
        "topics": enrichment.get("topics", []),
        "entities_people": enrichment.get("entities_people", []),
        "entities_organizations": enrichment.get("entities_organizations", []),
        "entities_locations": enrichment.get("entities_locations", []),
        "keywords": enrichment.get("keywords", []),
        # Chunk position metadata
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        # Chunking strategy metadata
        "chunking_strategy": chunking_strategy,
    }

    # Add timestamp metadata only if available
    if timestamp_start is not None:
        metadata["timestamp_start"] = timestamp_start
    if timestamp_end is not None:
        metadata["timestamp_end"] = timestamp_end
    if duration is not None:
        metadata["duration"] = duration

    # Add semantic chunking specific metadata
    if chunking_strategy == "semantic":
        metadata["has_overlap"] = has_overlap

    # Add media URLs
    if media_urls:
        metadata.update(media_urls)

    # Add transcript metadata
    if transcript_language is not None:
        metadata["transcript_language"] = transcript_language
    if transcript_duration is not None:
        metadata["transcript_duration"] = transcript_duration

    return metadata


def create_semantic_chunks_from_segments(
    segments: list,
    target_duration: float = 30.0,
    max_duration: float = 60.0,
    overlap_duration: float = 5.0,
) -> list:
    """
    Create semantic chunks from Whisper transcript segments based on natural speech boundaries.

    This approach is superior to character-based chunking because:
    1. Preserves complete sentences/thoughts (cuts at sentence boundaries)
    2. Respects natural pauses in speech
    3. Maintains accurate timestamp alignment
    4. Includes overlap for context preservation at boundaries

    Args:
        segments: List of Whisper segments with {id, start, end, text, words}
        target_duration: Target duration in seconds for each chunk (soft limit)
        max_duration: Maximum duration in seconds (hard limit)
        overlap_duration: Seconds of overlap to include from previous chunk

    Returns:
        List of chunk dictionaries with {text, start, end, duration, segment_ids, words, overlap_text}
    """
    if not segments:
        return []

    chunks = []
    current_chunk = {
        "segments": [],
        "text": "",
        "start": None,
        "end": None,
        "segment_ids": [],
        "words": [],
        "overlap_text": "",  # Text carried over from previous chunk for context
    }

    for seg_idx, segment in enumerate(segments):
        segment_text = segment.get("text", "").strip()
        segment_start = segment.get("start", 0)
        segment_end = segment.get("end", 0)
        segment_id = segment.get("id", seg_idx)
        segment_words = segment.get("words", [])

        # Initialize chunk start time
        if current_chunk["start"] is None:
            current_chunk["start"] = segment_start

        # Add segment to current chunk
        if current_chunk["text"]:
            current_chunk["text"] += " " + segment_text
        else:
            current_chunk["text"] = segment_text

        current_chunk["segments"].append(segment)
        current_chunk["end"] = segment_end
        current_chunk["segment_ids"].append(segment_id)
        current_chunk["words"].extend(segment_words)

        # Calculate current duration
        duration = current_chunk["end"] - current_chunk["start"]

        # Detect natural break points for chunking
        text_stripped = segment_text.rstrip()
        is_sentence_end = text_stripped.endswith(('.', '!', '?', '."', '!"', '?"'))

        # Check for long pause after this segment (indicates topic change)
        is_long_pause = False
        if seg_idx < len(segments) - 1:
            next_segment_start = segments[seg_idx + 1].get("start", segment_end)
            pause_duration = next_segment_start - segment_end
            is_long_pause = pause_duration > 1.5  # 1.5 second pause indicates natural break

        # Decide whether to finalize this chunk
        should_finalize = False

        if duration >= max_duration:
            # Hard limit reached - must finalize
            should_finalize = True
        elif duration >= target_duration:
            # Target reached - finalize at natural boundary
            if is_sentence_end or is_long_pause:
                should_finalize = True

        if should_finalize and current_chunk["text"].strip():
            # Calculate chunk metadata
            chunk_duration = current_chunk["end"] - current_chunk["start"]

            chunks.append(
                {
                    "text": current_chunk["text"].strip(),
                    "start": round(current_chunk["start"], 2),
                    "end": round(current_chunk["end"], 2),
                    "duration": round(chunk_duration, 2),
                    "segment_ids": current_chunk["segment_ids"].copy(),
                    "words": current_chunk["words"].copy(),
                    "overlap_text": current_chunk["overlap_text"],
                    "chunk_index": len(chunks),
                }
            )

            # Create overlap content for next chunk
            # Find segments that fall within the overlap window
            overlap_segments = []
            overlap_text_parts = []
            overlap_words = []
            overlap_start = current_chunk["end"] - overlap_duration

            for seg in current_chunk["segments"]:
                if seg.get("start", 0) >= overlap_start:
                    overlap_segments.append(seg)
                    overlap_text_parts.append(seg.get("text", "").strip())
                    overlap_words.extend(seg.get("words", []))

            # Start new chunk with overlap
            if overlap_segments:
                current_chunk = {
                    "segments": overlap_segments,
                    "text": " ".join(overlap_text_parts),
                    "start": overlap_segments[0].get("start", 0),
                    "end": None,
                    "segment_ids": [s.get("id", i) for i, s in enumerate(overlap_segments)],
                    "words": overlap_words,
                    "overlap_text": " ".join(overlap_text_parts),  # Mark as overlap
                }
            else:
                current_chunk = {
                    "segments": [],
                    "text": "",
                    "start": None,
                    "end": None,
                    "segment_ids": [],
                    "words": [],
                    "overlap_text": "",
                }

    # Don't forget the last chunk
    if current_chunk["text"].strip():
        chunk_duration = (current_chunk["end"] or 0) - (current_chunk["start"] or 0)
        chunks.append(
            {
                "text": current_chunk["text"].strip(),
                "start": round(current_chunk["start"] or 0, 2),
                "end": round(current_chunk["end"] or 0, 2),
                "duration": round(chunk_duration, 2),
                "segment_ids": current_chunk["segment_ids"].copy(),
                "words": current_chunk["words"].copy(),
                "overlap_text": current_chunk["overlap_text"],
                "chunk_index": len(chunks),
            }
        )

    # Add total_chunks to each chunk
    total_chunks = len(chunks)
    for chunk in chunks:
        chunk["total_chunks"] = total_chunks

    log.info(
        f"Created {len(chunks)} semantic chunks from {len(segments)} segments "
        f"(target: {target_duration}s, max: {max_duration}s, overlap: {overlap_duration}s)"
    )

    return chunks


def align_chunk_with_timestamps(chunk_text: str, segments: list, chunk_start_char: int, full_text: str) -> dict:
    """
    Find the timestamps that align with a text chunk from the full transcript.

        Args:
        chunk_text: The chunked text
        segments: List of segments with timestamps from Whisper
        chunk_start_char: Character position where this chunk starts in full transcript
        full_text: The complete transcript text

        Returns:
        Dictionary with timestamp_start, timestamp_end, and matching segments
    """
    if not segments or not chunk_text:
        return {
            "timestamp_start": None,
            "timestamp_end": None,
            "segment_ids": [],
            "duration": None,
        }

    # Find which segments overlap with this chunk based on text matching
    chunk_words = set(chunk_text.lower().split())
    chunk_length = len(chunk_text)
    chunk_end_char = chunk_start_char + chunk_length

    matching_segments = []
    current_char_pos = 0

    for segment in segments:
        segment_text = segment.get("text", "")
        segment_start_char = current_char_pos
        segment_end_char = current_char_pos + len(segment_text)

        # Check if this segment overlaps with the chunk
        if not (segment_end_char < chunk_start_char or segment_start_char > chunk_end_char):
            matching_segments.append(segment)

        current_char_pos = segment_end_char + 1  # +1 for space between segments

    if matching_segments:
        return {
            "timestamp_start": round(matching_segments[0]["start"], 2),
            "timestamp_end": round(matching_segments[-1]["end"], 2),
            "segment_ids": [seg.get("id", i) for i, seg in enumerate(matching_segments)],
            "duration": round(matching_segments[-1]["end"] - matching_segments[0]["start"], 2),
        }

    return {
        "timestamp_start": None,
        "timestamp_end": None,
        "segment_ids": [],
        "duration": None,
    }


def get_ef(
    engine: str,
    embedding_model: str,
    auto_update: bool = RAG_EMBEDDING_MODEL_AUTO_UPDATE,
):
    ef = None
    if embedding_model and engine == '':
        from sentence_transformers import SentenceTransformer

        try:
            ef = SentenceTransformer(
                get_model_path(embedding_model, auto_update),
                device=DEVICE_TYPE,
                trust_remote_code=RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
                backend=SENTENCE_TRANSFORMERS_BACKEND,
                model_kwargs=SENTENCE_TRANSFORMERS_MODEL_KWARGS,
            )
        except Exception as e:
            log.error(f'Error loading SentenceTransformer: {e}')

    return ef


def get_rf(
    engine: str = '',
    reranking_model: Optional[str] = None,
    external_reranker_url: str = '',
    external_reranker_api_key: str = '',
    external_reranker_timeout: str = '',
    auto_update: bool = RAG_RERANKING_MODEL_AUTO_UPDATE,
):
    rf = None
    # Convert timeout string to int or None (system default)
    timeout_value = int(external_reranker_timeout) if external_reranker_timeout else None
    if reranking_model:
        if any(model in reranking_model for model in ['jinaai/jina-colbert-v2']):
            try:
                from open_webui.retrieval.models.colbert import ColBERT

                rf = ColBERT(
                    get_model_path(reranking_model, auto_update),
                    env='docker' if DOCKER else None,
                )

            except Exception as e:
                log.error(f'ColBERT: {e}')
                raise Exception(ERROR_MESSAGES.DEFAULT(e))
        else:
            if engine == "pinecone":
                try:
                    from open_webui.retrieval.models.pinecone_reranker import (
                        PineconeReranker,
                    )

                    rf = PineconeReranker(
                        api_key=None,  # Will use PINECONE_API_KEY from environment
                        model=reranking_model,
                    )
                except Exception as e:
                    log.error(f"PineconeReranking: {e}")
                    raise Exception(ERROR_MESSAGES.DEFAULT(e))
            elif engine == 'external':
                try:
                    from open_webui.retrieval.models.external import ExternalReranker

                    rf = ExternalReranker(
                        url=external_reranker_url,
                        api_key=external_reranker_api_key,
                        model=reranking_model,
                        timeout=timeout_value,
                    )
                except Exception as e:
                    log.error(f'ExternalReranking: {e}')
                    raise Exception(ERROR_MESSAGES.DEFAULT(e))
            else:
                import sentence_transformers
                import torch

                try:
                    rf = sentence_transformers.CrossEncoder(
                        get_model_path(reranking_model, auto_update),
                        device=DEVICE_TYPE,
                        trust_remote_code=RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
                        backend=SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND,
                        model_kwargs=SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS,
                        activation_fn=(
                            torch.nn.Sigmoid()
                            if SENTENCE_TRANSFORMERS_CROSS_ENCODER_SIGMOID_ACTIVATION_FUNCTION
                            else None
                        ),
                    )
                except Exception as e:
                    log.error(f'CrossEncoder: {e}')
                    raise Exception(ERROR_MESSAGES.DEFAULT('CrossEncoder error'))

                # Safely adjust pad_token_id if missing as some models do not have this in config
                try:
                    model_cfg = getattr(rf, 'model', None)
                    if model_cfg and hasattr(model_cfg, 'config'):
                        cfg = model_cfg.config
                        if getattr(cfg, 'pad_token_id', None) is None:
                            # Fallback to eos_token_id when available
                            eos = getattr(cfg, 'eos_token_id', None)
                            if eos is not None:
                                cfg.pad_token_id = eos
                                log.debug(f'Missing pad_token_id detected; set to eos_token_id={eos}')
                            else:
                                log.warning('Neither pad_token_id nor eos_token_id present in model config')
                except Exception as e2:
                    log.warning(f'Failed to adjust pad_token_id on CrossEncoder: {e2}')

    return rf


##########################################
#
# API routes
#
##########################################


router = APIRouter()


class CollectionNameForm(BaseModel):
    collection_name: Optional[str] = None


class ProcessUrlForm(CollectionNameForm):
    url: str


class SearchForm(BaseModel):
    queries: List[str]


@router.get('/embedding')
async def get_embedding_config(request: Request, user=Depends(get_admin_user)):
    return {
        'status': True,
        'RAG_EMBEDDING_ENGINE': request.app.state.config.RAG_EMBEDDING_ENGINE,
        'RAG_EMBEDDING_MODEL': request.app.state.config.RAG_EMBEDDING_MODEL,
        'RAG_EMBEDDING_BATCH_SIZE': request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
        'ENABLE_ASYNC_EMBEDDING': request.app.state.config.ENABLE_ASYNC_EMBEDDING,
        'RAG_EMBEDDING_CONCURRENT_REQUESTS': request.app.state.config.RAG_EMBEDDING_CONCURRENT_REQUESTS,
        'openai_config': {
            'url': request.app.state.config.RAG_OPENAI_API_BASE_URL,
            'key': request.app.state.config.RAG_OPENAI_API_KEY,
        },
        'ollama_config': {
            'url': request.app.state.config.RAG_OLLAMA_BASE_URL,
            'key': request.app.state.config.RAG_OLLAMA_API_KEY,
        },
        'azure_openai_config': {
            'url': request.app.state.config.RAG_AZURE_OPENAI_BASE_URL,
            'key': request.app.state.config.RAG_AZURE_OPENAI_API_KEY,
            'version': request.app.state.config.RAG_AZURE_OPENAI_API_VERSION,
        },
    }


class OpenAIConfigForm(BaseModel):
    url: str
    key: str


class OllamaConfigForm(BaseModel):
    url: str
    key: str


class AzureOpenAIConfigForm(BaseModel):
    url: str
    key: str
    version: str


class EmbeddingModelUpdateForm(BaseModel):
    openai_config: Optional[OpenAIConfigForm] = None
    ollama_config: Optional[OllamaConfigForm] = None
    azure_openai_config: Optional[AzureOpenAIConfigForm] = None
    RAG_EMBEDDING_ENGINE: str
    RAG_EMBEDDING_MODEL: str
    RAG_EMBEDDING_BATCH_SIZE: Optional[int] = 1
    ENABLE_ASYNC_EMBEDDING: Optional[bool] = True
    RAG_EMBEDDING_CONCURRENT_REQUESTS: Optional[int] = 0


def unload_embedding_model(request: Request):
    if request.app.state.config.RAG_EMBEDDING_ENGINE == '':
        # unloads current internal embedding model and clears VRAM cache
        request.app.state.ef = None
        request.app.state.EMBEDDING_FUNCTION = None
        import gc

        gc.collect()
        if DEVICE_TYPE == 'cuda':
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()


@router.post('/embedding/update')
async def update_embedding_config(request: Request, form_data: EmbeddingModelUpdateForm, user=Depends(get_admin_user)):
    log.info(
        f'Updating embedding model: {request.app.state.config.RAG_EMBEDDING_MODEL} to {form_data.RAG_EMBEDDING_MODEL}'
    )
    unload_embedding_model(request)
    try:
        request.app.state.config.RAG_EMBEDDING_ENGINE = form_data.RAG_EMBEDDING_ENGINE
        request.app.state.config.RAG_EMBEDDING_MODEL = form_data.RAG_EMBEDDING_MODEL.strip()
        request.app.state.config.RAG_EMBEDDING_BATCH_SIZE = form_data.RAG_EMBEDDING_BATCH_SIZE
        request.app.state.config.ENABLE_ASYNC_EMBEDDING = form_data.ENABLE_ASYNC_EMBEDDING
        request.app.state.config.RAG_EMBEDDING_CONCURRENT_REQUESTS = form_data.RAG_EMBEDDING_CONCURRENT_REQUESTS

        if request.app.state.config.RAG_EMBEDDING_ENGINE in [
            'ollama',
            'openai',
            'azure_openai',
        ]:
            if form_data.openai_config is not None:
                request.app.state.config.RAG_OPENAI_API_BASE_URL = form_data.openai_config.url
                request.app.state.config.RAG_OPENAI_API_KEY = form_data.openai_config.key

            if form_data.ollama_config is not None:
                request.app.state.config.RAG_OLLAMA_BASE_URL = form_data.ollama_config.url
                request.app.state.config.RAG_OLLAMA_API_KEY = form_data.ollama_config.key

            if form_data.azure_openai_config is not None:
                request.app.state.config.RAG_AZURE_OPENAI_BASE_URL = form_data.azure_openai_config.url
                request.app.state.config.RAG_AZURE_OPENAI_API_KEY = form_data.azure_openai_config.key
                request.app.state.config.RAG_AZURE_OPENAI_API_VERSION = form_data.azure_openai_config.version

        request.app.state.ef = get_ef(
            request.app.state.config.RAG_EMBEDDING_ENGINE,
            request.app.state.config.RAG_EMBEDDING_MODEL,
        )

        request.app.state.EMBEDDING_FUNCTION = get_embedding_function(
            request.app.state.config.RAG_EMBEDDING_ENGINE,
            request.app.state.config.RAG_EMBEDDING_MODEL,
            request.app.state.ef,
            (
                request.app.state.config.RAG_OPENAI_API_BASE_URL
                if request.app.state.config.RAG_EMBEDDING_ENGINE == 'openai'
                else (
                    request.app.state.config.RAG_OLLAMA_BASE_URL
                    if request.app.state.config.RAG_EMBEDDING_ENGINE == 'ollama'
                    else request.app.state.config.RAG_AZURE_OPENAI_BASE_URL
                )
            ),
            (
                request.app.state.config.RAG_OPENAI_API_KEY
                if request.app.state.config.RAG_EMBEDDING_ENGINE == 'openai'
                else (
                    request.app.state.config.RAG_OLLAMA_API_KEY
                    if request.app.state.config.RAG_EMBEDDING_ENGINE == 'ollama'
                    else request.app.state.config.RAG_AZURE_OPENAI_API_KEY
                )
            ),
            request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
            azure_api_version=(
                request.app.state.config.RAG_AZURE_OPENAI_API_VERSION
                if request.app.state.config.RAG_EMBEDDING_ENGINE == 'azure_openai'
                else None
            ),
            enable_async=request.app.state.config.ENABLE_ASYNC_EMBEDDING,
            concurrent_requests=request.app.state.config.RAG_EMBEDDING_CONCURRENT_REQUESTS,
        )

        return {
            'status': True,
            'RAG_EMBEDDING_ENGINE': request.app.state.config.RAG_EMBEDDING_ENGINE,
            'RAG_EMBEDDING_MODEL': request.app.state.config.RAG_EMBEDDING_MODEL,
            'RAG_EMBEDDING_BATCH_SIZE': request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
            'ENABLE_ASYNC_EMBEDDING': request.app.state.config.ENABLE_ASYNC_EMBEDDING,
            'RAG_EMBEDDING_CONCURRENT_REQUESTS': request.app.state.config.RAG_EMBEDDING_CONCURRENT_REQUESTS,
            'openai_config': {
                'url': request.app.state.config.RAG_OPENAI_API_BASE_URL,
                'key': request.app.state.config.RAG_OPENAI_API_KEY,
            },
            'ollama_config': {
                'url': request.app.state.config.RAG_OLLAMA_BASE_URL,
                'key': request.app.state.config.RAG_OLLAMA_API_KEY,
            },
            'azure_openai_config': {
                'url': request.app.state.config.RAG_AZURE_OPENAI_BASE_URL,
                'key': request.app.state.config.RAG_AZURE_OPENAI_API_KEY,
                'version': request.app.state.config.RAG_AZURE_OPENAI_API_VERSION,
            },
        }
    except Exception as e:
        log.exception(f'Problem updating embedding model: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.get('/config')
async def get_rag_config(request: Request, user=Depends(get_admin_user)):
    return {
        'status': True,
        # RAG settings
        'RAG_TEMPLATE': request.app.state.config.RAG_TEMPLATE,
        'TOP_K': request.app.state.config.TOP_K,
        'BYPASS_EMBEDDING_AND_RETRIEVAL': request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL,
        'RAG_FULL_CONTEXT': request.app.state.config.RAG_FULL_CONTEXT,
        # Hybrid search settings
        'ENABLE_RAG_HYBRID_SEARCH': request.app.state.config.ENABLE_RAG_HYBRID_SEARCH,
        'ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS': request.app.state.config.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS,
        'TOP_K_RERANKER': request.app.state.config.TOP_K_RERANKER,
        'RELEVANCE_THRESHOLD': request.app.state.config.RELEVANCE_THRESHOLD,
        'HYBRID_BM25_WEIGHT': request.app.state.config.HYBRID_BM25_WEIGHT,
        # Content extraction settings
        'CONTENT_EXTRACTION_ENGINE': request.app.state.config.CONTENT_EXTRACTION_ENGINE,
        'PDF_EXTRACT_IMAGES': request.app.state.config.PDF_EXTRACT_IMAGES,
        'PDF_LOADER_MODE': request.app.state.config.PDF_LOADER_MODE,
        'DATALAB_MARKER_API_KEY': request.app.state.config.DATALAB_MARKER_API_KEY,
        'DATALAB_MARKER_API_BASE_URL': request.app.state.config.DATALAB_MARKER_API_BASE_URL,
        'DATALAB_MARKER_ADDITIONAL_CONFIG': request.app.state.config.DATALAB_MARKER_ADDITIONAL_CONFIG,
        'DATALAB_MARKER_SKIP_CACHE': request.app.state.config.DATALAB_MARKER_SKIP_CACHE,
        'DATALAB_MARKER_FORCE_OCR': request.app.state.config.DATALAB_MARKER_FORCE_OCR,
        'DATALAB_MARKER_PAGINATE': request.app.state.config.DATALAB_MARKER_PAGINATE,
        'DATALAB_MARKER_STRIP_EXISTING_OCR': request.app.state.config.DATALAB_MARKER_STRIP_EXISTING_OCR,
        'DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION': request.app.state.config.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION,
        'DATALAB_MARKER_FORMAT_LINES': request.app.state.config.DATALAB_MARKER_FORMAT_LINES,
        'DATALAB_MARKER_USE_LLM': request.app.state.config.DATALAB_MARKER_USE_LLM,
        'DATALAB_MARKER_OUTPUT_FORMAT': request.app.state.config.DATALAB_MARKER_OUTPUT_FORMAT,
        'EXTERNAL_DOCUMENT_LOADER_URL': request.app.state.config.EXTERNAL_DOCUMENT_LOADER_URL,
        'EXTERNAL_DOCUMENT_LOADER_API_KEY': request.app.state.config.EXTERNAL_DOCUMENT_LOADER_API_KEY,
        'TIKA_SERVER_URL': request.app.state.config.TIKA_SERVER_URL,
        'DOCLING_SERVER_URL': request.app.state.config.DOCLING_SERVER_URL,
        'DOCLING_API_KEY': request.app.state.config.DOCLING_API_KEY,
        'DOCLING_PARAMS': request.app.state.config.DOCLING_PARAMS,
        'DOCUMENT_INTELLIGENCE_ENDPOINT': request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT,
        'DOCUMENT_INTELLIGENCE_KEY': request.app.state.config.DOCUMENT_INTELLIGENCE_KEY,
        'DOCUMENT_INTELLIGENCE_MODEL': request.app.state.config.DOCUMENT_INTELLIGENCE_MODEL,
        'MISTRAL_OCR_API_BASE_URL': request.app.state.config.MISTRAL_OCR_API_BASE_URL,
        'MISTRAL_OCR_API_KEY': request.app.state.config.MISTRAL_OCR_API_KEY,
        'PADDLEOCR_VL_BASE_URL': request.app.state.config.PADDLEOCR_VL_BASE_URL,
        'PADDLEOCR_VL_TOKEN': request.app.state.config.PADDLEOCR_VL_TOKEN,
        # MinerU settings
        'MINERU_API_MODE': request.app.state.config.MINERU_API_MODE,
        'MINERU_API_URL': request.app.state.config.MINERU_API_URL,
        'MINERU_API_KEY': request.app.state.config.MINERU_API_KEY,
        'MINERU_API_TIMEOUT': request.app.state.config.MINERU_API_TIMEOUT,
        'MINERU_PARAMS': request.app.state.config.MINERU_PARAMS,
        # Reranking settings
        'RAG_RERANKING_MODEL': request.app.state.config.RAG_RERANKING_MODEL,
        'RAG_RERANKING_ENGINE': request.app.state.config.RAG_RERANKING_ENGINE,
        'RAG_RERANKING_BATCH_SIZE': request.app.state.config.RAG_RERANKING_BATCH_SIZE,
        'RAG_EXTERNAL_RERANKER_URL': request.app.state.config.RAG_EXTERNAL_RERANKER_URL,
        'RAG_EXTERNAL_RERANKER_API_KEY': request.app.state.config.RAG_EXTERNAL_RERANKER_API_KEY,
        'RAG_EXTERNAL_RERANKER_TIMEOUT': request.app.state.config.RAG_EXTERNAL_RERANKER_TIMEOUT,
        # Chunking settings
        'TEXT_SPLITTER': request.app.state.config.TEXT_SPLITTER,
        'ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER': request.app.state.config.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER,
        'CHUNK_SIZE': request.app.state.config.CHUNK_SIZE,
        'CHUNK_MIN_SIZE_TARGET': request.app.state.config.CHUNK_MIN_SIZE_TARGET,
        'CHUNK_OVERLAP': request.app.state.config.CHUNK_OVERLAP,
        # Video/Audio chunking settings (local addition)
        'VIDEO_AUDIO_CHUNKING_STRATEGY': request.app.state.config.VIDEO_AUDIO_CHUNKING_STRATEGY,
        'VIDEO_AUDIO_CHUNK_TARGET_DURATION': request.app.state.config.VIDEO_AUDIO_CHUNK_TARGET_DURATION,
        'VIDEO_AUDIO_CHUNK_MAX_DURATION': request.app.state.config.VIDEO_AUDIO_CHUNK_MAX_DURATION,
        'VIDEO_AUDIO_CHUNK_OVERLAP_DURATION': request.app.state.config.VIDEO_AUDIO_CHUNK_OVERLAP_DURATION,
        # File upload settings
        'FILE_MAX_SIZE': request.app.state.config.FILE_MAX_SIZE,
        'FILE_MAX_COUNT': request.app.state.config.FILE_MAX_COUNT,
        'FILE_IMAGE_COMPRESSION_WIDTH': request.app.state.config.FILE_IMAGE_COMPRESSION_WIDTH,
        'FILE_IMAGE_COMPRESSION_HEIGHT': request.app.state.config.FILE_IMAGE_COMPRESSION_HEIGHT,
        'ALLOWED_FILE_EXTENSIONS': request.app.state.config.ALLOWED_FILE_EXTENSIONS,
        # Integration settings
        'ENABLE_GOOGLE_DRIVE_INTEGRATION': request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
        'ENABLE_ONEDRIVE_INTEGRATION': request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION,
        # Web search settings
        'web': {
            'ENABLE_WEB_SEARCH': request.app.state.config.ENABLE_WEB_SEARCH,
            'WEB_SEARCH_ENGINE': request.app.state.config.WEB_SEARCH_ENGINE,
            'WEB_SEARCH_TRUST_ENV': request.app.state.config.WEB_SEARCH_TRUST_ENV,
            'WEB_SEARCH_RESULT_COUNT': request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            'WEB_SEARCH_CONCURRENT_REQUESTS': request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS,
            'WEB_FETCH_MAX_CONTENT_LENGTH': request.app.state.config.WEB_FETCH_MAX_CONTENT_LENGTH,
            'WEB_LOADER_CONCURRENT_REQUESTS': request.app.state.config.WEB_LOADER_CONCURRENT_REQUESTS,
            'WEB_SEARCH_DOMAIN_FILTER_LIST': request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            'BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL': request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL,
            'BYPASS_WEB_SEARCH_WEB_LOADER': request.app.state.config.BYPASS_WEB_SEARCH_WEB_LOADER,
            'OLLAMA_CLOUD_WEB_SEARCH_API_KEY': request.app.state.config.OLLAMA_CLOUD_WEB_SEARCH_API_KEY,
            'SEARXNG_QUERY_URL': request.app.state.config.SEARXNG_QUERY_URL,
            'SEARXNG_LANGUAGE': request.app.state.config.SEARXNG_LANGUAGE,
            'YACY_QUERY_URL': request.app.state.config.YACY_QUERY_URL,
            'YACY_USERNAME': request.app.state.config.YACY_USERNAME,
            'YACY_PASSWORD': request.app.state.config.YACY_PASSWORD,
            'GOOGLE_PSE_API_KEY': request.app.state.config.GOOGLE_PSE_API_KEY,
            'GOOGLE_PSE_ENGINE_ID': request.app.state.config.GOOGLE_PSE_ENGINE_ID,
            'BRAVE_SEARCH_API_KEY': request.app.state.config.BRAVE_SEARCH_API_KEY,
            'BRAVE_SEARCH_CONTEXT_TOKENS': request.app.state.config.BRAVE_SEARCH_CONTEXT_TOKENS,
            'KAGI_SEARCH_API_KEY': request.app.state.config.KAGI_SEARCH_API_KEY,
            'MOJEEK_SEARCH_API_KEY': request.app.state.config.MOJEEK_SEARCH_API_KEY,
            'BOCHA_SEARCH_API_KEY': request.app.state.config.BOCHA_SEARCH_API_KEY,
            'SERPSTACK_API_KEY': request.app.state.config.SERPSTACK_API_KEY,
            'SERPSTACK_HTTPS': request.app.state.config.SERPSTACK_HTTPS,
            'SERPER_API_KEY': request.app.state.config.SERPER_API_KEY,
            'SERPLY_API_KEY': request.app.state.config.SERPLY_API_KEY,
            'DDGS_BACKEND': request.app.state.config.DDGS_BACKEND,
            'TAVILY_API_KEY': request.app.state.config.TAVILY_API_KEY,
            'SEARCHAPI_API_KEY': request.app.state.config.SEARCHAPI_API_KEY,
            'SEARCHAPI_ENGINE': request.app.state.config.SEARCHAPI_ENGINE,
            'SERPAPI_API_KEY': request.app.state.config.SERPAPI_API_KEY,
            'SERPAPI_ENGINE': request.app.state.config.SERPAPI_ENGINE,
            'JINA_API_KEY': request.app.state.config.JINA_API_KEY,
            'JINA_API_BASE_URL': request.app.state.config.JINA_API_BASE_URL,
            'BING_SEARCH_V7_ENDPOINT': request.app.state.config.BING_SEARCH_V7_ENDPOINT,
            'BING_SEARCH_V7_SUBSCRIPTION_KEY': request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
            'EXA_API_KEY': request.app.state.config.EXA_API_KEY,
            'PERPLEXITY_API_KEY': request.app.state.config.PERPLEXITY_API_KEY,
            'PERPLEXITY_MODEL': request.app.state.config.PERPLEXITY_MODEL,
            'PERPLEXITY_SEARCH_CONTEXT_USAGE': request.app.state.config.PERPLEXITY_SEARCH_CONTEXT_USAGE,
            'PERPLEXITY_SEARCH_API_URL': request.app.state.config.PERPLEXITY_SEARCH_API_URL,
            'SOUGOU_API_SID': request.app.state.config.SOUGOU_API_SID,
            'SOUGOU_API_SK': request.app.state.config.SOUGOU_API_SK,
            'WEB_LOADER_ENGINE': request.app.state.config.WEB_LOADER_ENGINE,
            'WEB_LOADER_TIMEOUT': request.app.state.config.WEB_LOADER_TIMEOUT,
            'ENABLE_WEB_LOADER_SSL_VERIFICATION': request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
            'PLAYWRIGHT_WS_URL': request.app.state.config.PLAYWRIGHT_WS_URL,
            'PLAYWRIGHT_TIMEOUT': request.app.state.config.PLAYWRIGHT_TIMEOUT,
            'FIRECRAWL_API_KEY': request.app.state.config.FIRECRAWL_API_KEY,
            'FIRECRAWL_API_BASE_URL': request.app.state.config.FIRECRAWL_API_BASE_URL,
            'FIRECRAWL_TIMEOUT': request.app.state.config.FIRECRAWL_TIMEOUT,
            'TAVILY_EXTRACT_DEPTH': request.app.state.config.TAVILY_EXTRACT_DEPTH,
            'EXTERNAL_WEB_SEARCH_URL': request.app.state.config.EXTERNAL_WEB_SEARCH_URL,
            'EXTERNAL_WEB_SEARCH_API_KEY': request.app.state.config.EXTERNAL_WEB_SEARCH_API_KEY,
            'EXTERNAL_WEB_LOADER_URL': request.app.state.config.EXTERNAL_WEB_LOADER_URL,
            'EXTERNAL_WEB_LOADER_API_KEY': request.app.state.config.EXTERNAL_WEB_LOADER_API_KEY,
            'YOUTUBE_LOADER_LANGUAGE': request.app.state.config.YOUTUBE_LOADER_LANGUAGE,
            'YOUTUBE_LOADER_PROXY_URL': request.app.state.config.YOUTUBE_LOADER_PROXY_URL,
            'YOUTUBE_LOADER_TRANSLATION': request.app.state.YOUTUBE_LOADER_TRANSLATION,
            'YANDEX_WEB_SEARCH_URL': request.app.state.config.YANDEX_WEB_SEARCH_URL,
            'YANDEX_WEB_SEARCH_API_KEY': request.app.state.config.YANDEX_WEB_SEARCH_API_KEY,
            'YANDEX_WEB_SEARCH_CONFIG': request.app.state.config.YANDEX_WEB_SEARCH_CONFIG,
            'YOUCOM_API_KEY': request.app.state.config.YOUCOM_API_KEY,
        },
    }


class WebConfig(BaseModel):
    ENABLE_WEB_SEARCH: Optional[bool] = None
    WEB_SEARCH_ENGINE: Optional[str] = None
    WEB_SEARCH_TRUST_ENV: Optional[bool] = None
    WEB_SEARCH_RESULT_COUNT: Optional[int] = None
    WEB_SEARCH_CONCURRENT_REQUESTS: Optional[int] = None
    WEB_SEARCH_DOMAIN_FILTER_LIST: Optional[List[str]] = []
    WEB_FETCH_MAX_CONTENT_LENGTH: Optional[int] = None
    WEB_LOADER_CONCURRENT_REQUESTS: Optional[int] = None
    BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL: Optional[bool] = None
    BYPASS_WEB_SEARCH_WEB_LOADER: Optional[bool] = None
    OLLAMA_CLOUD_WEB_SEARCH_API_KEY: Optional[str] = None
    SEARXNG_QUERY_URL: Optional[str] = None
    SEARXNG_LANGUAGE: Optional[str] = None
    YACY_QUERY_URL: Optional[str] = None
    YACY_USERNAME: Optional[str] = None
    YACY_PASSWORD: Optional[str] = None
    GOOGLE_PSE_API_KEY: Optional[str] = None
    GOOGLE_PSE_ENGINE_ID: Optional[str] = None
    BRAVE_SEARCH_API_KEY: Optional[str] = None
    BRAVE_SEARCH_CONTEXT_TOKENS: Optional[int] = None
    KAGI_SEARCH_API_KEY: Optional[str] = None
    MOJEEK_SEARCH_API_KEY: Optional[str] = None
    BOCHA_SEARCH_API_KEY: Optional[str] = None
    SERPSTACK_API_KEY: Optional[str] = None
    SERPSTACK_HTTPS: Optional[bool] = None
    SERPER_API_KEY: Optional[str] = None
    SERPLY_API_KEY: Optional[str] = None
    DDGS_BACKEND: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    SEARCHAPI_API_KEY: Optional[str] = None
    SEARCHAPI_ENGINE: Optional[str] = None
    SERPAPI_API_KEY: Optional[str] = None
    SERPAPI_ENGINE: Optional[str] = None
    JINA_API_KEY: Optional[str] = None
    JINA_API_BASE_URL: Optional[str] = None
    BING_SEARCH_V7_ENDPOINT: Optional[str] = None
    BING_SEARCH_V7_SUBSCRIPTION_KEY: Optional[str] = None
    EXA_API_KEY: Optional[str] = None
    PERPLEXITY_API_KEY: Optional[str] = None
    PERPLEXITY_MODEL: Optional[str] = None
    PERPLEXITY_SEARCH_CONTEXT_USAGE: Optional[str] = None
    PERPLEXITY_SEARCH_API_URL: Optional[str] = None
    SOUGOU_API_SID: Optional[str] = None
    SOUGOU_API_SK: Optional[str] = None
    WEB_LOADER_ENGINE: Optional[str] = None
    WEB_LOADER_TIMEOUT: Optional[str] = None
    ENABLE_WEB_LOADER_SSL_VERIFICATION: Optional[bool] = None
    PLAYWRIGHT_WS_URL: Optional[str] = None
    PLAYWRIGHT_TIMEOUT: Optional[int] = None
    FIRECRAWL_API_KEY: Optional[str] = None
    FIRECRAWL_API_BASE_URL: Optional[str] = None
    FIRECRAWL_TIMEOUT: Optional[str] = None
    TAVILY_EXTRACT_DEPTH: Optional[str] = None
    EXTERNAL_WEB_SEARCH_URL: Optional[str] = None
    EXTERNAL_WEB_SEARCH_API_KEY: Optional[str] = None
    EXTERNAL_WEB_LOADER_URL: Optional[str] = None
    EXTERNAL_WEB_LOADER_API_KEY: Optional[str] = None
    YOUTUBE_LOADER_LANGUAGE: Optional[List[str]] = None
    YOUTUBE_LOADER_PROXY_URL: Optional[str] = None
    YOUTUBE_LOADER_TRANSLATION: Optional[str] = None
    YANDEX_WEB_SEARCH_URL: Optional[str] = None
    YANDEX_WEB_SEARCH_API_KEY: Optional[str] = None
    YANDEX_WEB_SEARCH_CONFIG: Optional[str] = None
    YOUCOM_API_KEY: Optional[str] = None


class ConfigForm(BaseModel):
    # RAG settings
    RAG_TEMPLATE: Optional[str] = None
    TOP_K: Optional[int] = None
    BYPASS_EMBEDDING_AND_RETRIEVAL: Optional[bool] = None
    RAG_FULL_CONTEXT: Optional[bool] = None

    # Hybrid search settings
    ENABLE_RAG_HYBRID_SEARCH: Optional[bool] = None
    ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS: Optional[bool] = None
    TOP_K_RERANKER: Optional[int] = None
    RELEVANCE_THRESHOLD: Optional[float] = None
    HYBRID_BM25_WEIGHT: Optional[float] = None

    # Content extraction settings
    CONTENT_EXTRACTION_ENGINE: Optional[str] = None
    PDF_EXTRACT_IMAGES: Optional[bool] = None
    PDF_LOADER_MODE: Optional[str] = None

    DATALAB_MARKER_API_KEY: Optional[str] = None
    DATALAB_MARKER_API_BASE_URL: Optional[str] = None
    DATALAB_MARKER_ADDITIONAL_CONFIG: Optional[str] = None
    DATALAB_MARKER_SKIP_CACHE: Optional[bool] = None
    DATALAB_MARKER_FORCE_OCR: Optional[bool] = None
    DATALAB_MARKER_PAGINATE: Optional[bool] = None
    DATALAB_MARKER_STRIP_EXISTING_OCR: Optional[bool] = None
    DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION: Optional[bool] = None
    DATALAB_MARKER_FORMAT_LINES: Optional[bool] = None
    DATALAB_MARKER_USE_LLM: Optional[bool] = None
    DATALAB_MARKER_OUTPUT_FORMAT: Optional[str] = None

    EXTERNAL_DOCUMENT_LOADER_URL: Optional[str] = None
    EXTERNAL_DOCUMENT_LOADER_API_KEY: Optional[str] = None

    TIKA_SERVER_URL: Optional[str] = None
    DOCLING_SERVER_URL: Optional[str] = None
    DOCLING_API_KEY: Optional[str] = None
    DOCLING_PARAMS: Optional[dict] = None
    DOCUMENT_INTELLIGENCE_ENDPOINT: Optional[str] = None
    DOCUMENT_INTELLIGENCE_KEY: Optional[str] = None
    DOCUMENT_INTELLIGENCE_MODEL: Optional[str] = None
    MISTRAL_OCR_API_BASE_URL: Optional[str] = None
    MISTRAL_OCR_API_KEY: Optional[str] = None
    PADDLEOCR_VL_BASE_URL: Optional[str] = None
    PADDLEOCR_VL_TOKEN: Optional[str] = None

    # MinerU settings
    MINERU_API_MODE: Optional[str] = None
    MINERU_API_URL: Optional[str] = None
    MINERU_API_KEY: Optional[str] = None
    MINERU_API_TIMEOUT: Optional[str] = None
    MINERU_PARAMS: Optional[dict] = None

    # Reranking settings
    RAG_RERANKING_MODEL: Optional[str] = None
    RAG_RERANKING_ENGINE: Optional[str] = None
    RAG_RERANKING_BATCH_SIZE: Optional[int] = None
    RAG_EXTERNAL_RERANKER_URL: Optional[str] = None
    RAG_EXTERNAL_RERANKER_API_KEY: Optional[str] = None
    RAG_EXTERNAL_RERANKER_TIMEOUT: Optional[str] = None

    # Chunking settings
    TEXT_SPLITTER: Optional[str] = None
    ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER: Optional[bool] = None
    CHUNK_SIZE: Optional[int] = None
    CHUNK_MIN_SIZE_TARGET: Optional[int] = None
    CHUNK_OVERLAP: Optional[int] = None

    # Video/Audio chunking settings
    VIDEO_AUDIO_CHUNKING_STRATEGY: Optional[str] = None
    VIDEO_AUDIO_CHUNK_TARGET_DURATION: Optional[int] = None
    VIDEO_AUDIO_CHUNK_MAX_DURATION: Optional[int] = None
    VIDEO_AUDIO_CHUNK_OVERLAP_DURATION: Optional[int] = None

    # File upload settings
    FILE_MAX_SIZE: Optional[Union[int, str]] = None
    FILE_MAX_COUNT: Optional[Union[int, str]] = None
    FILE_IMAGE_COMPRESSION_WIDTH: Optional[Union[int, str]] = None
    FILE_IMAGE_COMPRESSION_HEIGHT: Optional[Union[int, str]] = None
    ALLOWED_FILE_EXTENSIONS: Optional[List[str]] = None

    # Integration settings
    ENABLE_GOOGLE_DRIVE_INTEGRATION: Optional[bool] = None
    ENABLE_ONEDRIVE_INTEGRATION: Optional[bool] = None

    # Web search settings
    web: Optional[WebConfig] = None


@router.post('/config/update')
async def update_rag_config(request: Request, form_data: ConfigForm, user=Depends(get_admin_user)):
    # RAG settings
    request.app.state.config.RAG_TEMPLATE = (
        form_data.RAG_TEMPLATE if form_data.RAG_TEMPLATE is not None else request.app.state.config.RAG_TEMPLATE
    )
    request.app.state.config.TOP_K = form_data.TOP_K if form_data.TOP_K is not None else request.app.state.config.TOP_K
    request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL = (
        form_data.BYPASS_EMBEDDING_AND_RETRIEVAL
        if form_data.BYPASS_EMBEDDING_AND_RETRIEVAL is not None
        else request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL
    )
    request.app.state.config.RAG_FULL_CONTEXT = (
        form_data.RAG_FULL_CONTEXT
        if form_data.RAG_FULL_CONTEXT is not None
        else request.app.state.config.RAG_FULL_CONTEXT
    )

    # Hybrid search settings
    request.app.state.config.ENABLE_RAG_HYBRID_SEARCH = (
        form_data.ENABLE_RAG_HYBRID_SEARCH
        if form_data.ENABLE_RAG_HYBRID_SEARCH is not None
        else request.app.state.config.ENABLE_RAG_HYBRID_SEARCH
    )
    request.app.state.config.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS = (
        form_data.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS
        if form_data.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS is not None
        else request.app.state.config.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS
    )

    request.app.state.config.TOP_K_RERANKER = (
        form_data.TOP_K_RERANKER if form_data.TOP_K_RERANKER is not None else request.app.state.config.TOP_K_RERANKER
    )
    request.app.state.config.RELEVANCE_THRESHOLD = (
        form_data.RELEVANCE_THRESHOLD
        if form_data.RELEVANCE_THRESHOLD is not None
        else request.app.state.config.RELEVANCE_THRESHOLD
    )
    request.app.state.config.HYBRID_BM25_WEIGHT = (
        form_data.HYBRID_BM25_WEIGHT
        if form_data.HYBRID_BM25_WEIGHT is not None
        else request.app.state.config.HYBRID_BM25_WEIGHT
    )

    # Content extraction settings
    request.app.state.config.CONTENT_EXTRACTION_ENGINE = (
        form_data.CONTENT_EXTRACTION_ENGINE
        if form_data.CONTENT_EXTRACTION_ENGINE is not None
        else request.app.state.config.CONTENT_EXTRACTION_ENGINE
    )
    request.app.state.config.PDF_EXTRACT_IMAGES = (
        form_data.PDF_EXTRACT_IMAGES
        if form_data.PDF_EXTRACT_IMAGES is not None
        else request.app.state.config.PDF_EXTRACT_IMAGES
    )
    request.app.state.config.PDF_LOADER_MODE = (
        form_data.PDF_LOADER_MODE if form_data.PDF_LOADER_MODE is not None else request.app.state.config.PDF_LOADER_MODE
    )
    request.app.state.config.DATALAB_MARKER_API_KEY = (
        form_data.DATALAB_MARKER_API_KEY
        if form_data.DATALAB_MARKER_API_KEY is not None
        else request.app.state.config.DATALAB_MARKER_API_KEY
    )
    request.app.state.config.DATALAB_MARKER_API_BASE_URL = (
        form_data.DATALAB_MARKER_API_BASE_URL
        if form_data.DATALAB_MARKER_API_BASE_URL is not None
        else request.app.state.config.DATALAB_MARKER_API_BASE_URL
    )
    request.app.state.config.DATALAB_MARKER_ADDITIONAL_CONFIG = (
        form_data.DATALAB_MARKER_ADDITIONAL_CONFIG
        if form_data.DATALAB_MARKER_ADDITIONAL_CONFIG is not None
        else request.app.state.config.DATALAB_MARKER_ADDITIONAL_CONFIG
    )
    request.app.state.config.DATALAB_MARKER_SKIP_CACHE = (
        form_data.DATALAB_MARKER_SKIP_CACHE
        if form_data.DATALAB_MARKER_SKIP_CACHE is not None
        else request.app.state.config.DATALAB_MARKER_SKIP_CACHE
    )
    request.app.state.config.DATALAB_MARKER_FORCE_OCR = (
        form_data.DATALAB_MARKER_FORCE_OCR
        if form_data.DATALAB_MARKER_FORCE_OCR is not None
        else request.app.state.config.DATALAB_MARKER_FORCE_OCR
    )
    request.app.state.config.DATALAB_MARKER_PAGINATE = (
        form_data.DATALAB_MARKER_PAGINATE
        if form_data.DATALAB_MARKER_PAGINATE is not None
        else request.app.state.config.DATALAB_MARKER_PAGINATE
    )
    request.app.state.config.DATALAB_MARKER_STRIP_EXISTING_OCR = (
        form_data.DATALAB_MARKER_STRIP_EXISTING_OCR
        if form_data.DATALAB_MARKER_STRIP_EXISTING_OCR is not None
        else request.app.state.config.DATALAB_MARKER_STRIP_EXISTING_OCR
    )
    request.app.state.config.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION = (
        form_data.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION
        if form_data.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION is not None
        else request.app.state.config.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION
    )
    request.app.state.config.DATALAB_MARKER_FORMAT_LINES = (
        form_data.DATALAB_MARKER_FORMAT_LINES
        if form_data.DATALAB_MARKER_FORMAT_LINES is not None
        else request.app.state.config.DATALAB_MARKER_FORMAT_LINES
    )
    request.app.state.config.DATALAB_MARKER_OUTPUT_FORMAT = (
        form_data.DATALAB_MARKER_OUTPUT_FORMAT
        if form_data.DATALAB_MARKER_OUTPUT_FORMAT is not None
        else request.app.state.config.DATALAB_MARKER_OUTPUT_FORMAT
    )
    request.app.state.config.DATALAB_MARKER_USE_LLM = (
        form_data.DATALAB_MARKER_USE_LLM
        if form_data.DATALAB_MARKER_USE_LLM is not None
        else request.app.state.config.DATALAB_MARKER_USE_LLM
    )
    request.app.state.config.EXTERNAL_DOCUMENT_LOADER_URL = (
        form_data.EXTERNAL_DOCUMENT_LOADER_URL
        if form_data.EXTERNAL_DOCUMENT_LOADER_URL is not None
        else request.app.state.config.EXTERNAL_DOCUMENT_LOADER_URL
    )
    request.app.state.config.EXTERNAL_DOCUMENT_LOADER_API_KEY = (
        form_data.EXTERNAL_DOCUMENT_LOADER_API_KEY
        if form_data.EXTERNAL_DOCUMENT_LOADER_API_KEY is not None
        else request.app.state.config.EXTERNAL_DOCUMENT_LOADER_API_KEY
    )
    request.app.state.config.TIKA_SERVER_URL = (
        form_data.TIKA_SERVER_URL if form_data.TIKA_SERVER_URL is not None else request.app.state.config.TIKA_SERVER_URL
    )
    request.app.state.config.DOCLING_SERVER_URL = (
        form_data.DOCLING_SERVER_URL
        if form_data.DOCLING_SERVER_URL is not None
        else request.app.state.config.DOCLING_SERVER_URL
    )
    request.app.state.config.DOCLING_API_KEY = (
        form_data.DOCLING_API_KEY if form_data.DOCLING_API_KEY is not None else request.app.state.config.DOCLING_API_KEY
    )
    request.app.state.config.DOCLING_PARAMS = (
        form_data.DOCLING_PARAMS if form_data.DOCLING_PARAMS is not None else request.app.state.config.DOCLING_PARAMS
    )
    request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT = (
        form_data.DOCUMENT_INTELLIGENCE_ENDPOINT
        if form_data.DOCUMENT_INTELLIGENCE_ENDPOINT is not None
        else request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT
    )
    request.app.state.config.DOCUMENT_INTELLIGENCE_KEY = (
        form_data.DOCUMENT_INTELLIGENCE_KEY
        if form_data.DOCUMENT_INTELLIGENCE_KEY is not None
        else request.app.state.config.DOCUMENT_INTELLIGENCE_KEY
    )
    request.app.state.config.DOCUMENT_INTELLIGENCE_MODEL = (
        form_data.DOCUMENT_INTELLIGENCE_MODEL
        if form_data.DOCUMENT_INTELLIGENCE_MODEL is not None
        else request.app.state.config.DOCUMENT_INTELLIGENCE_MODEL
    )

    request.app.state.config.MISTRAL_OCR_API_BASE_URL = (
        form_data.MISTRAL_OCR_API_BASE_URL
        if form_data.MISTRAL_OCR_API_BASE_URL is not None
        else request.app.state.config.MISTRAL_OCR_API_BASE_URL
    )
    request.app.state.config.MISTRAL_OCR_API_KEY = (
        form_data.MISTRAL_OCR_API_KEY
        if form_data.MISTRAL_OCR_API_KEY is not None
        else request.app.state.config.MISTRAL_OCR_API_KEY
    )
    request.app.state.config.PADDLEOCR_VL_BASE_URL = (
        form_data.PADDLEOCR_VL_BASE_URL
        if form_data.PADDLEOCR_VL_BASE_URL is not None
        else request.app.state.config.PADDLEOCR_VL_BASE_URL
    )
    request.app.state.config.PADDLEOCR_VL_TOKEN = (
        form_data.PADDLEOCR_VL_TOKEN
        if form_data.PADDLEOCR_VL_TOKEN is not None
        else request.app.state.config.PADDLEOCR_VL_TOKEN
    )

    # MinerU settings
    request.app.state.config.MINERU_API_MODE = (
        form_data.MINERU_API_MODE if form_data.MINERU_API_MODE is not None else request.app.state.config.MINERU_API_MODE
    )
    request.app.state.config.MINERU_API_URL = (
        form_data.MINERU_API_URL if form_data.MINERU_API_URL is not None else request.app.state.config.MINERU_API_URL
    )
    request.app.state.config.MINERU_API_KEY = (
        form_data.MINERU_API_KEY if form_data.MINERU_API_KEY is not None else request.app.state.config.MINERU_API_KEY
    )
    request.app.state.config.MINERU_API_TIMEOUT = (
        form_data.MINERU_API_TIMEOUT
        if form_data.MINERU_API_TIMEOUT is not None
        else request.app.state.config.MINERU_API_TIMEOUT
    )
    request.app.state.config.MINERU_PARAMS = (
        form_data.MINERU_PARAMS if form_data.MINERU_PARAMS is not None else request.app.state.config.MINERU_PARAMS
    )

    # Reranking settings
    if request.app.state.config.RAG_RERANKING_ENGINE == '':
        # Unloading the internal reranker and clear VRAM memory
        request.app.state.rf = None
        request.app.state.RERANKING_FUNCTION = None
        import gc

        gc.collect()
        if DEVICE_TYPE == 'cuda':
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    request.app.state.config.RAG_RERANKING_ENGINE = (
        form_data.RAG_RERANKING_ENGINE
        if form_data.RAG_RERANKING_ENGINE is not None
        else request.app.state.config.RAG_RERANKING_ENGINE
    )

    request.app.state.config.RAG_EXTERNAL_RERANKER_URL = (
        form_data.RAG_EXTERNAL_RERANKER_URL
        if form_data.RAG_EXTERNAL_RERANKER_URL is not None
        else request.app.state.config.RAG_EXTERNAL_RERANKER_URL
    )

    request.app.state.config.RAG_EXTERNAL_RERANKER_API_KEY = (
        form_data.RAG_EXTERNAL_RERANKER_API_KEY
        if form_data.RAG_EXTERNAL_RERANKER_API_KEY is not None
        else request.app.state.config.RAG_EXTERNAL_RERANKER_API_KEY
    )

    request.app.state.config.RAG_EXTERNAL_RERANKER_TIMEOUT = (
        form_data.RAG_EXTERNAL_RERANKER_TIMEOUT
        if form_data.RAG_EXTERNAL_RERANKER_TIMEOUT is not None
        else request.app.state.config.RAG_EXTERNAL_RERANKER_TIMEOUT
    )

    request.app.state.config.RAG_RERANKING_BATCH_SIZE = (
        form_data.RAG_RERANKING_BATCH_SIZE
        if form_data.RAG_RERANKING_BATCH_SIZE is not None
        else request.app.state.config.RAG_RERANKING_BATCH_SIZE
    )

    log.info(
        f'Updating reranking model: {request.app.state.config.RAG_RERANKING_MODEL} to {form_data.RAG_RERANKING_MODEL}'
    )
    try:
        request.app.state.config.RAG_RERANKING_MODEL = (
            form_data.RAG_RERANKING_MODEL
            if form_data.RAG_RERANKING_MODEL is not None
            else request.app.state.config.RAG_RERANKING_MODEL
        )

        try:
            if (
                request.app.state.config.ENABLE_RAG_HYBRID_SEARCH
                and not request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL
            ):
                request.app.state.rf = get_rf(
                    request.app.state.config.RAG_RERANKING_ENGINE,
                    request.app.state.config.RAG_RERANKING_MODEL,
                    request.app.state.config.RAG_EXTERNAL_RERANKER_URL,
                    request.app.state.config.RAG_EXTERNAL_RERANKER_API_KEY,
                    request.app.state.config.RAG_EXTERNAL_RERANKER_TIMEOUT,
                )

                request.app.state.RERANKING_FUNCTION = get_reranking_function(
                    request.app.state.config.RAG_RERANKING_ENGINE,
                    request.app.state.config.RAG_RERANKING_MODEL,
                    request.app.state.rf,
                    reranking_batch_size=request.app.state.config.RAG_RERANKING_BATCH_SIZE,
                )
        except Exception as e:
            log.error(f'Error loading reranking model: {e}')
            request.app.state.config.ENABLE_RAG_HYBRID_SEARCH = False
    except Exception as e:
        log.exception(f'Problem updating reranking model: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )

    # Chunking settings
    request.app.state.config.TEXT_SPLITTER = (
        form_data.TEXT_SPLITTER if form_data.TEXT_SPLITTER is not None else request.app.state.config.TEXT_SPLITTER
    )
    request.app.state.config.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER = (
        form_data.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER
        if form_data.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER is not None
        else request.app.state.config.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER
    )
    request.app.state.config.CHUNK_SIZE = (
        form_data.CHUNK_SIZE if form_data.CHUNK_SIZE is not None else request.app.state.config.CHUNK_SIZE
    )
    request.app.state.config.CHUNK_MIN_SIZE_TARGET = (
        form_data.CHUNK_MIN_SIZE_TARGET
        if form_data.CHUNK_MIN_SIZE_TARGET is not None
        else request.app.state.config.CHUNK_MIN_SIZE_TARGET
    )
    request.app.state.config.CHUNK_OVERLAP = (
        form_data.CHUNK_OVERLAP if form_data.CHUNK_OVERLAP is not None else request.app.state.config.CHUNK_OVERLAP
    )

    # Video/Audio chunking settings
    request.app.state.config.VIDEO_AUDIO_CHUNKING_STRATEGY = (
        form_data.VIDEO_AUDIO_CHUNKING_STRATEGY
        if form_data.VIDEO_AUDIO_CHUNKING_STRATEGY is not None
        else request.app.state.config.VIDEO_AUDIO_CHUNKING_STRATEGY
    )
    request.app.state.config.VIDEO_AUDIO_CHUNK_TARGET_DURATION = (
        form_data.VIDEO_AUDIO_CHUNK_TARGET_DURATION
        if form_data.VIDEO_AUDIO_CHUNK_TARGET_DURATION is not None
        else request.app.state.config.VIDEO_AUDIO_CHUNK_TARGET_DURATION
    )
    request.app.state.config.VIDEO_AUDIO_CHUNK_MAX_DURATION = (
        form_data.VIDEO_AUDIO_CHUNK_MAX_DURATION
        if form_data.VIDEO_AUDIO_CHUNK_MAX_DURATION is not None
        else request.app.state.config.VIDEO_AUDIO_CHUNK_MAX_DURATION
    )
    request.app.state.config.VIDEO_AUDIO_CHUNK_OVERLAP_DURATION = (
        form_data.VIDEO_AUDIO_CHUNK_OVERLAP_DURATION
        if form_data.VIDEO_AUDIO_CHUNK_OVERLAP_DURATION is not None
        else request.app.state.config.VIDEO_AUDIO_CHUNK_OVERLAP_DURATION
    )

    # File upload settings
    # Empty string means "clear to None" (unlimited/no compression),
    # None means "don't change", int means "set to this value"
    if form_data.FILE_MAX_SIZE is not None:
        request.app.state.config.FILE_MAX_SIZE = None if form_data.FILE_MAX_SIZE == '' else form_data.FILE_MAX_SIZE
    if form_data.FILE_MAX_COUNT is not None:
        request.app.state.config.FILE_MAX_COUNT = None if form_data.FILE_MAX_COUNT == '' else form_data.FILE_MAX_COUNT
    if form_data.FILE_IMAGE_COMPRESSION_WIDTH is not None:
        request.app.state.config.FILE_IMAGE_COMPRESSION_WIDTH = (
            None if form_data.FILE_IMAGE_COMPRESSION_WIDTH == '' else form_data.FILE_IMAGE_COMPRESSION_WIDTH
        )
    if form_data.FILE_IMAGE_COMPRESSION_HEIGHT is not None:
        request.app.state.config.FILE_IMAGE_COMPRESSION_HEIGHT = (
            None if form_data.FILE_IMAGE_COMPRESSION_HEIGHT == '' else form_data.FILE_IMAGE_COMPRESSION_HEIGHT
        )

    request.app.state.config.ALLOWED_FILE_EXTENSIONS = (
        form_data.ALLOWED_FILE_EXTENSIONS
        if form_data.ALLOWED_FILE_EXTENSIONS is not None
        else request.app.state.config.ALLOWED_FILE_EXTENSIONS
    )

    # Integration settings
    request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION = (
        form_data.ENABLE_GOOGLE_DRIVE_INTEGRATION
        if form_data.ENABLE_GOOGLE_DRIVE_INTEGRATION is not None
        else request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION
    )
    request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION = (
        form_data.ENABLE_ONEDRIVE_INTEGRATION
        if form_data.ENABLE_ONEDRIVE_INTEGRATION is not None
        else request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION
    )

    if form_data.web is not None:
        # Web search settings
        request.app.state.config.ENABLE_WEB_SEARCH = form_data.web.ENABLE_WEB_SEARCH
        request.app.state.config.WEB_SEARCH_ENGINE = form_data.web.WEB_SEARCH_ENGINE
        request.app.state.config.WEB_SEARCH_TRUST_ENV = form_data.web.WEB_SEARCH_TRUST_ENV
        request.app.state.config.WEB_SEARCH_RESULT_COUNT = form_data.web.WEB_SEARCH_RESULT_COUNT
        request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS = form_data.web.WEB_SEARCH_CONCURRENT_REQUESTS
        request.app.state.config.WEB_FETCH_MAX_CONTENT_LENGTH = form_data.web.WEB_FETCH_MAX_CONTENT_LENGTH
        request.app.state.config.WEB_LOADER_CONCURRENT_REQUESTS = form_data.web.WEB_LOADER_CONCURRENT_REQUESTS
        request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST = form_data.web.WEB_SEARCH_DOMAIN_FILTER_LIST
        request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL = (
            form_data.web.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
        )
        request.app.state.config.BYPASS_WEB_SEARCH_WEB_LOADER = form_data.web.BYPASS_WEB_SEARCH_WEB_LOADER
        request.app.state.config.OLLAMA_CLOUD_WEB_SEARCH_API_KEY = form_data.web.OLLAMA_CLOUD_WEB_SEARCH_API_KEY
        request.app.state.config.SEARXNG_QUERY_URL = form_data.web.SEARXNG_QUERY_URL
        request.app.state.config.SEARXNG_LANGUAGE = form_data.web.SEARXNG_LANGUAGE
        request.app.state.config.YACY_QUERY_URL = form_data.web.YACY_QUERY_URL
        request.app.state.config.YACY_USERNAME = form_data.web.YACY_USERNAME
        request.app.state.config.YACY_PASSWORD = form_data.web.YACY_PASSWORD
        request.app.state.config.GOOGLE_PSE_API_KEY = form_data.web.GOOGLE_PSE_API_KEY
        request.app.state.config.GOOGLE_PSE_ENGINE_ID = form_data.web.GOOGLE_PSE_ENGINE_ID
        request.app.state.config.BRAVE_SEARCH_API_KEY = form_data.web.BRAVE_SEARCH_API_KEY
        if form_data.web.BRAVE_SEARCH_CONTEXT_TOKENS is not None:
            request.app.state.config.BRAVE_SEARCH_CONTEXT_TOKENS = form_data.web.BRAVE_SEARCH_CONTEXT_TOKENS
        request.app.state.config.KAGI_SEARCH_API_KEY = form_data.web.KAGI_SEARCH_API_KEY
        request.app.state.config.MOJEEK_SEARCH_API_KEY = form_data.web.MOJEEK_SEARCH_API_KEY
        request.app.state.config.BOCHA_SEARCH_API_KEY = form_data.web.BOCHA_SEARCH_API_KEY
        request.app.state.config.SERPSTACK_API_KEY = form_data.web.SERPSTACK_API_KEY
        request.app.state.config.SERPSTACK_HTTPS = form_data.web.SERPSTACK_HTTPS
        request.app.state.config.SERPER_API_KEY = form_data.web.SERPER_API_KEY
        request.app.state.config.SERPLY_API_KEY = form_data.web.SERPLY_API_KEY
        request.app.state.config.DDGS_BACKEND = form_data.web.DDGS_BACKEND
        request.app.state.config.TAVILY_API_KEY = form_data.web.TAVILY_API_KEY
        request.app.state.config.SEARCHAPI_API_KEY = form_data.web.SEARCHAPI_API_KEY
        request.app.state.config.SEARCHAPI_ENGINE = form_data.web.SEARCHAPI_ENGINE
        request.app.state.config.SERPAPI_API_KEY = form_data.web.SERPAPI_API_KEY
        request.app.state.config.SERPAPI_ENGINE = form_data.web.SERPAPI_ENGINE
        request.app.state.config.JINA_API_KEY = form_data.web.JINA_API_KEY
        request.app.state.config.JINA_API_BASE_URL = form_data.web.JINA_API_BASE_URL
        request.app.state.config.BING_SEARCH_V7_ENDPOINT = form_data.web.BING_SEARCH_V7_ENDPOINT
        request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY = form_data.web.BING_SEARCH_V7_SUBSCRIPTION_KEY
        request.app.state.config.EXA_API_KEY = form_data.web.EXA_API_KEY
        request.app.state.config.PERPLEXITY_API_KEY = form_data.web.PERPLEXITY_API_KEY
        request.app.state.config.PERPLEXITY_MODEL = form_data.web.PERPLEXITY_MODEL
        request.app.state.config.PERPLEXITY_SEARCH_CONTEXT_USAGE = form_data.web.PERPLEXITY_SEARCH_CONTEXT_USAGE
        request.app.state.config.PERPLEXITY_SEARCH_API_URL = form_data.web.PERPLEXITY_SEARCH_API_URL
        request.app.state.config.SOUGOU_API_SID = form_data.web.SOUGOU_API_SID
        request.app.state.config.SOUGOU_API_SK = form_data.web.SOUGOU_API_SK

        # Web loader settings
        request.app.state.config.WEB_LOADER_ENGINE = form_data.web.WEB_LOADER_ENGINE
        request.app.state.config.WEB_LOADER_TIMEOUT = form_data.web.WEB_LOADER_TIMEOUT

        request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION = form_data.web.ENABLE_WEB_LOADER_SSL_VERIFICATION
        request.app.state.config.PLAYWRIGHT_WS_URL = form_data.web.PLAYWRIGHT_WS_URL
        request.app.state.config.PLAYWRIGHT_TIMEOUT = form_data.web.PLAYWRIGHT_TIMEOUT
        request.app.state.config.FIRECRAWL_API_KEY = form_data.web.FIRECRAWL_API_KEY
        request.app.state.config.FIRECRAWL_API_BASE_URL = form_data.web.FIRECRAWL_API_BASE_URL
        request.app.state.config.FIRECRAWL_TIMEOUT = form_data.web.FIRECRAWL_TIMEOUT
        request.app.state.config.EXTERNAL_WEB_SEARCH_URL = form_data.web.EXTERNAL_WEB_SEARCH_URL
        request.app.state.config.EXTERNAL_WEB_SEARCH_API_KEY = form_data.web.EXTERNAL_WEB_SEARCH_API_KEY
        request.app.state.config.EXTERNAL_WEB_LOADER_URL = form_data.web.EXTERNAL_WEB_LOADER_URL
        request.app.state.config.EXTERNAL_WEB_LOADER_API_KEY = form_data.web.EXTERNAL_WEB_LOADER_API_KEY
        request.app.state.config.TAVILY_EXTRACT_DEPTH = form_data.web.TAVILY_EXTRACT_DEPTH
        request.app.state.config.YOUTUBE_LOADER_LANGUAGE = form_data.web.YOUTUBE_LOADER_LANGUAGE
        request.app.state.config.YOUTUBE_LOADER_PROXY_URL = form_data.web.YOUTUBE_LOADER_PROXY_URL
        request.app.state.YOUTUBE_LOADER_TRANSLATION = form_data.web.YOUTUBE_LOADER_TRANSLATION
        request.app.state.config.YANDEX_WEB_SEARCH_URL = form_data.web.YANDEX_WEB_SEARCH_URL
        request.app.state.config.YANDEX_WEB_SEARCH_API_KEY = form_data.web.YANDEX_WEB_SEARCH_API_KEY
        request.app.state.config.YANDEX_WEB_SEARCH_CONFIG = form_data.web.YANDEX_WEB_SEARCH_CONFIG
        request.app.state.config.YOUCOM_API_KEY = form_data.web.YOUCOM_API_KEY

    return {
        'status': True,
        # RAG settings
        'RAG_TEMPLATE': request.app.state.config.RAG_TEMPLATE,
        'TOP_K': request.app.state.config.TOP_K,
        'BYPASS_EMBEDDING_AND_RETRIEVAL': request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL,
        'RAG_FULL_CONTEXT': request.app.state.config.RAG_FULL_CONTEXT,
        # Hybrid search settings
        'ENABLE_RAG_HYBRID_SEARCH': request.app.state.config.ENABLE_RAG_HYBRID_SEARCH,
        'TOP_K_RERANKER': request.app.state.config.TOP_K_RERANKER,
        'RELEVANCE_THRESHOLD': request.app.state.config.RELEVANCE_THRESHOLD,
        'HYBRID_BM25_WEIGHT': request.app.state.config.HYBRID_BM25_WEIGHT,
        # Content extraction settings
        'CONTENT_EXTRACTION_ENGINE': request.app.state.config.CONTENT_EXTRACTION_ENGINE,
        'PDF_EXTRACT_IMAGES': request.app.state.config.PDF_EXTRACT_IMAGES,
        'PDF_LOADER_MODE': request.app.state.config.PDF_LOADER_MODE,
        'DATALAB_MARKER_API_KEY': request.app.state.config.DATALAB_MARKER_API_KEY,
        'DATALAB_MARKER_API_BASE_URL': request.app.state.config.DATALAB_MARKER_API_BASE_URL,
        'DATALAB_MARKER_ADDITIONAL_CONFIG': request.app.state.config.DATALAB_MARKER_ADDITIONAL_CONFIG,
        'DATALAB_MARKER_SKIP_CACHE': request.app.state.config.DATALAB_MARKER_SKIP_CACHE,
        'DATALAB_MARKER_FORCE_OCR': request.app.state.config.DATALAB_MARKER_FORCE_OCR,
        'DATALAB_MARKER_PAGINATE': request.app.state.config.DATALAB_MARKER_PAGINATE,
        'DATALAB_MARKER_STRIP_EXISTING_OCR': request.app.state.config.DATALAB_MARKER_STRIP_EXISTING_OCR,
        'DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION': request.app.state.config.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION,
        'DATALAB_MARKER_USE_LLM': request.app.state.config.DATALAB_MARKER_USE_LLM,
        'DATALAB_MARKER_OUTPUT_FORMAT': request.app.state.config.DATALAB_MARKER_OUTPUT_FORMAT,
        'EXTERNAL_DOCUMENT_LOADER_URL': request.app.state.config.EXTERNAL_DOCUMENT_LOADER_URL,
        'EXTERNAL_DOCUMENT_LOADER_API_KEY': request.app.state.config.EXTERNAL_DOCUMENT_LOADER_API_KEY,
        'TIKA_SERVER_URL': request.app.state.config.TIKA_SERVER_URL,
        'DOCLING_SERVER_URL': request.app.state.config.DOCLING_SERVER_URL,
        'DOCLING_API_KEY': request.app.state.config.DOCLING_API_KEY,
        'DOCLING_PARAMS': request.app.state.config.DOCLING_PARAMS,
        'DOCUMENT_INTELLIGENCE_ENDPOINT': request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT,
        'DOCUMENT_INTELLIGENCE_KEY': request.app.state.config.DOCUMENT_INTELLIGENCE_KEY,
        'DOCUMENT_INTELLIGENCE_MODEL': request.app.state.config.DOCUMENT_INTELLIGENCE_MODEL,
        'MISTRAL_OCR_API_BASE_URL': request.app.state.config.MISTRAL_OCR_API_BASE_URL,
        'MISTRAL_OCR_API_KEY': request.app.state.config.MISTRAL_OCR_API_KEY,
        'PADDLEOCR_VL_BASE_URL': request.app.state.config.PADDLEOCR_VL_BASE_URL,
        'PADDLEOCR_VL_TOKEN': request.app.state.config.PADDLEOCR_VL_TOKEN,
        # MinerU settings
        'MINERU_API_MODE': request.app.state.config.MINERU_API_MODE,
        'MINERU_API_URL': request.app.state.config.MINERU_API_URL,
        'MINERU_API_KEY': request.app.state.config.MINERU_API_KEY,
        'MINERU_API_TIMEOUT': request.app.state.config.MINERU_API_TIMEOUT,
        'MINERU_PARAMS': request.app.state.config.MINERU_PARAMS,
        # Reranking settings
        'RAG_RERANKING_MODEL': request.app.state.config.RAG_RERANKING_MODEL,
        'RAG_RERANKING_ENGINE': request.app.state.config.RAG_RERANKING_ENGINE,
        'RAG_EXTERNAL_RERANKER_URL': request.app.state.config.RAG_EXTERNAL_RERANKER_URL,
        'RAG_EXTERNAL_RERANKER_API_KEY': request.app.state.config.RAG_EXTERNAL_RERANKER_API_KEY,
        'RAG_EXTERNAL_RERANKER_TIMEOUT': request.app.state.config.RAG_EXTERNAL_RERANKER_TIMEOUT,
        # Chunking settings
        'TEXT_SPLITTER': request.app.state.config.TEXT_SPLITTER,
        'CHUNK_SIZE': request.app.state.config.CHUNK_SIZE,
        'CHUNK_MIN_SIZE_TARGET': request.app.state.config.CHUNK_MIN_SIZE_TARGET,
        'ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER': request.app.state.config.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER,
        'CHUNK_OVERLAP': request.app.state.config.CHUNK_OVERLAP,
        # Video/Audio chunking settings (local addition)
        'VIDEO_AUDIO_CHUNKING_STRATEGY': request.app.state.config.VIDEO_AUDIO_CHUNKING_STRATEGY,
        'VIDEO_AUDIO_CHUNK_TARGET_DURATION': request.app.state.config.VIDEO_AUDIO_CHUNK_TARGET_DURATION,
        'VIDEO_AUDIO_CHUNK_MAX_DURATION': request.app.state.config.VIDEO_AUDIO_CHUNK_MAX_DURATION,
        'VIDEO_AUDIO_CHUNK_OVERLAP_DURATION': request.app.state.config.VIDEO_AUDIO_CHUNK_OVERLAP_DURATION,
        # File upload settings
        'FILE_MAX_SIZE': request.app.state.config.FILE_MAX_SIZE,
        'FILE_MAX_COUNT': request.app.state.config.FILE_MAX_COUNT,
        'FILE_IMAGE_COMPRESSION_WIDTH': request.app.state.config.FILE_IMAGE_COMPRESSION_WIDTH,
        'FILE_IMAGE_COMPRESSION_HEIGHT': request.app.state.config.FILE_IMAGE_COMPRESSION_HEIGHT,
        'ALLOWED_FILE_EXTENSIONS': request.app.state.config.ALLOWED_FILE_EXTENSIONS,
        # Integration settings
        'ENABLE_GOOGLE_DRIVE_INTEGRATION': request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
        'ENABLE_ONEDRIVE_INTEGRATION': request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION,
        # Web search settings
        'web': {
            'ENABLE_WEB_SEARCH': request.app.state.config.ENABLE_WEB_SEARCH,
            'WEB_SEARCH_ENGINE': request.app.state.config.WEB_SEARCH_ENGINE,
            'WEB_SEARCH_TRUST_ENV': request.app.state.config.WEB_SEARCH_TRUST_ENV,
            'WEB_SEARCH_RESULT_COUNT': request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            'WEB_SEARCH_CONCURRENT_REQUESTS': request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS,
            'WEB_FETCH_MAX_CONTENT_LENGTH': request.app.state.config.WEB_FETCH_MAX_CONTENT_LENGTH,
            'WEB_LOADER_CONCURRENT_REQUESTS': request.app.state.config.WEB_LOADER_CONCURRENT_REQUESTS,
            'WEB_SEARCH_DOMAIN_FILTER_LIST': request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            'BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL': request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL,
            'BYPASS_WEB_SEARCH_WEB_LOADER': request.app.state.config.BYPASS_WEB_SEARCH_WEB_LOADER,
            'OLLAMA_CLOUD_WEB_SEARCH_API_KEY': request.app.state.config.OLLAMA_CLOUD_WEB_SEARCH_API_KEY,
            'SEARXNG_QUERY_URL': request.app.state.config.SEARXNG_QUERY_URL,
            'SEARXNG_LANGUAGE': request.app.state.config.SEARXNG_LANGUAGE,
            'YACY_QUERY_URL': request.app.state.config.YACY_QUERY_URL,
            'YACY_USERNAME': request.app.state.config.YACY_USERNAME,
            'YACY_PASSWORD': request.app.state.config.YACY_PASSWORD,
            'GOOGLE_PSE_API_KEY': request.app.state.config.GOOGLE_PSE_API_KEY,
            'GOOGLE_PSE_ENGINE_ID': request.app.state.config.GOOGLE_PSE_ENGINE_ID,
            'BRAVE_SEARCH_API_KEY': request.app.state.config.BRAVE_SEARCH_API_KEY,
            'BRAVE_SEARCH_CONTEXT_TOKENS': request.app.state.config.BRAVE_SEARCH_CONTEXT_TOKENS,
            'KAGI_SEARCH_API_KEY': request.app.state.config.KAGI_SEARCH_API_KEY,
            'MOJEEK_SEARCH_API_KEY': request.app.state.config.MOJEEK_SEARCH_API_KEY,
            'BOCHA_SEARCH_API_KEY': request.app.state.config.BOCHA_SEARCH_API_KEY,
            'SERPSTACK_API_KEY': request.app.state.config.SERPSTACK_API_KEY,
            'SERPSTACK_HTTPS': request.app.state.config.SERPSTACK_HTTPS,
            'SERPER_API_KEY': request.app.state.config.SERPER_API_KEY,
            'SERPLY_API_KEY': request.app.state.config.SERPLY_API_KEY,
            'TAVILY_API_KEY': request.app.state.config.TAVILY_API_KEY,
            'SEARCHAPI_API_KEY': request.app.state.config.SEARCHAPI_API_KEY,
            'SEARCHAPI_ENGINE': request.app.state.config.SEARCHAPI_ENGINE,
            'SERPAPI_API_KEY': request.app.state.config.SERPAPI_API_KEY,
            'SERPAPI_ENGINE': request.app.state.config.SERPAPI_ENGINE,
            'JINA_API_KEY': request.app.state.config.JINA_API_KEY,
            'JINA_API_BASE_URL': request.app.state.config.JINA_API_BASE_URL,
            'BING_SEARCH_V7_ENDPOINT': request.app.state.config.BING_SEARCH_V7_ENDPOINT,
            'BING_SEARCH_V7_SUBSCRIPTION_KEY': request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
            'EXA_API_KEY': request.app.state.config.EXA_API_KEY,
            'PERPLEXITY_API_KEY': request.app.state.config.PERPLEXITY_API_KEY,
            'PERPLEXITY_MODEL': request.app.state.config.PERPLEXITY_MODEL,
            'PERPLEXITY_SEARCH_CONTEXT_USAGE': request.app.state.config.PERPLEXITY_SEARCH_CONTEXT_USAGE,
            'PERPLEXITY_SEARCH_API_URL': request.app.state.config.PERPLEXITY_SEARCH_API_URL,
            'SOUGOU_API_SID': request.app.state.config.SOUGOU_API_SID,
            'SOUGOU_API_SK': request.app.state.config.SOUGOU_API_SK,
            'WEB_LOADER_ENGINE': request.app.state.config.WEB_LOADER_ENGINE,
            'WEB_LOADER_TIMEOUT': request.app.state.config.WEB_LOADER_TIMEOUT,
            'ENABLE_WEB_LOADER_SSL_VERIFICATION': request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
            'PLAYWRIGHT_WS_URL': request.app.state.config.PLAYWRIGHT_WS_URL,
            'PLAYWRIGHT_TIMEOUT': request.app.state.config.PLAYWRIGHT_TIMEOUT,
            'FIRECRAWL_API_KEY': request.app.state.config.FIRECRAWL_API_KEY,
            'FIRECRAWL_API_BASE_URL': request.app.state.config.FIRECRAWL_API_BASE_URL,
            'FIRECRAWL_TIMEOUT': request.app.state.config.FIRECRAWL_TIMEOUT,
            'TAVILY_EXTRACT_DEPTH': request.app.state.config.TAVILY_EXTRACT_DEPTH,
            'EXTERNAL_WEB_SEARCH_URL': request.app.state.config.EXTERNAL_WEB_SEARCH_URL,
            'EXTERNAL_WEB_SEARCH_API_KEY': request.app.state.config.EXTERNAL_WEB_SEARCH_API_KEY,
            'EXTERNAL_WEB_LOADER_URL': request.app.state.config.EXTERNAL_WEB_LOADER_URL,
            'EXTERNAL_WEB_LOADER_API_KEY': request.app.state.config.EXTERNAL_WEB_LOADER_API_KEY,
            'YOUTUBE_LOADER_LANGUAGE': request.app.state.config.YOUTUBE_LOADER_LANGUAGE,
            'YOUTUBE_LOADER_PROXY_URL': request.app.state.config.YOUTUBE_LOADER_PROXY_URL,
            'YOUTUBE_LOADER_TRANSLATION': request.app.state.YOUTUBE_LOADER_TRANSLATION,
            'YANDEX_WEB_SEARCH_URL': request.app.state.config.YANDEX_WEB_SEARCH_URL,
            'YANDEX_WEB_SEARCH_API_KEY': request.app.state.config.YANDEX_WEB_SEARCH_API_KEY,
            'YANDEX_WEB_SEARCH_CONFIG': request.app.state.config.YANDEX_WEB_SEARCH_CONFIG,
            'YOUCOM_API_KEY': request.app.state.config.YOUCOM_API_KEY,
        },
    }


####################################
#
# Document process and retrieval
#
####################################


def can_merge_chunks(a: Document, b: Document) -> bool:
    if a.metadata.get('source') != b.metadata.get('source'):
        return False

    a_file_id = a.metadata.get('file_id')
    b_file_id = b.metadata.get('file_id')

    if a_file_id is not None and b_file_id is not None:
        return a_file_id == b_file_id

    return True


def merge_docs_to_target_size(
    request: Request,
    chunks: list[Document],
) -> list[Document]:
    """
    Best-effort normalization of chunk sizes.

    Attempts to grow small chunks up to a desired minimum size,
    without exceeding the maximum size or crossing source/file
    boundaries.
    """
    min_chunk_size_target = request.app.state.config.CHUNK_MIN_SIZE_TARGET
    max_chunk_size = request.app.state.config.CHUNK_SIZE

    if min_chunk_size_target <= 0:
        return chunks

    measure_chunk_size = len
    if request.app.state.config.TEXT_SPLITTER == 'token':
        encoding = tiktoken.get_encoding(str(request.app.state.config.TIKTOKEN_ENCODING_NAME))
        measure_chunk_size = lambda text: len(encoding.encode(text))

    processed_chunks: list[Document] = []

    current_chunk: Document | None = None
    current_content: str = ''

    for next_chunk in chunks:
        if current_chunk is None:
            current_chunk = next_chunk
            current_content = next_chunk.page_content
            continue  # First chunk initialization

        proposed_content = f'{current_content}\n\n{next_chunk.page_content}'

        can_merge = (
            can_merge_chunks(current_chunk, next_chunk)
            and measure_chunk_size(current_content) < min_chunk_size_target
            and measure_chunk_size(proposed_content) <= max_chunk_size
        )

        if can_merge:
            current_content = proposed_content
        else:
            processed_chunks.append(
                Document(
                    page_content=current_content,
                    metadata={**current_chunk.metadata},
                )
            )
            current_chunk = next_chunk
            current_content = next_chunk.page_content

    if current_chunk is not None:
        processed_chunks.append(
            Document(
                page_content=current_content,
                metadata={**current_chunk.metadata},
            )
        )

    return processed_chunks


def save_docs_to_vector_db(
    request: Request,
    docs,
    collection_name,
    metadata: Optional[dict] = None,
    overwrite: bool = True,  # Default to True for smooth UX (auto-replace like file systems)
    split: bool = True,
    add: bool = False,
    user=None,
) -> bool:
    def _get_docs_info(docs: list[Document]) -> str:
        docs_info = set()

        # Trying to select relevant metadata identifying the document.
        for doc in docs:
            metadata = getattr(doc, 'metadata', {})
            doc_name = metadata.get('name', '')
            if not doc_name:
                doc_name = metadata.get('title', '')
            if not doc_name:
                doc_name = metadata.get('source', '')
            if doc_name:
                docs_info.add(doc_name)

        return ', '.join(docs_info)

    log.debug(f'save_docs_to_vector_db: document {_get_docs_info(docs)} {collection_name}')

    # Get namespace for Pinecone isolation (None for other DBs)
    namespace = get_namespace_for_collection(collection_name)

    # Check if entries with the same hash (metadata.hash) already exist
    if metadata and 'hash' in metadata:
        result = VECTOR_DB_CLIENT.query(
            collection_name=collection_name,
            filter={'hash': metadata['hash']},
            namespace=namespace,
        )

        if result is not None and result.ids and len(result.ids) > 0:
            existing_doc_ids = result.ids[0]
            if existing_doc_ids:
                filename = metadata.get("name", "Unknown file")
                log.info(
                    f"Document '{filename}' with hash {metadata['hash']} already exists in collection {collection_name}"
                )

                # Check if the existing document belongs to the same file
                # If same file_id, this is a re-add/reindex - allow it
                # If different file_id, this is a duplicate - block it
                existing_file_id = None
                if result.metadatas and result.metadatas[0]:
                    existing_file_id = result.metadatas[0][0].get('file_id')

                if existing_file_id != metadata.get('file_id'):
                    # If overwrite is True, delete existing documents first
                    if overwrite:
                        log.info(f"Replacing existing version of '{filename}' ({len(existing_doc_ids)} vectors)")
                        try:
                            VECTOR_DB_CLIENT.delete(
                                collection_name=collection_name,
                                ids=existing_doc_ids,
                                namespace=namespace,
                            )
                            log.info(f"Deleted {len(existing_doc_ids)} existing vectors for '{filename}'")
                        except Exception as e:
                            log.warning(f"Failed to delete existing documents: {e}")
                            # Continue processing instead of failing
                    else:
                        log.info(f'Document with hash {metadata["hash"]} already exists')
                        raise ValueError(ERROR_MESSAGES.DUPLICATE_CONTENT)

    if split:
        if request.app.state.config.TEXT_SPLITTER in ['unstructured']:
            # Unstructured.io handles chunking internally, no additional splitting needed
            log.info('Using Unstructured.io semantic chunking (handled internally)')
            # docs are already chunked by UnstructuredUnifiedLoader
        elif request.app.state.config.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER:
            log.info('Using markdown header text splitter')
            # Define headers to split on - covering most common markdown header levels
            markdown_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=[
                    ('#', 'Header 1'),
                    ('##', 'Header 2'),
                    ('###', 'Header 3'),
                    ('####', 'Header 4'),
                    ('#####', 'Header 5'),
                    ('######', 'Header 6'),
                ],
                strip_headers=False,  # Keep headers in content for context
            )

            split_docs = []
            for doc in docs:
                split_docs.extend(
                    [
                        Document(
                            page_content=split_chunk.page_content,
                            metadata={**doc.metadata},
                        )
                        for split_chunk in markdown_splitter.split_text(doc.page_content)
                    ]
                )

            docs = split_docs
            if request.app.state.config.CHUNK_MIN_SIZE_TARGET > 0:
                docs = merge_docs_to_target_size(request, docs)

        if request.app.state.config.TEXT_SPLITTER in ['', 'character']:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=request.app.state.config.CHUNK_SIZE,
                chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                add_start_index=True,
            )
            docs = text_splitter.split_documents(docs)
        elif request.app.state.config.TEXT_SPLITTER == 'token':
            log.info(f'Using token text splitter: {request.app.state.config.TIKTOKEN_ENCODING_NAME}')

            tiktoken.get_encoding(str(request.app.state.config.TIKTOKEN_ENCODING_NAME))
            text_splitter = TokenTextSplitter(
                encoding_name=str(request.app.state.config.TIKTOKEN_ENCODING_NAME),
                chunk_size=request.app.state.config.CHUNK_SIZE,
                chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                add_start_index=True,
            )
            docs = text_splitter.split_documents(docs)
        else:
            raise ValueError(ERROR_MESSAGES.DEFAULT('Invalid text splitter'))

    # Filter out empty documents and validate content
    docs = [doc for doc in docs if doc.page_content and doc.page_content.strip()]

    if len(docs) == 0:
        log.warning(f"No valid content found in documents for collection {collection_name}")
        raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

    texts = [sanitize_text_for_db(doc.page_content) for doc in docs]

    # Additional validation: ensure texts are not just whitespace
    texts = [text.strip() for text in texts if text.strip()]

    if len(texts) == 0:
        log.warning(f"No valid text content found after filtering for collection {collection_name}")
        raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

    # Optimize metadata for better performance and lower storage costs
    def optimize_metadata(doc_metadata, additional_metadata):
        """Optimize metadata by removing large/unnecessary fields and consolidating data"""
        optimized = {}

        # Copy essential fields
        essential_fields = [
            "file_id",
            "filename",
            "filetype",
            "hash",
            "created_by",
            "chunk_index",
            "total_chunks",
            "page_number",
            "processing_engine",
            "strategy",
            "chunking_strategy",
            "cleaning_level",
            "element_type",
            "source",
            "languages",
            "last_modified",
            # High-Impact Enrichment Fields
            "chunk_summary",
            "chunk_title",
            "potential_questions",
            # Enhanced Entity Extraction
            "topics",
            "entities_people",
            "entities_organizations",
            "entities_locations",
            "keywords",
            # Audio/Video Timestamp Fields
            "timestamp_start",
            "timestamp_end",
            "duration",
            "audio_segment_url",
            "video_segment_url",
            "transcript_language",
            "transcript_duration",
        ]

        for field in essential_fields:
            if field in doc_metadata and doc_metadata[field] is not None:
                optimized[field] = doc_metadata[field]

        # Add additional metadata (filtering out None values)
        if additional_metadata:
            for key, value in additional_metadata.items():
                if value is not None:
                    optimized[key] = value

        # Add compact embedding config (single string instead of object)
        optimized["embedding"] = (
            f"{request.app.state.config.RAG_EMBEDDING_ENGINE}:{request.app.state.config.RAG_EMBEDDING_MODEL}"
        )

        # Validate metadata size (Pinecone has limits)
        metadata_size = len(str(optimized))
        if metadata_size > 40000:  # Pinecone limit is ~40KB
            log.warning(f"Metadata size ({metadata_size} bytes) is close to Pinecone limit")

        return optimized

    metadatas = [
        optimize_metadata(
            doc.metadata,
            {
                **(metadata if metadata else {}),
                'embedding_config': {
                    'engine': request.app.state.config.RAG_EMBEDDING_ENGINE,
                    'model': request.app.state.config.RAG_EMBEDDING_MODEL,
                },
            },
        )
        for doc in docs
    ]

    try:
        # Get namespace for Pinecone isolation (None for other DBs)
        namespace = get_namespace_for_collection(collection_name)

        if VECTOR_DB_CLIENT.has_collection(collection_name=collection_name, namespace=namespace):
            log.info(
                f'collection {collection_name} already exists' + (f" in namespace '{namespace}'" if namespace else '')
            )

            if overwrite:
                VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name, namespace=namespace)
                log.info(
                    f'deleting existing collection {collection_name}'
                    + (f" from namespace '{namespace}'" if namespace else '')
                )
            elif add is False:
                log.info(f'collection {collection_name} already exists, overwrite is False and add is False')
                return True

        log.info(f'generating embeddings for {collection_name}')
        embedding_function = get_embedding_function(
            request.app.state.config.RAG_EMBEDDING_ENGINE,
            request.app.state.config.RAG_EMBEDDING_MODEL,
            request.app.state.ef,
            (
                request.app.state.config.RAG_OPENAI_API_BASE_URL
                if request.app.state.config.RAG_EMBEDDING_ENGINE == 'openai'
                else (
                    request.app.state.config.RAG_OLLAMA_BASE_URL
                    if request.app.state.config.RAG_EMBEDDING_ENGINE == 'ollama'
                    else request.app.state.config.RAG_AZURE_OPENAI_BASE_URL
                )
            ),
            (
                request.app.state.config.RAG_OPENAI_API_KEY
                if request.app.state.config.RAG_EMBEDDING_ENGINE == 'openai'
                else (
                    request.app.state.config.RAG_OLLAMA_API_KEY
                    if request.app.state.config.RAG_EMBEDDING_ENGINE == 'ollama'
                    else request.app.state.config.RAG_AZURE_OPENAI_API_KEY
                )
            ),
            request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
            azure_api_version=(
                request.app.state.config.RAG_AZURE_OPENAI_API_VERSION
                if request.app.state.config.RAG_EMBEDDING_ENGINE == 'azure_openai'
                else None
            ),
            enable_async=request.app.state.config.ENABLE_ASYNC_EMBEDDING,
            concurrent_requests=request.app.state.config.RAG_EMBEDDING_CONCURRENT_REQUESTS,
        )

        # Run async embedding in sync context using the main event loop
        # This allows the main loop to stay responsive to health checks during long operations
        embedding_timeout = RAG_EMBEDDING_TIMEOUT

        future = asyncio.run_coroutine_threadsafe(
            embedding_function(
                list(map(lambda x: x.replace('\n', ' '), texts)),
                prefix=RAG_EMBEDDING_CONTENT_PREFIX,
                user=user,
            ),
            request.app.state.main_loop,
        )
        embeddings = future.result(timeout=embedding_timeout)

        if embeddings is None:
            log.error('Embedding generation failed')
            return False

        # Filter out None embeddings and corresponding texts/metadatas (defensive)
        valid_embeddings = []
        valid_texts = []
        valid_metadatas = []

        for i, embedding in enumerate(embeddings):
            if embedding is not None:
                valid_embeddings.append(embedding)
                valid_texts.append(texts[i])
                valid_metadatas.append(metadatas[i])

        if len(valid_embeddings) == 0:
            log.error('No valid embeddings generated')
            return False

        embeddings = valid_embeddings
        texts = valid_texts
        metadatas = valid_metadatas

        log.info(f'embeddings generated {len(embeddings)} for {len(texts)} items')

        items = [
            {
                'id': str(uuid.uuid4()),
                'text': text,
                'vector': embeddings[idx],
                'metadata': metadatas[idx],
            }
            for idx, text in enumerate(texts)
        ]

        log.info(f'Adding {len(items)} items to collection {collection_name}')
        if items and 'file_id' in metadatas[0]:
            log.info(f'File ID in metadata: {metadatas[0].get("file_id")}')
            log.info(f'File name in metadata: {metadatas[0].get("name", "Unknown")}')

        # Process in batches for better performance (especially for large documents)
        batch_size = 100  # Optimal batch size for most vector databases
        total_added = 0

        # Get namespace for Pinecone isolation (None for other DBs)
        namespace = get_namespace_for_collection(collection_name)

        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            VECTOR_DB_CLIENT.insert(
                collection_name=collection_name,
                items=batch,
                namespace=namespace,
            )
            total_added += len(batch)
            log.debug(f'Added batch {i // batch_size + 1}: {len(batch)} items')

        log.info(f'added {total_added} items to collection {collection_name}')
        return True
    except Exception as e:
        log.exception(e)
        raise e


class ProcessFileForm(BaseModel):
    file_id: str
    content: Optional[str] = None
    collection_name: Optional[str] = None


@router.post('/process/file')
async def process_file(
    request: Request,
    form_data: ProcessFileForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Process a file and save its content to the vector database.
    Process a file and save its content to the vector database.
    Note: granular session management is used to prevent connection pool exhaustion.
    The session is committed before external API calls, and updates use a fresh session.
    """
    log.info(
        f'Processing file: file_id={form_data.file_id}, has_content={bool(form_data.content)}, collection_name={form_data.collection_name}'
    )

    if user.role == 'admin':
        file = await Files.get_file_by_id(form_data.file_id, db=db)
    else:
        file = await Files.get_file_by_id_and_user_id(form_data.file_id, user.id, db=db)

    if file:
        try:
            collection_name = form_data.collection_name

            if collection_name is None:
                collection_name = f'file-{file.id}'
            else:
                await _validate_collection_access([collection_name], user, access_type='write')

            # CRITICAL: Ensure file.id is unique and correct
            if not file.id or len(file.id) < 10:
                log.error(f"Invalid file ID: {file.id} for file {file.filename}")
                raise ValueError(f"Invalid file ID: {file.id}")

            log.info(f"File {file.id} ({file.filename}) will be saved to collection: {collection_name}")

            # Double-check that we're not accidentally using the wrong collection
            if form_data.content and not form_data.collection_name:
                expected_collection = f"file-{file.id}"
                if collection_name != expected_collection:
                    log.error(f"Collection name mismatch! Expected: {expected_collection}, Got: {collection_name}")
                    raise ValueError(f"Collection name mismatch for file {file.id}")

            # When adding to knowledge base, reuse existing file-{id} vectors (same as text files)
            # Only process content if: (1) content exists AND (2) NOT adding to knowledge base
            if form_data.content and not form_data.collection_name:
                # Update the content in the file
                # Usage: /files/{file_id}/data/content/update, /files/ (audio file upload pipeline)
                # Note: Audio/video transcripts come through this path and need chunking
                # Unlike file-based processing, transcripts don't go through Loader/Unstructured

                # Only delete existing collection if it exists (for updates)
                # For new uploads, the collection won't exist yet
                file_collection = f'file-{file.id}'
                file_namespace = get_namespace_for_collection(file_collection)

                if VECTOR_DB_CLIENT.has_collection(collection_name=file_collection, namespace=file_namespace):
                    try:
                        # This is an update operation - delete the old collection
                        log.info(f"Updating existing collection for file {file.id}")
                        VECTOR_DB_CLIENT.delete_collection(
                            collection_name=file_collection,
                            namespace=file_namespace,
                        )
                    except Exception as e:
                        log.warning(f"Failed to delete existing collection for file {file.id}: {e}")
                        # Continue processing even if deletion fails

                # Create single document with full transcript
                full_transcript = form_data.content.replace("<br/>", "\n")
                # Filter out potentially contaminated file-specific URLs from metadata
                filtered_meta = {
                    k: v for k, v in file.meta.items() if k not in ["video_segment_url", "audio_segment_url"]
                }
                docs = [
                    Document(
                        page_content=full_transcript,
                        metadata={
                            **filtered_meta,
                            'name': file.filename,
                            'created_by': file.user_id,
                            'file_id': file.id,
                            'source': file.filename,
                        },
                    )
                ]

                # Get transcript segments from file metadata (if available)
                transcript_segments = file.meta.get("transcript_segments", [])
                transcript_duration = file.meta.get("transcript_duration")
                transcript_language = file.meta.get("transcript_language")

                # Determine chunking strategy for video/audio transcripts
                video_chunking_strategy = get_config_value(
                    request, "VIDEO_AUDIO_CHUNKING_STRATEGY", VIDEO_AUDIO_CHUNKING_STRATEGY
                )

                # Use semantic chunking if enabled AND segments are available
                use_semantic_chunking = (
                    video_chunking_strategy == "semantic" and transcript_segments and len(transcript_segments) > 0
                )

                # Check if source is video or audio (used by both paths)
                is_video = file.meta.get("content_type", "").startswith("video/")

                # Base metadata for all chunks
                base_metadata = {
                    **filtered_meta,
                    "name": file.filename,
                    "created_by": file.user_id,
                    "file_id": file.id,
                    "source": file.filename,
                }

                if use_semantic_chunking:
                    # ============================================================
                    # SEMANTIC CHUNKING: Uses Whisper segments with natural boundaries
                    # Benefits: Preserves sentences, respects pauses, accurate timestamps
                    # ============================================================
                    log.info(
                        f"Using semantic chunking for audio/video transcript with {len(transcript_segments)} segments"
                    )

                    # Get chunking parameters from config using shared utility
                    target_duration = float(
                        get_config_value(
                            request, "VIDEO_AUDIO_CHUNK_TARGET_DURATION", VIDEO_AUDIO_CHUNK_TARGET_DURATION
                        )
                    )
                    max_duration = float(
                        get_config_value(request, "VIDEO_AUDIO_CHUNK_MAX_DURATION", VIDEO_AUDIO_CHUNK_MAX_DURATION)
                    )
                    overlap_duration = float(
                        get_config_value(
                            request, "VIDEO_AUDIO_CHUNK_OVERLAP_DURATION", VIDEO_AUDIO_CHUNK_OVERLAP_DURATION
                        )
                    )

                    # Create semantic chunks from Whisper segments
                    semantic_chunks = create_semantic_chunks_from_segments(
                        segments=transcript_segments,
                        target_duration=target_duration,
                        max_duration=max_duration,
                        overlap_duration=overlap_duration,
                    )

                    # Convert semantic chunks to enriched documents
                    enriched_docs = []
                    for chunk in semantic_chunks:
                        enrichment = extract_enhanced_metadata(chunk["text"])
                        media_urls = build_media_segment_urls(file.id, chunk["start"], chunk["end"], is_video)

                        enriched_metadata = build_enriched_chunk_metadata(
                            base_metadata=base_metadata,
                            enrichment=enrichment,
                            chunk_index=chunk["chunk_index"],
                            total_chunks=chunk["total_chunks"],
                            timestamp_start=chunk["start"],
                            timestamp_end=chunk["end"],
                            duration=chunk["duration"],
                            chunking_strategy="semantic",
                            has_overlap=bool(chunk.get("overlap_text")),
                            transcript_language=transcript_language,
                            transcript_duration=transcript_duration,
                            media_urls=media_urls,
                        )

                        enriched_docs.append(Document(page_content=chunk["text"], metadata=enriched_metadata))

                    docs = enriched_docs
                    log.info(
                        f"Created {len(docs)} semantic chunks with direct timestamps "
                        f"(target: {target_duration}s, max: {max_duration}s, overlap: {overlap_duration}s)"
                    )

                else:
                    # ============================================================
                    # LEGACY CHARACTER-BASED CHUNKING: Fallback when no segments
                    # Used when: segments not available OR strategy set to "character"
                    # ============================================================
                    log.info(
                        f"Using character-based chunking for audio/video transcript "
                        f"(strategy: {video_chunking_strategy}, segments available: {len(transcript_segments) if transcript_segments else 0})"
                    )

                    text_splitter_config = request.app.state.config.TEXT_SPLITTER

                    if text_splitter_config in ["", "unstructured", "character"]:
                        text_splitter = RecursiveCharacterTextSplitter(
                            chunk_size=request.app.state.config.CHUNK_SIZE,
                            chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                            add_start_index=True,
                        )
                        docs = text_splitter.split_documents(docs)
                        log.info(f"Split audio/video transcript into {len(docs)} chunks (character)")
                    elif text_splitter_config == "token":
                        tiktoken.get_encoding(str(request.app.state.config.TIKTOKEN_ENCODING_NAME))
                        text_splitter = TokenTextSplitter(
                            encoding_name=str(request.app.state.config.TIKTOKEN_ENCODING_NAME),
                            chunk_size=request.app.state.config.CHUNK_SIZE,
                            chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                            add_start_index=True,
                        )
                        docs = text_splitter.split_documents(docs)
                        log.info(f"Split audio/video transcript into {len(docs)} chunks (token)")
                    elif text_splitter_config == "markdown_header":
                        headers_to_split_on = [("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]
                        markdown_splitter = MarkdownHeaderTextSplitter(
                            headers_to_split_on=headers_to_split_on,
                            strip_headers=False,
                        )
                        md_splits = markdown_splitter.split_text(docs[0].page_content)
                        text_splitter = RecursiveCharacterTextSplitter(
                            chunk_size=request.app.state.config.CHUNK_SIZE,
                            chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                            add_start_index=True,
                        )
                        docs = text_splitter.split_documents(md_splits)
                        log.info(f"Split audio/video transcript into {len(docs)} chunks (markdown)")
                    else:
                        log.warning(f"Unknown TEXT_SPLITTER '{text_splitter_config}', using character splitter")
                        text_splitter = RecursiveCharacterTextSplitter(
                            chunk_size=request.app.state.config.CHUNK_SIZE,
                            chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                            add_start_index=True,
                        )
                        docs = text_splitter.split_documents(docs)

                    # Enrich each chunk with timestamps and topics/entities
                    enriched_docs = []
                    total_docs = len(docs)

                    for idx, doc in enumerate(docs):
                        chunk_start_char = doc.metadata.get("start_index", 0)
                        enrichment = extract_enhanced_metadata(doc.page_content)

                        # Align chunk with timestamps from Whisper segments
                        timestamp_data = {}
                        if transcript_segments:
                            timestamp_data = align_chunk_with_timestamps(
                                doc.page_content, transcript_segments, chunk_start_char, full_transcript
                            )

                        # Build media URLs if timestamps available
                        media_urls = None
                        if (
                            timestamp_data.get("timestamp_start") is not None
                            and timestamp_data.get("timestamp_end") is not None
                        ):
                            media_urls = build_media_segment_urls(
                                file.id, timestamp_data["timestamp_start"], timestamp_data["timestamp_end"], is_video
                            )

                        # Use shared utility to build metadata
                        enriched_metadata = build_enriched_chunk_metadata(
                            base_metadata={**doc.metadata, **base_metadata},
                            enrichment=enrichment,
                            chunk_index=idx,
                            total_chunks=total_docs,
                            timestamp_start=timestamp_data.get("timestamp_start"),
                            timestamp_end=timestamp_data.get("timestamp_end"),
                            duration=timestamp_data.get("duration"),
                            chunking_strategy="character",
                            transcript_language=transcript_language,
                            transcript_duration=transcript_duration,
                            media_urls=media_urls,
                        )

                        enriched_docs.append(Document(page_content=doc.page_content, metadata=enriched_metadata))

                    docs = enriched_docs
                    log.info(f"Enriched {len(docs)} chunks with timestamps and topics/entities (character-based)")

                text_content = form_data.content
            elif form_data.collection_name:
                # Check if the file has already been processed and reuse vectors
                # Usage: /knowledge/{id}/file/add, /knowledge/{id}/file/update
                log.info(f'Checking if file {file.id} already processed in collection file-{file.id}')

                # Query with retry to handle Pinecone's eventual consistency
                # After upsert, vectors may not be immediately queryable (1-15s delay)
                max_retries = 6
                retry_delay = 3  # seconds
                result = None

                # Get namespace for file collection
                file_collection = f"file-{file.id}"
                file_namespace = get_namespace_for_collection(file_collection)

                for attempt in range(max_retries):
                    try:
                        result = VECTOR_DB_CLIENT.query(
                            collection_name=file_collection,
                            filter={"file_id": file.id},
                            namespace=file_namespace,
                        )

                        # Check if result has vectors (safely check nested structure)
                        if result is not None and result.ids and len(result.ids) > 0 and len(result.ids[0]) > 0:
                            log.info(
                                f"Found {len(result.ids[0])} existing vectors for file {file.id} on attempt {attempt + 1}"
                            )
                            break

                        if attempt < max_retries - 1:
                            log.warning(
                                f"No vectors found yet for file {file.id}, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})"
                            )
                            time.sleep(retry_delay)
                    except Exception as e:
                        log.error(f"Error querying collection file-{file.id}: {e}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)

                # Check if we successfully found vectors
                if result is not None and result.ids and len(result.ids) > 0 and len(result.ids[0]) > 0:
                    log.info(f"Reusing {len(result.ids[0])} existing vectors for file {file.id}")
                    docs = []
                    for idx, id in enumerate(result.ids[0]):
                        existing_metadata = result.metadatas[0][idx]

                        # Filter out file-specific URLs that might be from other files
                        # and regenerate them with the correct file ID
                        filtered_metadata = {
                            k: v
                            for k, v in existing_metadata.items()
                            if k not in ["video_segment_url", "audio_segment_url"]
                        }

                        # Regenerate URLs if timestamps are available
                        if "timestamp_start" in filtered_metadata and "timestamp_end" in filtered_metadata:
                            # Check if source is video or audio
                            is_video = file.meta.get("content_type", "").startswith("video/")

                            if is_video:
                                # For video files, provide both full video URL and audio URL/segment
                                filtered_metadata["video_url"] = f"/api/v1/files/{file.id}/video"
                                filtered_metadata["video_segment_url"] = (
                                    f"/api/v1/audio/video/files/{file.id}/segment"
                                    f"?start={filtered_metadata['timestamp_start']}"
                                    f"&end={filtered_metadata['timestamp_end']}"
                                )

                            # Always provide audio URL (works for both audio and video files)
                            filtered_metadata["audio_segment_url"] = (
                                f"/api/v1/audio/files/{file.id}/segment"
                                f"?start={filtered_metadata['timestamp_start']}"
                                f"&end={filtered_metadata['timestamp_end']}"
                            )

                        doc = Document(
                            page_content=result.documents[0][idx],
                            metadata={
                                **filtered_metadata,
                                # Ensure correct file metadata
                                "file_id": file.id,
                                "name": file.filename,
                                "source": file.filename,
                                # Update collection_name to the knowledge base collection
                                "collection_name": collection_name,
                            },
                        )
                        docs.append(doc)
                else:
                    log.warning(
                        f"No existing vectors found for file {file.id} after {max_retries} retries, falling back to content field"
                    )
                    # Filter out potentially contaminated file-specific URLs from metadata
                    filtered_meta = {
                        k: v for k, v in file.meta.items() if k not in ["video_segment_url", "audio_segment_url"]
                    }
                    # If this is a video, include the full video URL for client-side seeking
                    if file.meta.get("content_type", "").startswith("video/"):
                        filtered_meta["video_url"] = f"/api/v1/files/{file.id}/video"
                    docs = [
                        Document(
                            page_content=file.data.get('content', ''),
                            metadata={
                                **filtered_meta,
                                'name': file.filename,
                                'created_by': file.user_id,
                                'file_id': file.id,
                                'source': file.filename,
                                # Set collection_name to the knowledge base collection
                                'collection_name': collection_name,
                            },
                        )
                    ]
                    # IMPORTANT: Clear form_data.content so should_split=True later
                    # This ensures the fallback content gets chunked properly
                    form_data.content = None

                text_content = file.data.get('content', '')
            else:
                # Process the file and save the content
                # Usage: /files/
                file_path = file.path
                if file_path:
                    file_path = await asyncio.to_thread(Storage.get_file, file_path)
                    loader = build_loader_from_config(request)
                    loader.user = user
                    docs = await loader.aload(file.filename, file.meta.get('content_type'), file_path)

                    docs = [
                        Document(
                            page_content=doc.page_content,
                            metadata={
                                **filter_metadata(doc.metadata),
                                'name': file.filename,
                                'created_by': file.user_id,
                                'file_id': file.id,
                                'source': file.filename,
                            },
                        )
                        for doc in docs
                    ]
                else:
                    docs = [
                        Document(
                            page_content=file.data.get('content', ''),
                            metadata={
                                **file.meta,
                                'name': file.filename,
                                'created_by': file.user_id,
                                'file_id': file.id,
                                'source': file.filename,
                            },
                        )
                    ]
                text_content = ' '.join([doc.page_content for doc in docs])

            log.debug(f'text_content: {text_content}')
            await Files.update_file_data_by_id(
                file.id,
                {'content': text_content},
                db=db,
            )
            hash = calculate_sha256_string(text_content)

            if request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL:
                await Files.update_file_data_by_id(file.id, {'status': 'completed'}, db=db)
                await Files.update_file_hash_by_id(file.id, hash, db=db)
                return {
                    'status': True,
                    'collection_name': None,
                    'filename': file.filename,
                    'content': text_content,
                }
            else:
                try:
                    # Note: split=False because audio/video transcripts are already chunked above
                    # Text files will have split=True (default) since they're chunked by Loader
                    should_split = not form_data.content  # Don't split if content provided (already chunked)

                    # CRITICAL: Ensure each file's metadata includes its unique file_id
                    # This is essential for Pinecone which uses metadata filtering for collections
                    file_metadata = {
                        "file_id": file.id,
                        "name": file.filename,
                        "hash": hash,
                    }

                    # Double-check file_id is in all document metadata
                    for doc in docs:
                        if "file_id" not in doc.metadata or doc.metadata["file_id"] != file.id:
                            log.warning(
                                f"Correcting file_id in document metadata. Was: {doc.metadata.get('file_id')}, Should be: {file.id}"
                            )
                            doc.metadata["file_id"] = file.id

                    # Commit any pending changes before the slow embedding step.
                    # Note: file is already a Pydantic model (not ORM), so no expunge needed.
                    await db.commit()

                    # External embedding API takes time (5-60s+).
                    # Subsequent updates use fresh async sessions.
                    # NOTE: save_docs_to_vector_db is a sync function that
                    # calls asyncio.run_coroutine_threadsafe(..., main_loop).result()
                    # which blocks the calling thread.  We MUST run it in a
                    # worker thread to avoid deadlocking the event loop.
                    result = await run_in_threadpool(
                        save_docs_to_vector_db,
                        request,
                        docs=docs,
                        collection_name=collection_name,
                        metadata=file_metadata,
                        add=(True if form_data.collection_name else False),
                        overwrite=(
                            False if form_data.collection_name else True
                        ),  # Don't overwrite when adding to knowledge base, only when creating standalone file collection
                        split=should_split,  # Skip splitting for transcripts (already chunked)
                        user=user,
                    )
                    log.info(f'added {len(docs)} items to collection {collection_name}')

                    if result:
                        # Fresh session for the final update.
                        async with get_async_db() as session:
                            await Files.update_file_metadata_by_id(
                                file.id,
                                {
                                    'collection_name': collection_name,
                                },
                                db=session,
                            )

                            await Files.update_file_data_by_id(
                                file.id,
                                {'status': 'completed'},
                                db=session,
                            )
                            await Files.update_file_hash_by_id(file.id, hash, db=session)

                            return {
                                'status': True,
                                'collection_name': collection_name,
                                'filename': file.filename,
                                'content': text_content,
                            }
                    else:
                        raise Exception('Error saving document to vector database')
                except Exception as e:
                    raise e

        except Exception as e:
            log.exception(e)
            # Fresh session for error status update.
            async with get_async_db() as session:
                await Files.update_file_data_by_id(
                    file.id,
                    {'status': 'failed'},
                    db=session,
                )
                # Clear the hash so the file can be re-uploaded after fixing the issue
                await Files.update_file_hash_by_id(file.id, None, db=session)

            if 'No pandoc was found' in str(e):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.PANDOC_NOT_INSTALLED,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )

    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)


class ProcessTextForm(BaseModel):
    name: str
    content: str
    collection_name: Optional[str] = None


@router.post('/process/text')
async def process_text(
    request: Request,
    form_data: ProcessTextForm,
    user=Depends(get_verified_user),
):
    collection_name = form_data.collection_name
    if collection_name is None:
        collection_name = calculate_sha256_string(form_data.content)
    else:
        await _validate_collection_access([collection_name], user, access_type='write')

    docs = [
        Document(
            page_content=form_data.content,
            metadata={'name': form_data.name, 'created_by': user.id},
        )
    ]
    text_content = form_data.content
    log.debug(f'text_content: {text_content}')

    result = await run_in_threadpool(save_docs_to_vector_db, request, docs, collection_name, user=user)
    if result:
        return {
            'status': True,
            'collection_name': collection_name,
            'content': text_content,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@router.post('/process/youtube')
@router.post('/process/web')
async def process_web(
    request: Request,
    form_data: ProcessUrlForm,
    process: bool = Query(True, description='Whether to process and save the content'),
    overwrite: bool = Query(True, description='Whether to overwrite existing collection'),
    user=Depends(get_verified_user),
):
    try:
        content, docs = await run_in_threadpool(get_content_from_url, request, form_data.url)
        log.debug(f'text_content: {content}')

        if process:
            collection_name = form_data.collection_name
            if not collection_name:
                collection_name = calculate_sha256_string(form_data.url)[:63]
            else:
                await _validate_collection_access([collection_name], user, access_type='write')

            if not request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL:
                await run_in_threadpool(
                    save_docs_to_vector_db,
                    request,
                    docs,
                    collection_name,
                    overwrite=overwrite,
                    add=(not overwrite),
                    user=user,
                )
            else:
                collection_name = None

            return {
                'status': True,
                'collection_name': collection_name,
                'filename': form_data.url,
                'file': {
                    'data': {
                        'content': content,
                    },
                    'meta': {
                        'name': form_data.url,
                        'source': form_data.url,
                    },
                },
            }
        else:
            return {
                'status': True,
                'content': content,
            }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


def search_web(request: Request, engine: str, query: str, user=None) -> list[SearchResult]:
    """Search the web using a search engine and return the results as a list of SearchResult objects.
    Will look for a search engine API key in environment variables in the following order:
    - SEARXNG_QUERY_URL
    - YACY_QUERY_URL + YACY_USERNAME + YACY_PASSWORD
    - GOOGLE_PSE_API_KEY + GOOGLE_PSE_ENGINE_ID
    - BRAVE_SEARCH_API_KEY
    - KAGI_SEARCH_API_KEY
    - MOJEEK_SEARCH_API_KEY
    - BOCHA_SEARCH_API_KEY
    - SERPSTACK_API_KEY
    - SERPER_API_KEY
    - SERPLY_API_KEY
    - TAVILY_API_KEY
    - EXA_API_KEY
    - PERPLEXITY_API_KEY
    - SOUGOU_API_SID + SOUGOU_API_SK
    - SEARCHAPI_API_KEY + SEARCHAPI_ENGINE (by default `google`)
    - SERPAPI_API_KEY + SERPAPI_ENGINE (by default `google`)
    Args:
        query (str): The query to search for
    """

    # TODO: add playwright to search the web
    if engine == 'ollama_cloud':
        return search_ollama_cloud(
            'https://ollama.com',
            request.app.state.config.OLLAMA_CLOUD_WEB_SEARCH_API_KEY,
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == 'perplexity_search':
        if request.app.state.config.PERPLEXITY_API_KEY:
            return search_perplexity_search(
                request.app.state.config.PERPLEXITY_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                request.app.state.config.PERPLEXITY_SEARCH_API_URL,
                user,
            )
        else:
            raise Exception('No PERPLEXITY_API_KEY found in environment variables')
    elif engine == 'searxng':
        if request.app.state.config.SEARXNG_QUERY_URL:
            searxng_kwargs = {'language': request.app.state.config.SEARXNG_LANGUAGE}
            return search_searxng(
                request.app.state.config.SEARXNG_QUERY_URL,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                **searxng_kwargs,
            )
        else:
            raise Exception('No SEARXNG_QUERY_URL found in environment variables')
    elif engine == 'yacy':
        if request.app.state.config.YACY_QUERY_URL:
            return search_yacy(
                request.app.state.config.YACY_QUERY_URL,
                request.app.state.config.YACY_USERNAME,
                request.app.state.config.YACY_PASSWORD,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No YACY_QUERY_URL found in environment variables')
    elif engine == 'google_pse':
        if request.app.state.config.GOOGLE_PSE_API_KEY and request.app.state.config.GOOGLE_PSE_ENGINE_ID:
            return search_google_pse(
                request.app.state.config.GOOGLE_PSE_API_KEY,
                request.app.state.config.GOOGLE_PSE_ENGINE_ID,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                referer=request.app.state.config.WEBUI_URL,
            )
        else:
            raise Exception('No GOOGLE_PSE_API_KEY or GOOGLE_PSE_ENGINE_ID found in environment variables')
    elif engine == 'brave':
        if request.app.state.config.BRAVE_SEARCH_API_KEY:
            return search_brave(
                request.app.state.config.BRAVE_SEARCH_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No BRAVE_SEARCH_API_KEY found in environment variables')
    elif engine == 'brave_llm_context':
        if request.app.state.config.BRAVE_SEARCH_API_KEY:
            return search_brave_llm_context(
                request.app.state.config.BRAVE_SEARCH_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                request.app.state.config.BRAVE_SEARCH_CONTEXT_TOKENS,
            )
        else:
            raise Exception('No BRAVE_SEARCH_API_KEY found in environment variables')
    elif engine == 'kagi':
        if request.app.state.config.KAGI_SEARCH_API_KEY:
            return search_kagi(
                request.app.state.config.KAGI_SEARCH_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No KAGI_SEARCH_API_KEY found in environment variables')
    elif engine == 'mojeek':
        if request.app.state.config.MOJEEK_SEARCH_API_KEY:
            return search_mojeek(
                request.app.state.config.MOJEEK_SEARCH_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No MOJEEK_SEARCH_API_KEY found in environment variables')
    elif engine == 'bocha':
        if request.app.state.config.BOCHA_SEARCH_API_KEY:
            return search_bocha(
                request.app.state.config.BOCHA_SEARCH_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No BOCHA_SEARCH_API_KEY found in environment variables')
    elif engine == 'serpstack':
        if request.app.state.config.SERPSTACK_API_KEY:
            return search_serpstack(
                request.app.state.config.SERPSTACK_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                https_enabled=request.app.state.config.SERPSTACK_HTTPS,
            )
        else:
            raise Exception('No SERPSTACK_API_KEY found in environment variables')
    elif engine == 'serper':
        if request.app.state.config.SERPER_API_KEY:
            return search_serper(
                request.app.state.config.SERPER_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No SERPER_API_KEY found in environment variables')
    elif engine == 'serply':
        if request.app.state.config.SERPLY_API_KEY:
            return search_serply(
                request.app.state.config.SERPLY_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                filter_list=request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No SERPLY_API_KEY found in environment variables')
    elif engine == 'duckduckgo':
        return search_duckduckgo(
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            concurrent_requests=request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS,
            backend=request.app.state.config.DDGS_BACKEND,
        )
    elif engine == 'tavily':
        if request.app.state.config.TAVILY_API_KEY:
            return search_tavily(
                request.app.state.config.TAVILY_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No TAVILY_API_KEY found in environment variables')
    elif engine == 'exa':
        if request.app.state.config.EXA_API_KEY:
            return search_exa(
                request.app.state.config.EXA_API_KEY,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No EXA_API_KEY found in environment variables')
    elif engine == 'searchapi':
        if request.app.state.config.SEARCHAPI_API_KEY:
            return search_searchapi(
                request.app.state.config.SEARCHAPI_API_KEY,
                request.app.state.config.SEARCHAPI_ENGINE,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No SEARCHAPI_API_KEY found in environment variables')
    elif engine == 'serpapi':
        if request.app.state.config.SERPAPI_API_KEY:
            return search_serpapi(
                request.app.state.config.SERPAPI_API_KEY,
                request.app.state.config.SERPAPI_ENGINE,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No SERPAPI_API_KEY found in environment variables')
    elif engine == 'jina':
        return search_jina(
            request.app.state.config.JINA_API_KEY,
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.JINA_API_BASE_URL,
        )
    elif engine == 'bing':
        return search_bing(
            request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
            request.app.state.config.BING_SEARCH_V7_ENDPOINT,
            str(DEFAULT_LOCALE),
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == 'azure':
        if (
            request.app.state.config.AZURE_AI_SEARCH_API_KEY
            and request.app.state.config.AZURE_AI_SEARCH_ENDPOINT
            and request.app.state.config.AZURE_AI_SEARCH_INDEX_NAME
        ):
            return search_azure(
                request.app.state.config.AZURE_AI_SEARCH_API_KEY,
                request.app.state.config.AZURE_AI_SEARCH_ENDPOINT,
                request.app.state.config.AZURE_AI_SEARCH_INDEX_NAME,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception(
                'AZURE_AI_SEARCH_API_KEY, AZURE_AI_SEARCH_ENDPOINT, and AZURE_AI_SEARCH_INDEX_NAME are required for Azure AI Search'
            )
    elif engine == 'exa':
        return search_exa(
            request.app.state.config.EXA_API_KEY,
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == 'perplexity':
        return search_perplexity(
            request.app.state.config.PERPLEXITY_API_KEY,
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            model=request.app.state.config.PERPLEXITY_MODEL,
            search_context_usage=request.app.state.config.PERPLEXITY_SEARCH_CONTEXT_USAGE,
        )
    elif engine == 'sougou':
        if request.app.state.config.SOUGOU_API_SID and request.app.state.config.SOUGOU_API_SK:
            return search_sougou(
                request.app.state.config.SOUGOU_API_SID,
                request.app.state.config.SOUGOU_API_SK,
                query,
                request.app.state.config.WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No SOUGOU_API_SID or SOUGOU_API_SK found in environment variables')
    elif engine == 'firecrawl':
        return search_firecrawl(
            request.app.state.config.FIRECRAWL_API_BASE_URL,
            request.app.state.config.FIRECRAWL_API_KEY,
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == 'external':
        return search_external(
            request,
            request.app.state.config.EXTERNAL_WEB_SEARCH_URL,
            request.app.state.config.EXTERNAL_WEB_SEARCH_API_KEY,
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            user=user,
        )
    elif engine == 'yandex':
        return search_yandex(
            request,
            request.app.state.config.YANDEX_WEB_SEARCH_URL,
            request.app.state.config.YANDEX_WEB_SEARCH_API_KEY,
            request.app.state.config.YANDEX_WEB_SEARCH_CONFIG,
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            user=user,
        )
    elif engine == 'youcom':
        return search_youcom(
            request.app.state.config.YOUCOM_API_KEY,
            query,
            request.app.state.config.WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    else:
        raise Exception('No search engine API key found in environment variables')


@router.post('/process/web/search')
async def process_web_search(request: Request, form_data: SearchForm, user=Depends(get_verified_user)):
    if not request.app.state.config.ENABLE_WEB_SEARCH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if user.role != 'admin' and not await has_permission(
        user.id, 'features.web_search', request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    urls = []
    result_items = []

    try:
        logging.debug(f'trying to web search with {request.app.state.config.WEB_SEARCH_ENGINE, form_data.queries}')

        # Use semaphore to limit concurrent requests based on WEB_SEARCH_CONCURRENT_REQUESTS
        # 0 or None = unlimited (previous behavior), positive number = limited concurrency
        # Set to 1 for sequential execution (rate-limited APIs like Brave free tier)
        concurrent_limit = request.app.state.config.WEB_SEARCH_CONCURRENT_REQUESTS

        if concurrent_limit:
            # Limited concurrency with semaphore
            semaphore = asyncio.Semaphore(concurrent_limit)

            async def search_query_with_semaphore(query):
                async with semaphore:
                    return await run_in_threadpool(
                        search_web,
                        request,
                        request.app.state.config.WEB_SEARCH_ENGINE,
                        query,
                        user,
                    )

            search_tasks = [search_query_with_semaphore(query) for query in form_data.queries]
        else:
            # Unlimited parallel execution (previous behavior)
            search_tasks = [
                run_in_threadpool(
                    search_web,
                    request,
                    request.app.state.config.WEB_SEARCH_ENGINE,
                    query,
                    user,
                )
                for query in form_data.queries
            ]

        search_results = await asyncio.gather(*search_tasks)

        for result in search_results:
            if result:
                for item in result:
                    if item and item.link:
                        result_items.append(item)
                        urls.append(item.link)

        urls = list(dict.fromkeys(urls))
        log.debug(f'urls: {urls}')

    except Exception as e:
        log.exception(e)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.WEB_SEARCH_ERROR(e),
        )

    if len(urls) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.DEFAULT('No results found from web search'),
        )

    try:
        if request.app.state.config.BYPASS_WEB_SEARCH_WEB_LOADER:
            search_results = [item for result in search_results for item in result if result]

            docs = [
                Document(
                    page_content=result.snippet,
                    metadata={
                        'source': result.link,
                        'title': result.title,
                        'snippet': result.snippet,
                        'link': result.link,
                    },
                )
                for result in search_results
                if hasattr(result, 'snippet') and result.snippet is not None
            ]
        else:
            loader = get_web_loader(
                urls,
                verify_ssl=request.app.state.config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
                requests_per_second=request.app.state.config.WEB_LOADER_CONCURRENT_REQUESTS,
                trust_env=request.app.state.config.WEB_SEARCH_TRUST_ENV,
            )
            docs = await loader.aload()

        urls = [
            doc.metadata.get('source') for doc in docs if doc.metadata.get('source')
        ]  # only keep the urls returned by the loader
        result_items = [
            dict(item) for item in result_items if item.link in urls
        ]  # only keep the search results that have been loaded

        if request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL:
            return {
                'status': True,
                'collection_name': None,
                'filenames': urls,
                'items': result_items,
                'docs': [
                    {
                        'content': doc.page_content,
                        'metadata': doc.metadata,
                    }
                    for doc in docs
                ],
                'loaded_count': len(docs),
            }
        else:
            # Create a single collection for all documents
            collection_name = f'web-search-{calculate_sha256_string("-".join(form_data.queries))}'[:63]

            try:
                await run_in_threadpool(
                    save_docs_to_vector_db,
                    request,
                    docs,
                    collection_name,
                    overwrite=True,
                    user=user,
                )
            except Exception as e:
                log.debug(f'error saving docs: {e}')

            return {
                'status': True,
                'collection_names': [collection_name],
                'items': result_items,
                'filenames': urls,
                'loaded_count': len(docs),
            }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


async def _validate_collection_access(collection_names: list[str], user, access_type: str = 'read') -> None:
    """
    Raise 403 if the user lacks access to any of the requested collections.
    Delegates to the shared filter_accessible_collections utility so the
    access rules stay in one place.
    """
    requested = set(collection_names)
    allowed = await filter_accessible_collections(requested, user, access_type=access_type)
    denied = requested - allowed
    if denied:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


class QueryDocForm(BaseModel):
    collection_name: str
    query: str
    k: Optional[int] = None
    k_reranker: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None


@router.post('/query/doc')
async def query_doc_handler(
    request: Request,
    form_data: QueryDocForm,
    user=Depends(get_verified_user),
):
    await _validate_collection_access([form_data.collection_name], user)

    try:
        if request.app.state.config.ENABLE_RAG_HYBRID_SEARCH and (form_data.hybrid is None or form_data.hybrid):
            collection_results = {}
            namespace = get_namespace_for_collection(form_data.collection_name)
            collection_results[form_data.collection_name] = await asyncio.to_thread(
                VECTOR_DB_CLIENT.get,
                collection_name=form_data.collection_name,
                namespace=namespace,
            )
            return await query_doc_with_hybrid_search(
                collection_name=form_data.collection_name,
                collection_result=collection_results[form_data.collection_name],
                query=form_data.query,
                embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                    query, prefix=prefix, user=user
                ),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
                reranking_function=(
                    (lambda query, documents: request.app.state.RERANKING_FUNCTION(query, documents, user=user))
                    if request.app.state.RERANKING_FUNCTION
                    else None
                ),
                k_reranker=form_data.k_reranker or request.app.state.config.TOP_K_RERANKER,
                r=(form_data.r if form_data.r else request.app.state.config.RELEVANCE_THRESHOLD),
                hybrid_bm25_weight=(
                    form_data.hybrid_bm25_weight
                    if form_data.hybrid_bm25_weight
                    else request.app.state.config.HYBRID_BM25_WEIGHT
                ),
                user=user,
            )
        else:
            query_embedding = await request.app.state.EMBEDDING_FUNCTION(
                form_data.query, prefix=RAG_EMBEDDING_QUERY_PREFIX, user=user
            )
            # query_doc wraps a blocking VECTOR_DB_CLIENT.search call;
            # offload so the request's event loop stays responsive.
            return await asyncio.to_thread(
                query_doc,
                collection_name=form_data.collection_name,
                query_embedding=query_embedding,
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
                user=user,
            )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


class QueryCollectionsForm(BaseModel):
    collection_names: list[str]
    query: str
    k: Optional[int] = None
    k_reranker: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None
    hybrid_bm25_weight: Optional[float] = None
    enable_enriched_texts: Optional[bool] = None


@router.post('/query/collection')
async def query_collection_handler(
    request: Request,
    form_data: QueryCollectionsForm,
    user=Depends(get_verified_user),
):
    await _validate_collection_access(form_data.collection_names, user)

    try:
        if request.app.state.config.ENABLE_RAG_HYBRID_SEARCH and (form_data.hybrid is None or form_data.hybrid):
            return await query_collection_with_hybrid_search(
                collection_names=form_data.collection_names,
                queries=[form_data.query],
                embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                    query, prefix=prefix, user=user
                ),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
                reranking_function=(
                    (lambda query, documents: request.app.state.RERANKING_FUNCTION(query, documents, user=user))
                    if request.app.state.RERANKING_FUNCTION
                    else None
                ),
                k_reranker=form_data.k_reranker or request.app.state.config.TOP_K_RERANKER,
                r=(form_data.r if form_data.r else request.app.state.config.RELEVANCE_THRESHOLD),
                hybrid_bm25_weight=(
                    form_data.hybrid_bm25_weight
                    if form_data.hybrid_bm25_weight
                    else request.app.state.config.HYBRID_BM25_WEIGHT
                ),
                enable_enriched_texts=(
                    form_data.enable_enriched_texts
                    if form_data.enable_enriched_texts is not None
                    else request.app.state.config.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS
                ),
            )
        else:
            return await query_collection(
                request,
                collection_names=form_data.collection_names,
                queries=[form_data.query],
                embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                    query, prefix=prefix, user=user
                ),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
            )

    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


####################################
#
# Vector DB operations
#
####################################


class DeleteForm(BaseModel):
    collection_name: str
    file_id: str


@router.post('/delete')
async def delete_entries_from_collection(
    form_data: DeleteForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        namespace = get_namespace_for_collection(form_data.collection_name)

        if VECTOR_DB_CLIENT.has_collection(collection_name=form_data.collection_name, namespace=namespace):
            file = await Files.get_file_by_id(form_data.file_id, db=db)
            if not file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
            hash = file.hash

            # Refuse to issue a `filter={'hash': None}` query — the
            # match semantics of a null filter value are
            # backend-dependent (some backends ignore the key, some
            # match every row whose metadata lacks `hash`) and risk
            # deleting unrelated entries. Files without a hash are
            # typically unprocessed / failed / legacy records that
            # can't be targeted by hash anyway.
            if hash is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT('File has no hash; cannot delete vector entries by hash.'),
                )

            # Pre-existing bug: this used `metadata=` which is not a
            # parameter on `VectorDBBase.delete` nor on any backend
            # implementation, so the call always raised TypeError that
            # was silently swallowed by the surrounding `except
            # Exception` and the endpoint reported `{'status': False}`
            # for every request. Use `filter` to actually do what the
            # endpoint name promises.
            await ASYNC_VECTOR_DB_CLIENT.delete(
                collection_name=form_data.collection_name,
                filter={'hash': hash},
                namespace=namespace,
            )
            return {'status': True}
        else:
            return {'status': False}
    except HTTPException:
        # Caller-meaningful errors (404/400 above) must not be
        # swallowed and re-shaped as `{'status': False}`.
        raise
    except Exception as e:
        log.exception(e)
        return {'status': False}


@router.post('/reset/db')
async def reset_vector_db(user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    await ASYNC_VECTOR_DB_CLIENT.reset()
    await Knowledges.delete_all_knowledge(db=db)


@router.post('/reset/uploads')
async def reset_upload_dir(user=Depends(get_admin_user)) -> bool:
    folder = f'{UPLOAD_DIR}'
    try:
        # Check if the directory exists
        if os.path.exists(folder):
            # Iterate over all the files and directories in the specified directory
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # Remove the file or link
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Remove the directory
                except Exception as e:
                    log.exception(f'Failed to delete {file_path}. Reason: {e}')
        else:
            log.warning(f'The directory {folder} does not exist')
    except Exception as e:
        log.exception(f'Failed to process the directory {folder}. Reason: {e}')
    return True


if ENV == 'dev':

    @router.get('/ef/{text}')
    async def get_embeddings(request: Request, text: Optional[str] = 'Hello World!'):
        return {'result': await request.app.state.EMBEDDING_FUNCTION(text, prefix=RAG_EMBEDDING_QUERY_PREFIX)}


class BatchProcessFilesForm(BaseModel):
    files: List[FileModel]
    collection_name: str


class BatchProcessFilesResult(BaseModel):
    file_id: str
    status: str
    error: Optional[str] = None


class BatchProcessFilesResponse(BaseModel):
    results: List[BatchProcessFilesResult]
    errors: List[BatchProcessFilesResult]


@router.post('/process/files/batch')
async def process_files_batch(
    request: Request,
    form_data: BatchProcessFilesForm,
    user=Depends(get_verified_user),
    db=None,
) -> BatchProcessFilesResponse:
    """
    Process a batch of files and save them to the vector database.

    NOTE: We intentionally do NOT use Depends(get_async_session) here.
    The save_docs_to_vector_db() call makes external embedding API calls which
    can take 5-60+ seconds for batch operations. Database operations after
    embedding (Files.update_file_by_id) manage their own short-lived sessions.
    """

    collection_name = form_data.collection_name

    if collection_name:
        await _validate_collection_access([collection_name], user, access_type='write')

    file_results: List[BatchProcessFilesResult] = []
    file_errors: List[BatchProcessFilesResult] = []
    file_updates: List[FileUpdateForm] = []

    # Prepare all documents first
    all_docs: List[Document] = []

    for file in form_data.files:
        try:
            # Ownership check: verify the requesting user owns the file or is an admin
            db_file = await Files.get_file_by_id(file.id, db=db)
            if not db_file:
                file_errors.append(
                    BatchProcessFilesResult(
                        file_id=file.id,
                        status='failed',
                        error='File not found',
                    )
                )
                continue
            if db_file.user_id != user.id and user.role != 'admin':
                file_errors.append(
                    BatchProcessFilesResult(
                        file_id=file.id,
                        status='failed',
                        error='Permission denied: not file owner',
                    )
                )
                continue

            text_content = file.data.get('content', '')
            docs: List[Document] = [
                Document(
                    page_content=text_content.replace('<br/>', '\n'),
                    metadata={
                        **file.meta,
                        'name': file.filename,
                        'created_by': file.user_id,
                        'file_id': file.id,
                        'source': file.filename,
                    },
                )
            ]

            all_docs.extend(docs)

            file_updates.append(
                FileUpdateForm(
                    hash=calculate_sha256_string(text_content),
                    data={'content': text_content},
                )
            )
            file_results.append(BatchProcessFilesResult(file_id=file.id, status='prepared'))

        except Exception as e:
            log.error(f'process_files_batch: Error processing file {file.id}: {str(e)}')
            file_errors.append(BatchProcessFilesResult(file_id=file.id, status='failed', error=str(e)))

    # Save all documents in one batch
    if all_docs:
        try:
            await run_in_threadpool(
                save_docs_to_vector_db,
                request,
                all_docs,
                collection_name,
                add=True,
                user=user,
            )

            # Update all files with collection name
            for file_update, file_result in zip(file_updates, file_results):
                await Files.update_file_by_id(id=file_result.file_id, form_data=file_update, db=db)
                file_result.status = 'completed'

        except Exception as e:
            log.error(f'process_files_batch: Error saving documents to vector DB: {str(e)}')
            for file_result in file_results:
                file_result.status = 'failed'
                file_errors.append(BatchProcessFilesResult(file_id=file_result.file_id, status='failed', error=str(e)))

    return BatchProcessFilesResponse(results=file_results, errors=file_errors)
