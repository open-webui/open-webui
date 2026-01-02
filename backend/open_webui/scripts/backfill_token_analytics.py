#!/usr/bin/env python3
"""
Token Analytics Backfill Script

This script retroactively calculates token usage for all existing chats
and populates the analytics tables (conversation_token_usage, daily_token_usage,
model_token_usage) for the "Wrapped" feature.

Usage:
    python -m open_webui.scripts.backfill_token_analytics [--dry-run] [--verbose] [--user-id USER_ID] [--clear]

Token Counting Logic:
    - INPUT tokens = sum of ALL message tokens (U1 + A1 + U2 + A2 + U3 + A3 + ...)
    - OUTPUT tokens = ONLY the last assistant message tokens
    - TOTAL tokens = cumulative API context cost per turn, summed (what you actually pay for)
    
    Example for a 3-turn conversation (U=user, A=assistant):
    - Turn 1 API call: sends U1, receives A1 → cost = U1 + A1
    - Turn 2 API call: sends U1+A1+U2, receives A2 → cost = U1 + A1 + U2 + A2
    - Turn 3 API call: sends U1+A1+U2+A2+U3, receives A3 → cost = U1 + A1 + U2 + A2 + U3 + A3
    
    So:
    - input_tokens = U1 + A1 + U2 + A2 + U3 + A3 (simple sum of all messages)
    - output_tokens = A3 (last assistant message only)
    - total_tokens = (U1+A1) + (U1+A1+U2+A2) + (U1+A1+U2+A2+U3+A3) (cumulative context)

Uses tiktoken with o200k_base encoding for all models.
"""

import argparse
import logging
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

import tiktoken

# Set up path for imports
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Allow DATABASE_URL to be set before importing db module
def setup_database_url():
    """Print and optionally override DATABASE_URL"""
    from open_webui.env import DATABASE_URL, DATA_DIR
    print(f"DATABASE_URL: {DATABASE_URL}")
    print(f"DATA_DIR: {DATA_DIR}")
    return DATABASE_URL

# Print database info early
_db_url = setup_database_url()

from open_webui.internal.db import get_db
from open_webui.models.chats import Chat, Chats
from open_webui.models.analytics import (
    ConversationTokenUsage,
    DailyTokenUsage, 
    ModelTokenUsage,
    Analytics
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# Initialize tiktoken encoder with o200k_base
# This is used for all models as specified
ENCODING = tiktoken.get_encoding("o200k_base")


class TokenCounter:
    """Handles token counting using tiktoken o200k_base encoding"""
    
    def __init__(self):
        self.encoding = ENCODING
        self._cache = {}  # Cache for repeated content
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string"""
        if not text:
            return 0
        
        # Use cache for repeated content (common in conversations)
        cache_key = hash(text[:1000]) if len(text) > 1000 else hash(text)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            token_count = len(self.encoding.encode(text, disallowed_special=()))
            self._cache[cache_key] = token_count
            return token_count
        except Exception as e:
            log.warning(f"Error counting tokens: {e}")
            # Fallback: rough estimate of 4 characters per token
            return len(text) // 4
    
    def count_message_tokens(self, message: Dict) -> int:
        """Count tokens in a message (content + any structured data)"""
        total = 0
        
        # Main content
        content = message.get('content', '')
        if isinstance(content, str):
            total += self.count_tokens(content)
        elif isinstance(content, list):
            # Handle multi-modal content (text + images)
            for part in content:
                if isinstance(part, dict):
                    if part.get('type') == 'text':
                        total += self.count_tokens(part.get('text', ''))
                    # Image tokens are counted as a fixed amount by most models
                    elif part.get('type') == 'image_url':
                        total += 85  # Base tokens for image
                elif isinstance(part, str):
                    total += self.count_tokens(part)
        
        # Add overhead for message structure (role, etc.)
        total += 4  # Approximate overhead per message
        
        return total


class ConversationTracer:
    """Extracts ordered message list from conversation history"""
    
    @staticmethod
    def get_messages_in_order(history: Dict) -> List[Dict]:
        """
        Extract messages from history in conversation order.
        Follows the parent-child chain from root to current.
        """
        messages = history.get('messages', {})
        current_id = history.get('currentId')
        
        if not messages or not current_id:
            return []
        
        # Build the actual conversation path (from root to current)
        path = []
        visited = set()
        
        # First, trace back from current to root
        msg_id = current_id
        while msg_id and msg_id not in visited:
            visited.add(msg_id)
            if msg_id in messages:
                path.append(messages[msg_id])
                msg_id = messages[msg_id].get('parentId')
            else:
                break
        
        # Reverse to get root-to-current order
        path.reverse()
        
        return path
    
    @staticmethod
    def get_model_from_message(message: Dict, default_model: str = 'unknown') -> str:
        """Extract model ID from a message"""
        return message.get('model') or message.get('selectedModelId') or default_model


class ChatTokenAnalyzer:
    """Analyzes a chat and calculates token usage"""
    
    def __init__(self, token_counter: TokenCounter, verbose: bool = False):
        self.counter = token_counter
        self.tracer = ConversationTracer()
        self.verbose = verbose
    
    def analyze_chat(self, chat: Dict, chat_id: str, user_id: str) -> Optional[Dict]:
        """
        Analyze a chat and return token statistics.
        
        Token Calculation Logic:
        - INPUT = Simple sum of ALL message tokens (U1 + A1 + U2 + A2 + ...)
        - OUTPUT = ONLY the last assistant message tokens
        - TOTAL = Sum of cumulative turn totals (what API actually charges)
        
        Returns:
            Dict with:
            - total_input_tokens: Sum of all message tokens
            - total_output_tokens: Last assistant message tokens only
            - total_tokens: Cumulative API cost
            - message_count: Number of messages
            - model_id: Primary model used
            - turns: List of turn details for debugging
        """
        history = chat.get('history', {})
        models = chat.get('models', [])
        default_model = models[0] if models else 'unknown'
        
        # Get messages in order
        messages = self.tracer.get_messages_in_order(history)
        
        if not messages:
            # Try fallback to messages array
            messages = chat.get('messages', [])
        
        if not messages:
            if self.verbose:
                log.warning(f"Chat {chat_id}: No messages found")
            return None
        
        # First pass: count tokens for each message
        message_tokens = []  # List of (role, tokens, model) tuples
        message_count = len(messages)
        primary_model = default_model
        
        for message in messages:
            role = message.get('role', '')
            model = self.tracer.get_model_from_message(message, default_model)
            msg_tokens = self.counter.count_message_tokens(message)
            message_tokens.append((role, msg_tokens, model))
        
        # Calculate totals with CORRECT logic:
        # INPUT = simple sum of ALL tokens
        total_input_tokens = sum(tokens for _, tokens, _ in message_tokens)
        
        # OUTPUT = ONLY the last assistant message
        total_output_tokens = 0
        for role, tokens, _ in reversed(message_tokens):
            if role == 'assistant':
                total_output_tokens = tokens
                break
        
        # TOTAL = cumulative API cost (sum of each turn's context)
        # Turn N costs: all messages from 1 to N (context sent + response)
        total_tokens = 0
        context_tokens = 0
        model_usage = defaultdict(int)
        turns = []
        
        for i, (role, tokens, model) in enumerate(message_tokens):
            if role == 'assistant':
                # This turn's cost = context (all previous) + this response
                turn_total = context_tokens + tokens
                total_tokens += turn_total
                model_usage[model] += turn_total
                
                if self.verbose:
                    turns.append({
                        'turn': len(turns) + 1,
                        'context_tokens': context_tokens,
                        'output_tokens': tokens,
                        'turn_total': turn_total,
                        'model': model
                    })
            
            # Add this message to context for next turn
            context_tokens += tokens
        
        # Determine primary model (most tokens used)
        if model_usage:
            primary_model = max(model_usage.keys(), key=lambda k: model_usage[k])
        
        return {
            'chat_id': chat_id,
            'user_id': user_id,
            'total_input_tokens': total_input_tokens,
            'total_output_tokens': total_output_tokens,
            'total_tokens': total_tokens,
            'message_count': message_count,
            'model_id': primary_model,
            'model_usage': dict(model_usage),
            'turns': turns if self.verbose else []
        }


class BackfillProcessor:
    """Main processor for backfilling token analytics"""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.counter = TokenCounter()
        self.analyzer = ChatTokenAnalyzer(self.counter, verbose)
        
        # Statistics
        self.stats = {
            'total_chats': 0,
            'processed_chats': 0,
            'skipped_chats': 0,
            'error_chats': 0,
            'total_tokens': 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_messages': 0,
            'users': set(),
            'models': defaultdict(int),
            'daily_tokens': defaultdict(int),
        }
    
    def process_all_chats(self, user_id_filter: Optional[str] = None) -> Dict:
        """Process all chats (or filter by user_id)"""
        log.info("=" * 60)
        log.info("Token Analytics Backfill Script")
        log.info("=" * 60)
        log.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        log.info(f"Verbose: {self.verbose}")
        if user_id_filter:
            log.info(f"Filtering to user: {user_id_filter}")
        log.info("")
        
        start_time = time.time()
        
        # Fetch all chats
        log.info("Fetching chats from database...")
        with get_db() as db:
            query = db.query(Chat)
            if user_id_filter:
                query = query.filter(Chat.user_id == user_id_filter)
            # Exclude shared chats (user_id starts with "shared-")
            query = query.filter(~Chat.user_id.startswith('shared-'))
            all_chats = query.all()
        
        self.stats['total_chats'] = len(all_chats)
        log.info(f"Found {len(all_chats)} chats to process")
        log.info("")
        
        # Process each chat
        for idx, chat_record in enumerate(all_chats, 1):
            try:
                self._process_single_chat(chat_record, idx)
            except Exception as e:
                log.error(f"Error processing chat {chat_record.id}: {e}")
                self.stats['error_chats'] += 1
                if self.verbose:
                    import traceback
                    traceback.print_exc()
            
            # Progress update every 100 chats
            if idx % 100 == 0:
                elapsed = time.time() - start_time
                rate = idx / elapsed
                log.info(f"Progress: {idx}/{len(all_chats)} chats ({rate:.1f} chats/sec)")
        
        # Finalize
        elapsed = time.time() - start_time
        self._print_summary(elapsed)
        
        return self.stats
    
    def _process_single_chat(self, chat_record: Chat, idx: int):
        """Process a single chat record"""
        chat_id = chat_record.id
        user_id = chat_record.user_id
        chat_data = chat_record.chat
        created_at = chat_record.created_at
        
        if self.verbose:
            log.info(f"[{idx}] Processing chat: {chat_id} (user: {user_id})")
        
        # Analyze the chat
        result = self.analyzer.analyze_chat(chat_data, chat_id, user_id)
        
        if not result or result['total_tokens'] == 0:
            self.stats['skipped_chats'] += 1
            if self.verbose:
                log.info(f"  Skipped: No tokens found")
            return
        
        # Update statistics
        self.stats['processed_chats'] += 1
        self.stats['total_tokens'] += result['total_tokens']
        self.stats['total_input_tokens'] += result['total_input_tokens']
        self.stats['total_output_tokens'] += result['total_output_tokens']
        self.stats['total_messages'] += result['message_count']
        self.stats['users'].add(user_id)
        
        # Track model usage
        for model, tokens in result['model_usage'].items():
            self.stats['models'][model] += tokens
        
        # Track daily usage
        chat_date = datetime.fromtimestamp(created_at, tz=timezone.utc).strftime('%Y-%m-%d')
        self.stats['daily_tokens'][chat_date] += result['total_tokens']
        
        if self.verbose:
            log.info(f"  Input: {result['total_input_tokens']:,} tokens")
            log.info(f"  Output: {result['total_output_tokens']:,} tokens")
            log.info(f"  Total: {result['total_tokens']:,} tokens")
            log.info(f"  Messages: {result['message_count']}")
            log.info(f"  Model: {result['model_id']}")
        
        # Store in database
        if not self.dry_run:
            self._store_analytics(result, chat_date, created_at)
    
    def _store_analytics(self, result: Dict, chat_date: str, created_at: int):
        """Store analytics data in database"""
        try:
            with get_db() as db:
                now = int(time.time())
                
                # 1. Store/Update ConversationTokenUsage
                conv_record = db.query(ConversationTokenUsage).filter_by(
                    chat_id=result['chat_id']
                ).first()
                
                if conv_record:
                    # Update existing - add backfill data
                    conv_record.total_input_tokens = result['total_input_tokens']
                    conv_record.total_output_tokens = result['total_output_tokens']
                    conv_record.total_tokens = result['total_tokens']
                    conv_record.message_count = result['message_count']
                    conv_record.model_id = result['model_id']
                    conv_record.updated_at = now
                else:
                    # Create new
                    conv_record = ConversationTokenUsage(
                        id=str(uuid.uuid4()),
                        chat_id=result['chat_id'],
                        user_id=result['user_id'],
                        model_id=result['model_id'],
                        total_input_tokens=result['total_input_tokens'],
                        total_output_tokens=result['total_output_tokens'],
                        total_tokens=result['total_tokens'],
                        last_input_tokens=0,
                        last_output_tokens=0,
                        message_count=result['message_count'],
                        created_at=created_at,
                        updated_at=now
                    )
                    db.add(conv_record)
                
                # 2. Update DailyTokenUsage
                daily_record = db.query(DailyTokenUsage).filter_by(
                    user_id=result['user_id'],
                    date=chat_date
                ).first()
                
                if daily_record:
                    daily_record.total_input_tokens += result['total_input_tokens']
                    daily_record.total_output_tokens += result['total_output_tokens']
                    daily_record.total_tokens += result['total_tokens']
                    daily_record.conversation_count += 1
                    daily_record.message_count += result['message_count']
                    daily_record.updated_at = now
                else:
                    daily_record = DailyTokenUsage(
                        id=str(uuid.uuid4()),
                        user_id=result['user_id'],
                        date=chat_date,
                        total_input_tokens=result['total_input_tokens'],
                        total_output_tokens=result['total_output_tokens'],
                        total_tokens=result['total_tokens'],
                        conversation_count=1,
                        message_count=result['message_count'],
                        created_at=now,
                        updated_at=now
                    )
                    db.add(daily_record)
                
                # 3. Update ModelTokenUsage (per-user)
                for model_id, model_tokens in result['model_usage'].items():
                    # Calculate input/output ratio for this model
                    total_tokens = result['total_tokens']
                    model_input = int(result['total_input_tokens'] * model_tokens / total_tokens) if total_tokens > 0 else 0
                    model_output = int(result['total_output_tokens'] * model_tokens / total_tokens) if total_tokens > 0 else 0
                    
                    # User-specific record
                    user_model_record = db.query(ModelTokenUsage).filter_by(
                        user_id=result['user_id'],
                        model_id=model_id
                    ).first()
                    
                    if user_model_record:
                        user_model_record.total_input_tokens += model_input
                        user_model_record.total_output_tokens += model_output
                        user_model_record.total_tokens += model_tokens
                        user_model_record.conversation_count += 1
                        user_model_record.message_count += result['message_count']
                        user_model_record.updated_at = now
                    else:
                        user_model_record = ModelTokenUsage(
                            id=str(uuid.uuid4()),
                            user_id=result['user_id'],
                            model_id=model_id,
                            total_input_tokens=model_input,
                            total_output_tokens=model_output,
                            total_tokens=model_tokens,
                            conversation_count=1,
                            message_count=result['message_count'],
                            created_at=now,
                            updated_at=now
                        )
                        db.add(user_model_record)
                    
                    # Global record (user_id=None)
                    global_model_record = db.query(ModelTokenUsage).filter_by(
                        user_id=None,
                        model_id=model_id
                    ).first()
                    
                    if global_model_record:
                        global_model_record.total_input_tokens += model_input
                        global_model_record.total_output_tokens += model_output
                        global_model_record.total_tokens += model_tokens
                        global_model_record.conversation_count += 1
                        global_model_record.message_count += result['message_count']
                        global_model_record.updated_at = now
                    else:
                        global_model_record = ModelTokenUsage(
                            id=str(uuid.uuid4()),
                            user_id=None,
                            model_id=model_id,
                            total_input_tokens=model_input,
                            total_output_tokens=model_output,
                            total_tokens=model_tokens,
                            conversation_count=1,
                            message_count=result['message_count'],
                            created_at=now,
                            updated_at=now
                        )
                        db.add(global_model_record)
                
                db.commit()
                
        except Exception as e:
            log.error(f"Error storing analytics for chat {result['chat_id']}: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
    
    def _print_summary(self, elapsed: float):
        """Print final summary"""
        log.info("")
        log.info("=" * 60)
        log.info("BACKFILL COMPLETE")
        log.info("=" * 60)
        log.info("")
        log.info(f"Time elapsed: {elapsed:.1f} seconds")
        log.info(f"Rate: {self.stats['total_chats'] / elapsed:.1f} chats/second")
        log.info("")
        log.info("Chat Statistics:")
        log.info(f"  Total chats found: {self.stats['total_chats']:,}")
        log.info(f"  Successfully processed: {self.stats['processed_chats']:,}")
        log.info(f"  Skipped (no tokens): {self.stats['skipped_chats']:,}")
        log.info(f"  Errors: {self.stats['error_chats']:,}")
        log.info("")
        log.info("Token Statistics:")
        log.info(f"  Total input tokens: {self.stats['total_input_tokens']:,}")
        log.info(f"  Total output tokens: {self.stats['total_output_tokens']:,}")
        log.info(f"  Total tokens: {self.stats['total_tokens']:,}")
        log.info(f"  Total messages: {self.stats['total_messages']:,}")
        log.info("")
        log.info("User Statistics:")
        log.info(f"  Unique users: {len(self.stats['users']):,}")
        log.info(f"  Avg tokens per user: {self.stats['total_tokens'] / len(self.stats['users']):,.0f}" if self.stats['users'] else "  No users")
        log.info("")
        log.info("Top Models by Token Usage:")
        sorted_models = sorted(self.stats['models'].items(), key=lambda x: x[1], reverse=True)[:10]
        for i, (model, tokens) in enumerate(sorted_models, 1):
            pct = tokens / self.stats['total_tokens'] * 100 if self.stats['total_tokens'] > 0 else 0
            log.info(f"  {i}. {model}: {tokens:,} tokens ({pct:.1f}%)")
        log.info("")
        log.info("Days with Activity:")
        log.info(f"  Total days: {len(self.stats['daily_tokens']):,}")
        if self.stats['daily_tokens']:
            max_day = max(self.stats['daily_tokens'].items(), key=lambda x: x[1])
            log.info(f"  Busiest day: {max_day[0]} ({max_day[1]:,} tokens)")
        log.info("")
        if self.dry_run:
            log.info("NOTE: This was a DRY RUN. No data was written to the database.")
            log.info("Run without --dry-run to actually backfill the data.")


def main():
    parser = argparse.ArgumentParser(
        description='Backfill token analytics for existing chats',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run analysis without writing to database'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output with per-chat details'
    )
    parser.add_argument(
        '--user-id',
        type=str,
        default=None,
        help='Only process chats for a specific user ID'
    )
    parser.add_argument(
        '--clear-existing',
        action='store_true',
        help='Clear existing analytics data before backfill (prompts for confirmation)'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing analytics data without prompting (USE WITH CAUTION)'
    )
    
    args = parser.parse_args()
    
    # Clear existing data if requested
    if (args.clear or args.clear_existing) and not args.dry_run:
        if args.clear_existing and not args.clear:
            # Prompt for confirmation
            confirm = input("WARNING: This will delete all existing token analytics data. Continue? (yes/no): ")
            if confirm.lower() != 'yes':
                log.info("Aborted.")
                return
        
        log.info("Clearing existing analytics data...")
        with get_db() as db:
            conv_count = db.query(ConversationTokenUsage).delete()
            daily_count = db.query(DailyTokenUsage).delete()
            model_count = db.query(ModelTokenUsage).delete()
            db.commit()
        log.info(f"Cleared: {conv_count} conversation records, {daily_count} daily records, {model_count} model records")
    
    # Run backfill
    processor = BackfillProcessor(
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    try:
        processor.process_all_chats(user_id_filter=args.user_id)
    except KeyboardInterrupt:
        log.info("\nBackfill interrupted by user.")
        sys.exit(1)
    except Exception as e:
        log.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
