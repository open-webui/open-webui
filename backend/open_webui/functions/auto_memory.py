"""
title: Auto Memory
description: Automatically extract and store conversation facts using NER
author: open-webui
version: 1.0.0
requirements: spacy>=3.7.0
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import time
import logging

log = logging.getLogger(__name__)


class Filter:
    """
    Auto Memory Outlet Filter

    Automatically extracts entities and facts from LLM responses
    and stores them in the user's memory system using ChromaDB.
    """

    class Valves(BaseModel):
        """Configuration for Auto Memory filter"""
        enabled: bool = Field(
            default=True,
            description="Enable/disable automatic memory extraction"
        )
        min_confidence: float = Field(
            default=0.7,
            ge=0.0,
            le=1.0,
            description="Minimum confidence threshold for entity extraction"
        )
        memory_types: List[str] = Field(
            default=["PERSON", "ORG", "GPE", "DATE", "TIME", "MONEY", "PRODUCT"],
            description="Entity types to extract and store"
        )
        max_context_length: int = Field(
            default=200,
            description="Maximum context characters to store with each memory"
        )
        deduplicate: bool = Field(
            default=True,
            description="Avoid storing duplicate memories"
        )

    def __init__(self):
        """Initialize the Auto Memory filter"""
        self.valves = self.Valves()
        self.nlp = None
        self._recent_memories = {}  # Simple dedup cache

    def _load_nlp(self):
        """Lazy load Spacy NLP model"""
        if self.nlp is None:
            try:
                import spacy
                try:
                    self.nlp = spacy.load("en_core_web_sm")
                    log.info("Spacy model loaded successfully")
                except OSError:
                    log.warning("Spacy model not found, downloading...")
                    import subprocess
                    subprocess.run(
                        ["python", "-m", "spacy", "download", "en_core_web_sm"],
                        check=True
                    )
                    self.nlp = spacy.load("en_core_web_sm")
                    log.info("Spacy model downloaded and loaded")
            except Exception as e:
                log.error(f"Failed to load Spacy model: {str(e)}")
                raise

    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract named entities from text

        Args:
            text: Text to process

        Returns:
            List of extracted entities with metadata
        """
        if not text or not text.strip():
            return []

        self._load_nlp()
        doc = self.nlp(text)

        entities = []
        for ent in doc.ents:
            if ent.label_ in self.valves.memory_types:
                # Get sentence context
                sent_text = ent.sent.text

                # Truncate context if needed
                if len(sent_text) > self.valves.max_context_length:
                    sent_text = sent_text[:self.valves.max_context_length] + "..."

                entity_data = {
                    "text": ent.text,
                    "type": ent.label_,
                    "context": sent_text,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "confidence": 0.9,  # Spacy doesn't provide confidence, use default
                }

                # Apply confidence threshold
                if entity_data["confidence"] >= self.valves.min_confidence:
                    entities.append(entity_data)

        return entities

    def _should_store_memory(self, entity: Dict[str, Any], user_id: str) -> bool:
        """
        Check if memory should be stored (deduplication)

        Args:
            entity: Entity to check
            user_id: User ID

        Returns:
            True if memory should be stored
        """
        if not self.valves.deduplicate:
            return True

        # Simple dedup: check if same entity stored in last 10 minutes
        cache_key = f"{user_id}:{entity['type']}:{entity['text'].lower()}"
        last_stored = self._recent_memories.get(cache_key, 0)
        current_time = time.time()

        if current_time - last_stored < 600:  # 10 minutes
            return False

        self._recent_memories[cache_key] = current_time
        return True

    def _store_memory(self, entity: Dict[str, Any], user_id: str) -> bool:
        """
        Store entity in ChromaDB memory

        Args:
            entity: Entity to store
            user_id: User ID

        Returns:
            True if stored successfully
        """
        try:
            from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

            collection_name = f"user-memory-{user_id}"

            # Format memory text
            memory_text = f"{entity['type']}: {entity['text']}"
            if entity.get('context'):
                memory_text += f" (Context: {entity['context']})"

            # Store in vector database
            VECTOR_DB_CLIENT.insert(
                collection_name=collection_name,
                documents=[memory_text],
                metadatas=[{
                    "type": entity["type"],
                    "entity": entity["text"],
                    "context": entity.get("context", ""),
                    "source": "auto_memory",
                    "confidence": entity.get("confidence", 0.9),
                    "timestamp": int(time.time()),
                    "version": "1.0.0"
                }]
            )

            log.debug(f"Stored memory for user {user_id}: {memory_text}")
            return True

        except Exception as e:
            log.error(f"Failed to store memory: {str(e)}")
            return False

    async def outlet(
        self,
        body: dict,
        user: Optional[dict] = None,
        __event_emitter__=None
    ) -> dict:
        """
        Process LLM response and extract memories

        This is the main filter function that processes assistant responses.

        Args:
            body: Message body containing messages array
            user: User dict with id and other info
            __event_emitter__: Optional event emitter

        Returns:
            Modified body with metadata
        """
        # Skip if disabled or no user
        if not self.valves.enabled or not user:
            return body

        try:
            # Extract last assistant message
            messages = body.get("messages", [])
            if not messages:
                return body

            last_message = messages[-1]
            if last_message.get("role") != "assistant":
                return body

            content = last_message.get("content", "")
            if not content:
                return body

            # Extract entities
            entities = self._extract_entities(content)

            if not entities:
                # No entities found
                body["__metadata__"] = body.get("__metadata__", {})
                body["__metadata__"]["auto_memory"] = {
                    "extracted": 0,
                    "stored": 0,
                    "types": []
                }
                return body

            # Store entities
            stored_count = 0
            stored_types = set()

            for entity in entities:
                if self._should_store_memory(entity, user["id"]):
                    if self._store_memory(entity, user["id"]):
                        stored_count += 1
                        stored_types.add(entity["type"])

            # Add metadata to response
            body["__metadata__"] = body.get("__metadata__", {})
            body["__metadata__"]["auto_memory"] = {
                "extracted": len(entities),
                "stored": stored_count,
                "types": list(stored_types)
            }

            # Emit event if available
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {
                        "description": f"Auto Memory: Stored {stored_count} new memories",
                        "done": True
                    }
                })

            log.info(f"Auto Memory: Extracted {len(entities)}, stored {stored_count} for user {user['id']}")

        except Exception as e:
            log.error(f"Auto Memory error: {str(e)}")
            # Don't fail the request, just log error
            body["__metadata__"] = body.get("__metadata__", {})
            body["__metadata__"]["auto_memory"] = {
                "error": str(e),
                "extracted": 0,
                "stored": 0
            }

        return body
