"""
Langfuse Prompt Adapter

Provides adapter layer to sync prompts between local DB and Langfuse Cloud for version control.
"""

from typing import Optional
from langfuse import Langfuse
import logging

log = logging.getLogger(__name__)


class LangfusePromptAdapter:
    """Adapter to sync prompts between local DB and Langfuse"""

    def __init__(self, public_key: str, secret_key: str, host: str):
        self.public_key = public_key
        self.secret_key = secret_key
        self.host = host
        self.langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host
        )
        self.enabled = True
        log.info(f"[LANGFUSE] Adapter initialized with host: {host}")

    def sync_prompt_to_langfuse(self, prompt) -> bool:
        """
        Push a local prompt to Langfuse (creates new version).

        Args:
            prompt: PromptModel instance from local DB

        Returns:
            True if sync successful, False otherwise
        """
        try:
            import json
            import requests
            import base64
            from datetime import datetime

            # Map local prompt to Langfuse format
            langfuse_name = self._get_langfuse_name(prompt)

            # Create commit message with timestamp metadata
            commit_message = json.dumps({
                "timestamp": prompt.timestamp,
                "datetime": datetime.fromtimestamp(prompt.timestamp).isoformat(),
                "user_id": prompt.user_id,
                "title": prompt.title
            })

            # Use REST API directly since SDK doesn't support commitMessage
            auth_string = f"{self.public_key}:{self.secret_key}"
            auth_bytes = base64.b64encode(auth_string.encode()).decode()

            headers = {
                "Authorization": f"Basic {auth_bytes}",
                "Content-Type": "application/json"
            }

            # Prepare request body (Langfuse v2 API format)
            payload = {
                "name": langfuse_name,
                "prompt": [
                    {
                        "role": "system",
                        "content": prompt.content
                    }
                ],
                "type": "chat",
                "labels": [prompt.prompt_type] if prompt.prompt_type else [],
                "config": {
                    "command": prompt.command,
                    "title": prompt.title,
                    "prompt_type": prompt.prompt_type,
                    "persona_value": prompt.persona_value,
                    "tool_description": prompt.tool_description,
                    "tool_priority": prompt.tool_priority,
                },
                "commitMessage": commit_message
            }

            # POST to Langfuse v2 API
            url = f"{self.host}/api/public/v2/prompts"
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()

            log.info(f"[LANGFUSE] Synced prompt to Langfuse: {prompt.command}")
            return True
        except Exception as e:
            log.error(f"[LANGFUSE] Failed to sync prompt to Langfuse: {e}", exc_info=True)
            return False

    def fetch_prompt_from_langfuse(
        self,
        command: str,
        version: Optional[int] = None
    ) -> Optional[str]:
        """
        Fetch a prompt from Langfuse (specific version or latest) using v2 REST API.

        Args:
            command: Prompt command (e.g., "/base-math")
            version: Specific version number, or None for latest

        Returns:
            Prompt content string, or None if not found
        """
        try:
            import requests
            import base64

            langfuse_name = self._command_to_langfuse_name(command)

            # Prepare auth header
            auth_string = f"{self.public_key}:{self.secret_key}"
            auth_bytes = base64.b64encode(auth_string.encode()).decode()

            headers = {
                "Authorization": f"Basic {auth_bytes}",
                "Content-Type": "application/json"
            }

            # Fetch from v2 API
            url = f"{self.host}/api/public/v2/prompts/{langfuse_name}"
            params = {}
            if version is not None:
                params["version"] = version

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            version_data = response.json()

            # Extract content from chat messages
            content = ""
            if version_data.get("type") == "chat" and "prompt" in version_data:
                messages = version_data["prompt"]
                content = "\n\n".join([
                    msg.get("content", "")
                    for msg in messages
                    if isinstance(msg, dict) and msg.get("content")
                ])

            log.debug(f"[LANGFUSE] Fetched prompt from Langfuse: {command} v{version or 'latest'}")
            return content if content else None
        except Exception as e:
            log.error(f"[LANGFUSE] Failed to fetch prompt from Langfuse: {e}", exc_info=True)
            return None

    def get_prompt_versions(self, command: str, max_versions: int = 100) -> list[dict]:
        """
        Get all versions of a prompt from Langfuse using REST API v2.

        Args:
            command: Prompt command (e.g., "/base-math")
            max_versions: Maximum number of versions to fetch

        Returns:
            List of version dicts with version, content, created_at
        """
        try:
            import requests
            import json
            import base64

            prompt_name = self._command_to_langfuse_name(command)
            versions = []

            # Prepare auth header
            auth_string = f"{self.public_key}:{self.secret_key}"
            auth_bytes = base64.b64encode(auth_string.encode()).decode()

            headers = {
                "Authorization": f"Basic {auth_bytes}",
                "Content-Type": "application/json"
            }

            # Step 1: Get list of versions using v2 API
            log.debug(f"[LANGFUSE] Fetching version list for prompt: {prompt_name} via v2 REST API")
            list_url = f"{self.host}/api/public/v2/prompts"
            params = {
                "name": prompt_name,
                "page": 1,
                "limit": 1  # We only need the version list from the first item
            }

            try:
                list_response = requests.get(list_url, headers=headers, params=params, timeout=10)
                list_response.raise_for_status()
                list_data = list_response.json()

                if "data" not in list_data or len(list_data["data"]) == 0:
                    log.info(f"[LANGFUSE] Prompt not found in Langfuse: {command}")
                    return []

                # Get version numbers from the response
                prompt_info = list_data["data"][0]
                version_numbers = prompt_info.get("versions", [])

                log.info(f"[LANGFUSE] Found {len(version_numbers)} versions for: {command}")

                # Step 2: Fetch each version's details to get commitMessage
                for version_num in version_numbers[:max_versions]:
                    try:
                        detail_url = f"{self.host}/api/public/v2/prompts/{prompt_name}"
                        detail_params = {"version": version_num}

                        detail_response = requests.get(detail_url, headers=headers, params=detail_params, timeout=10)
                        detail_response.raise_for_status()
                        version_data = detail_response.json()

                        # Extract content from chat messages
                        content = ""
                        if version_data.get("type") == "chat" and "prompt" in version_data:
                            # Concatenate all message contents
                            messages = version_data["prompt"]
                            content = "\n\n".join([
                                msg.get("content", "")
                                for msg in messages
                                if isinstance(msg, dict)
                            ])

                        # Parse commitMessage for timestamp
                        created_at = None
                        commit_message = version_data.get("commitMessage")
                        if commit_message:
                            try:
                                commit_data = json.loads(commit_message)
                                created_at = commit_data.get("datetime")  # ISO format
                            except:
                                pass

                        versions.append({
                            "version": version_num,
                            "content": content,
                            "created_at": created_at,
                            "updated_at": None,
                        })

                        log.debug(f"[LANGFUSE] Fetched version {version_num} with timestamp: {created_at}")
                    except Exception as version_error:
                        log.warning(f"[LANGFUSE] Failed to fetch version {version_num}: {version_error}")
                        continue

                log.info(f"[LANGFUSE] Successfully fetched {len(versions)} versions via v2 REST API for: {command}")
                return versions

            except Exception as api_error:
                log.error(f"[LANGFUSE] v2 REST API failed: {api_error}", exc_info=True)
                return []

        except Exception as e:
            log.error(f"[LANGFUSE] Failed to fetch versions: {e}", exc_info=True)
            return []

    def _get_langfuse_name(self, prompt) -> str:
        """Convert local command to Langfuse name"""
        # Remove leading slash: "/base-math" → "base-math"
        return prompt.command.lstrip("/")

    def _command_to_langfuse_name(self, command: str) -> str:
        """Convert command to Langfuse name"""
        return command.lstrip("/")

    def get_traces_for_prompt_group(
        self,
        prompt_group_id: str,
        limit: int = 50,
        days: int = 7,
        offset: int = 0,
        summary_only: bool = False,
        model: Optional[str] = None,
        user_id: Optional[str] = None,
        chapter_id: Optional[str] = None,
    ) -> dict:
        """
        Get traces that used a specific prompt group.

        Args:
            prompt_group_id: Prompt group ID to filter by
            limit: Maximum number of traces to return
            days: Number of days to look back
            offset: Number of traces to skip (for pagination)
            summary_only: If True, return only trace metadata without observations (fast)
            model: Optional model name filter (metadata.model)
            user_id: Optional user_id filter (metadata.user_id)
            chapter_id: Optional chapter_id filter (metadata.chapter_id)

        Returns:
            Dictionary with stats and trace list
        """
        try:
            from datetime import datetime, timedelta

            # Calculate timestamp for filtering
            cutoff_time = datetime.now() - timedelta(days=days)

            # Use Langfuse REST API to fetch traces with all necessary data
            # Use trace-level metrics (totalTokens, latency, totalCost) to avoid timeout
            try:
                import requests
                import base64
                import json

                # Prepare auth header
                auth_string = f"{self.public_key}:{self.secret_key}"
                auth_bytes = base64.b64encode(auth_string.encode()).decode()

                headers = {
                    "Authorization": f"Basic {auth_bytes}",
                    "Content-Type": "application/json"
                }

                # Build filter for metadata.prompt_group_id
                filter_list = [
                    {
                        "type": "stringObject",
                        "column": "metadata",
                        "key": "prompt_group_id",
                        "operator": "=",
                        "value": prompt_group_id
                    },
                    {
                        "type": "datetime",
                        "column": "timestamp",
                        "operator": ">=",
                        "value": cutoff_time.isoformat() + "Z"
                    }
                ]
                if model:
                    filter_list.append({
                        "type": "stringObject", "column": "metadata",
                        "key": "model", "operator": "=", "value": model
                    })
                if user_id:
                    filter_list.append({
                        "type": "stringObject", "column": "metadata",
                        "key": "user_id", "operator": "=", "value": user_id
                    })
                if chapter_id:
                    filter_list.append({
                        "type": "stringObject", "column": "metadata",
                        "key": "chapter_id", "operator": "=", "value": chapter_id
                    })
                filter_json = json.dumps(filter_list)

                # Fetch traces from REST API - get trace IDs and basic metadata
                url = f"{self.host}/api/public/traces"

                # For pagination: fetch all available, then slice
                # Langfuse uses page-based pagination, convert offset to page
                page = (offset // limit) + 1

                params = {
                    "page": page,
                    "limit": limit,
                    "filter": filter_json,
                    "fields": "core,metadata",  # Get core + metadata for summary
                    "orderBy": "timestamp.desc"
                }

                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                api_data = response.json()
                traces_data = api_data.get("data", [])
                total_count = api_data.get("totalCount", len(traces_data))

                log.info(f"[LANGFUSE] Fetched {len(traces_data)} traces (page {page}) for group {prompt_group_id}, total: {total_count}")

                # If summary_only, return lightweight data without observations
                if summary_only:
                    traces = []
                    unique_users = set()
                    for trace_data in traces_data:
                        user_id = trace_data.get('userId') or trace_data.get('metadata', {}).get('user_id')
                        if user_id:
                            unique_users.add(user_id)

                        traces.append({
                            'id': trace_data.get('id'),
                            'userId': user_id,
                            'timestamp': trace_data.get('timestamp'),
                            'metadata': trace_data.get('metadata', {}),
                            'observations': []  # Empty for summary
                        })

                    log.info(f"[LANGFUSE] Returning summary-only data (no observations), fetched {len(traces)} items")

                    # For summary, return basic structure with trace list
                    trace_list = []
                    for trace in traces:
                        metadata = trace.get('metadata', {})
                        trace_list.append({
                            "trace_id": trace.get('id'),
                            "user_id": trace.get('userId'),
                            "timestamp": trace.get('timestamp'),
                            "provider": metadata.get('provider'),
                            "proficiency_level": metadata.get('proficiency_level'),
                            "response_style": metadata.get('response_style'),
                            "chapter_id": metadata.get('chapter_id'),
                            "langfuse_url": f"{self.host}/trace/{trace.get('id')}",
                        })

                    # Enrich with user details
                    user_details = {}
                    if unique_users:
                        try:
                            from open_webui.models.users import Users
                            users = Users.get_users_by_user_ids(list(unique_users))
                            user_details = {
                                user.id: {
                                    "id": user.id,
                                    "name": user.name,
                                    "email": user.email,
                                    "role": user.role
                                } for user in users
                            }
                        except Exception as user_error:
                            log.warning(f"[LANGFUSE] Failed to fetch user details: {user_error}")

                    for trace_item in trace_list:
                        user_id = trace_item.get("user_id")
                        if user_id and user_id in user_details:
                            trace_item["user"] = user_details[user_id]
                        elif user_id:
                            trace_item["user"] = {"id": user_id, "name": None, "email": None, "role": None}
                        else:
                            trace_item["user"] = None

                    # Calculate has_more based on limit, not actual fetched count
                    # This handles cases where Langfuse returns more/fewer items than requested
                    has_more = (offset + limit) < total_count
                    log.info(f"[LANGFUSE PAGINATION] offset={offset}, limit={limit}, fetched={len(trace_list)}, total={total_count}, has_more={has_more}")

                    return {
                        "stats": {
                            "total_count": total_count,
                            "fetched_count": len(traces),
                            "users": list(unique_users),
                        },
                        "traces": trace_list,
                        "pagination": {
                            "offset": offset,
                            "limit": limit,
                            "has_more": has_more
                        }
                    }

                # For detailed view, fetch observations
                trace_ids = [t.get('id') for t in traces_data]
                log.info(f"[LANGFUSE] Fetching observations for {len(trace_ids)} traces")

                # Fetch observations to get actual usage data
                # Add rate limiting: small delay between requests to avoid 429
                import time
                traces = []
                failed_count = 0

                for i, trace_id in enumerate(trace_ids):
                    try:
                        # Rate limiting: add small delay after every 5 requests
                        if i > 0 and i % 5 == 0:
                            time.sleep(0.2)  # 200ms delay every 5 requests

                        # Get observations for this trace with usage and metrics data
                        obs_url = f"{self.host}/api/public/observations"
                        obs_params = {
                            "traceId": trace_id,
                            "type": "GENERATION",
                            "fields": "core,basic,usage,metrics,io,metadata"  # Include usage for tokens/cost, metrics for latency
                        }
                        obs_response = requests.get(obs_url, headers=headers, params=obs_params, timeout=10)
                        obs_response.raise_for_status()
                        obs_data = obs_response.json()

                        observations = obs_data.get("data", [])

                        # Get trace metadata from first observation
                        if observations:
                            first_obs = observations[0]
                            trace_info = {
                                'id': trace_id,
                                'userId': first_obs.get('trace', {}).get('userId'),
                                'timestamp': first_obs.get('startTime'),
                                'metadata': first_obs.get('metadata', {}),
                                'observations': observations
                            }
                            traces.append(trace_info)
                    except requests.exceptions.HTTPError as http_error:
                        # Handle 429 specifically - skip but don't spam logs
                        if "429" in str(http_error):
                            failed_count += 1
                            if failed_count <= 3:  # Only log first 3 failures
                                log.warning(f"[LANGFUSE] Rate limited (429) for trace {trace_id}, skipping...")
                        else:
                            log.warning(f"[LANGFUSE] HTTP error fetching observations for trace {trace_id}: {http_error}")
                        continue
                    except Exception as obs_error:
                        log.warning(f"[LANGFUSE] Failed to fetch observations for trace {trace_id}: {obs_error}")
                        continue

                if failed_count > 3:
                    log.warning(f"[LANGFUSE] Rate limited on {failed_count} traces (only first 3 logged)")
                log.info(f"[LANGFUSE] Fetched observations for {len(traces)} traces (skipped {failed_count} due to rate limiting)")
            except Exception as api_error:
                log.warning(f"[LANGFUSE] Failed to fetch traces: {api_error}")
                traces = []

            # Process traces to extract statistics
            total_calls = len(traces)
            total_latency = 0
            total_tokens = 0
            unique_users = set()
            trace_list = []

            # Debug: Log first trace structure to see what data we're getting
            if traces and len(traces) > 0:
                first_trace = traces[0]
                first_obs = first_trace.get('observations', [{}])[0]
                usage = first_obs.get('usageDetails', {})

                # Debug: Log ALL time-related fields
                log.info(f"[LANGFUSE API] First observation DEBUG:")
                log.info(f"  - id: {first_obs.get('id')}")
                log.info(f"  - type: {first_obs.get('type')}")
                log.info(f"  - startTime: {first_obs.get('startTime')}")
                log.info(f"  - endTime: {first_obs.get('endTime')}")
                log.info(f"  - completionStartTime: {first_obs.get('completionStartTime')}")
                log.info(f"  - latency: {first_obs.get('latency')}")
                log.info(f"  - timeToFirstToken: {first_obs.get('timeToFirstToken')}")
                log.info(f"  - usageDetails: {usage}")
                log.info(f"  - totalCost: {first_obs.get('totalCost')}")
                log.info(f"  - All keys: {list(first_obs.keys())}")

            for trace in traces:
                # Extract data from observations
                observations = trace.get('observations', [])
                if not observations:
                    continue

                # Use first GENERATION observation for main metrics
                main_obs = observations[0]

                # Detect error: any observation flagged as ERROR level
                is_error = any((o.get('level') == 'ERROR') for o in observations)

                # Get metadata and user info
                metadata = main_obs.get('metadata', {})
                user_id = trace.get('userId') or metadata.get('user_id')  # Fallback to metadata
                trace_id = trace.get('id')
                timestamp = main_obs.get('startTime')

                # Extract user
                if user_id:
                    unique_users.add(user_id)

                # Extract token usage from usageDetails
                usage_details = main_obs.get('usageDetails', {}) or {}
                input_tokens = usage_details.get('input', 0) or 0
                output_tokens = usage_details.get('output', 0) or 0
                tokens = usage_details.get('total', 0) or (input_tokens + output_tokens)
                total_tokens += tokens

                # Get latency directly from observation's latency field (in seconds)
                latency_ms = 0
                latency_seconds = main_obs.get('latency')  # Langfuse provides latency in seconds
                if latency_seconds is not None and latency_seconds > 0:
                    latency_ms = latency_seconds * 1000
                    total_latency += latency_ms
                else:
                    # Fallback: calculate from startTime and endTime if latency field not available
                    if main_obs.get('startTime') and main_obs.get('endTime'):
                        try:
                            from datetime import datetime
                            start_time = datetime.fromisoformat(main_obs['startTime'].replace('Z', '+00:00'))
                            end_time = datetime.fromisoformat(main_obs['endTime'].replace('Z', '+00:00'))
                            latency_seconds = (end_time - start_time).total_seconds()
                            latency_ms = latency_seconds * 1000
                            total_latency += latency_ms
                        except Exception as e:
                            log.warning(f"[LANGFUSE] Failed to calculate latency from timestamps: {e}")

                # Get cost from observation
                obs_total_cost = main_obs.get('totalCost', 0) or 0

                # Extract model from metadata or observation
                model = metadata.get('model') or main_obs.get('model')

                # Get other useful metadata
                provider = metadata.get('provider')
                proficiency_level = metadata.get('proficiency_level')
                response_style = metadata.get('response_style')
                chapter_id = metadata.get('chapter_id')

                # Build Langfuse UI URL using trace ID
                langfuse_url = f"{self.host}/trace/{trace_id}"

                # Get input/output from observation
                trace_input = main_obs.get('input')
                trace_output = main_obs.get('output')

                # Truncate input/output for preview
                input_preview = None
                if trace_input:
                    if isinstance(trace_input, str):
                        input_preview = trace_input[:200] + "..." if len(trace_input) > 200 else trace_input
                    elif isinstance(trace_input, list):
                        # If it's a list of messages, get the last user message
                        for msg in reversed(trace_input):
                            if isinstance(msg, dict) and msg.get('role') == 'user':
                                content = msg.get('content', '')
                                input_preview = content[:200] + "..." if len(content) > 200 else content
                                break

                output_preview = None
                if trace_output:
                    if isinstance(trace_output, str):
                        output_preview = trace_output[:200] + "..." if len(trace_output) > 200 else trace_output
                    elif isinstance(trace_output, dict):
                        # Extract from response structure
                        content = trace_output.get('content', str(trace_output)[:200])
                        output_preview = content[:200] + "..." if len(content) > 200 else content

                # Add to trace list
                trace_item = {
                    "trace_id": trace_id,
                    "user_id": user_id,
                    "timestamp": timestamp,
                    "latency": round(latency_ms, 2),
                    "tokens": tokens,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost": round(obs_total_cost, 6) if obs_total_cost else 0,
                    "model": model,
                    "provider": provider,
                    "proficiency_level": proficiency_level,
                    "response_style": response_style,
                    "chapter_id": chapter_id,
                    "input_preview": input_preview,
                    "output_preview": output_preview,
                    "langfuse_url": langfuse_url,
                    "is_error": is_error,
                }

                trace_list.append(trace_item)

            # Calculate averages
            avg_latency = total_latency / total_calls if total_calls > 0 else 0

            # Fetch user information for all unique users
            user_details = {}
            if unique_users:
                try:
                    from open_webui.models.users import Users
                    users = Users.get_users_by_user_ids(list(unique_users))
                    user_details = {
                        user.id: {
                            "id": user.id,
                            "name": user.name,
                            "email": user.email,
                            "role": user.role
                        } for user in users
                    }
                    log.debug(f"[LANGFUSE] Fetched details for {len(user_details)} users")
                except Exception as user_error:
                    log.warning(f"[LANGFUSE] Failed to fetch user details: {user_error}")

            # Enrich trace_list with user details
            for trace_item in trace_list:
                user_id = trace_item.get("user_id")
                if user_id and user_id in user_details:
                    trace_item["user"] = user_details[user_id]
                elif user_id:
                    # User not found in DB, keep just the ID
                    trace_item["user"] = {"id": user_id, "name": None, "email": None, "role": None}
                else:
                    trace_item["user"] = None

            # Calculate has_more based on limit, not actual fetched count
            has_more = (offset + limit) < total_count
            log.info(f"[LANGFUSE PAGINATION] Detailed mode: offset={offset}, limit={limit}, fetched={len(trace_list)}, total={total_count}, has_more={has_more}")

            return {
                "stats": {
                    "total_count": total_count,
                    "total_calls": total_calls,
                    "avg_latency": round(avg_latency, 2),
                    "total_tokens": total_tokens,
                    "users": list(unique_users),
                },
                "traces": trace_list,
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "has_more": has_more
                }
            }

        except Exception as e:
            log.error(f"[LANGFUSE] Failed to fetch traces: {e}", exc_info=True)
            return {
                "stats": {
                    "total_count": 0,
                    "total_calls": 0,
                    "avg_latency": 0,
                    "total_tokens": 0,
                    "users": [],
                },
                "traces": [],
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "has_more": False
                }
            }


    def get_global_summary(self, days: int = 7) -> dict:
        """
        Aggregate stats over all traces in the time window.

        Returns: dict with today_cost_usd, total_messages, p95_latency_ms,
                 active_users, top_models[], error_rate, daily[] sparkline.
        """
        from datetime import datetime, timedelta
        import requests, base64, json, math

        cutoff = datetime.now() - timedelta(days=days)
        auth = base64.b64encode(f"{self.public_key}:{self.secret_key}".encode()).decode()
        headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

        filter_json = json.dumps([{
            "type": "datetime",
            "column": "timestamp",
            "operator": ">=",
            "value": cutoff.isoformat() + "Z"
        }])

        traces = []
        page = 1
        page_limit = 100
        max_pages = 10  # cap at 1000 traces per summary
        total_count = 0
        try:
            while page <= max_pages:
                resp = requests.get(
                    f"{self.host}/api/public/traces",
                    headers=headers,
                    params={
                        "page": page,
                        "limit": page_limit,
                        "filter": filter_json,
                        "fields": "core,metadata",
                        "orderBy": "timestamp.desc",
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                batch = data.get("data", [])
                total_count = data.get("totalCount", total_count)
                traces.extend(batch)
                if len(batch) < page_limit:
                    break
                page += 1
        except Exception as e:
            log.warning(f"[LANGFUSE] global summary trace fetch failed: {e}")

        # Fetch observations for cost/latency (best-effort, sample first 200 to limit calls)
        sampled = traces[:200]
        latencies = []
        costs_by_day = {}
        models_count = {}
        active_users = set()
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_cost = 0.0
        error_count = 0

        # Per-trace records for top-N aggregation
        trace_records: list[dict] = []
        user_tokens: dict[str, dict] = {}  # uid -> { tokens, calls, cost }

        import time as _time
        for i, t in enumerate(sampled):
            tid = t.get("id")
            try:
                if i > 0 and i % 10 == 0:
                    _time.sleep(0.1)
                obs_resp = requests.get(
                    f"{self.host}/api/public/observations",
                    headers=headers,
                    params={
                        "traceId": tid,
                        "type": "GENERATION",
                        "fields": "core,basic,usage,metrics,metadata",
                    },
                    timeout=10,
                )
                obs_resp.raise_for_status()
                obs_list = obs_resp.json().get("data", [])
                if not obs_list:
                    continue
                obs = obs_list[0]
                if obs.get("level") == "ERROR":
                    error_count += 1
                lat = obs.get("latency")
                lat_ms = lat * 1000 if lat else None
                if lat_ms is not None:
                    latencies.append(lat_ms)
                cost = obs.get("totalCost") or 0
                if cost:
                    day = (obs.get("startTime") or "")[:10]
                    costs_by_day[day] = costs_by_day.get(day, 0) + cost
                    if day == today_str:
                        today_cost += cost
                model = obs.get("model") or (obs.get("metadata", {}) or {}).get("model")
                if model:
                    models_count[model] = models_count.get(model, 0) + 1
                uid = t.get("userId") or (obs.get("metadata", {}) or {}).get("user_id")
                if uid:
                    active_users.add(uid)
                usage = obs.get("usage") or {}
                tokens = (usage.get("total") or 0) or (
                    (usage.get("input") or 0) + (usage.get("output") or 0)
                )
                trace_records.append({
                    "trace_id": tid,
                    "timestamp": t.get("timestamp") or obs.get("startTime"),
                    "model": model,
                    "user_id": uid,
                    "user_name": (t.get("metadata") or {}).get("user_name") if isinstance(t.get("metadata"), dict) else None,
                    "tokens": int(tokens or 0),
                    "cost": float(cost or 0),
                    "latency_ms": float(lat_ms) if lat_ms is not None else None,
                })
                if uid:
                    rec = user_tokens.setdefault(uid, {"tokens": 0, "calls": 0, "cost": 0.0, "name": None})
                    rec["tokens"] += int(tokens or 0)
                    rec["calls"] += 1
                    rec["cost"] += float(cost or 0)
            except Exception:
                continue

        # Resolve user names from local DB (best-effort)
        try:
            from open_webui.models.users import Users
            for uid in list(user_tokens.keys()):
                u = Users.get_user_by_id(uid)
                if u is not None:
                    user_tokens[uid]["name"] = getattr(u, "name", None) or getattr(u, "email", None)
        except Exception:
            pass

        # p95 latency
        p95 = 0
        if latencies:
            latencies.sort()
            idx = max(0, math.ceil(0.95 * len(latencies)) - 1)
            p95 = round(latencies[idx], 2)

        top_models = sorted(models_count.items(), key=lambda x: -x[1])[:5]
        daily = [
            {"date": d, "cost": round(c, 6)}
            for d, c in sorted(costs_by_day.items())
        ]

        # Top-N aggregations
        top_token_users = sorted(
            (
                {
                    "user_id": uid,
                    "name": rec.get("name"),
                    "tokens": rec["tokens"],
                    "calls": rec["calls"],
                    "cost": round(rec["cost"], 6),
                }
                for uid, rec in user_tokens.items()
                if rec["tokens"] > 0
            ),
            key=lambda r: -r["tokens"],
        )[:5]

        top_expensive = sorted(
            (
                {
                    "trace_id": r["trace_id"],
                    "timestamp": r["timestamp"],
                    "model": r["model"],
                    "cost_usd": round(r["cost"], 6),
                }
                for r in trace_records
                if r["cost"] > 0
            ),
            key=lambda r: -r["cost_usd"],
        )[:5]

        top_slow = sorted(
            (
                {
                    "trace_id": r["trace_id"],
                    "timestamp": r["timestamp"],
                    "model": r["model"],
                    "latency_ms": round(r["latency_ms"], 1),
                }
                for r in trace_records
                if r["latency_ms"] is not None
            ),
            key=lambda r: -r["latency_ms"],
        )[:5]

        return {
            "days": days,
            "total_messages": total_count,
            "sampled_messages": len(sampled),
            "today_cost_usd": round(today_cost, 6),
            "p95_latency_ms": p95,
            "active_users": len(active_users),
            "error_rate": round(error_count / len(sampled), 4) if sampled else 0,
            "top_models": [{"model": m, "count": c} for m, c in top_models],
            "daily": daily,
            "top_token_users": top_token_users,
            "top_expensive": top_expensive,
            "top_slow": top_slow,
        }


    def get_trace_detail(self, trace_id: str) -> Optional[dict]:
        """
        Fetch a single trace with input/output preview, observations breakdown,
        cost/token totals, and a Langfuse deep link.

        Returns None if not found.
        """
        import requests, base64
        auth = base64.b64encode(f"{self.public_key}:{self.secret_key}".encode()).decode()
        headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

        try:
            tr_resp = requests.get(
                f"{self.host}/api/public/traces/{trace_id}",
                headers=headers,
                timeout=15,
            )
            if tr_resp.status_code == 404:
                return None
            tr_resp.raise_for_status()
            trace = tr_resp.json()
        except Exception as e:
            log.warning(f"[LANGFUSE] trace fetch failed: {e}")
            return None

        try:
            obs_resp = requests.get(
                f"{self.host}/api/public/observations",
                headers=headers,
                params={
                    "traceId": trace_id,
                    "fields": "core,basic,usage,metrics,io,metadata",
                    "limit": 50,
                },
                timeout=15,
            )
            obs_resp.raise_for_status()
            obs_list = obs_resp.json().get("data", [])
        except Exception as e:
            log.warning(f"[LANGFUSE] observations fetch failed: {e}")
            obs_list = []

        # Aggregate
        total_cost = 0.0
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0
        total_latency_ms = 0.0
        model = None
        input_preview = ""
        output_preview = ""
        observations: list[dict] = []
        for obs in obs_list:
            cost = obs.get("totalCost") or 0
            total_cost += float(cost or 0)
            usage = obs.get("usageDetails") or obs.get("usage") or {}
            t_in = int(usage.get("input") or 0)
            t_out = int(usage.get("output") or 0)
            t_total = int(usage.get("total") or 0) or (t_in + t_out)
            input_tokens += t_in
            output_tokens += t_out
            total_tokens += t_total
            lat = obs.get("latency")
            lat_ms = (lat * 1000) if lat else 0
            total_latency_ms += lat_ms
            if model is None:
                model = obs.get("model") or (obs.get("metadata") or {}).get("model")

            observations.append({
                "name": obs.get("name") or obs.get("type") or "obs",
                "latency_ms": round(lat_ms, 1),
            })

            if obs.get("type") == "GENERATION" or not input_preview:
                obs_in = obs.get("input")
                obs_out = obs.get("output")
                if isinstance(obs_in, list):
                    for msg in reversed(obs_in):
                        if isinstance(msg, dict) and msg.get("role") == "user":
                            content = msg.get("content")
                            if isinstance(content, str):
                                input_preview = content[:800]
                                break
                elif isinstance(obs_in, str) and not input_preview:
                    input_preview = obs_in[:800]
                if isinstance(obs_out, str) and not output_preview:
                    output_preview = obs_out[:800]
                elif isinstance(obs_out, dict) and not output_preview:
                    content = obs_out.get("content") if isinstance(obs_out.get("content"), str) else None
                    output_preview = (content or str(obs_out))[:800]

        # Resolve user info
        uid = trace.get("userId") or (trace.get("metadata") or {}).get("user_id")
        user_block = None
        if uid:
            try:
                from open_webui.models.users import Users
                u = Users.get_user_by_id(uid)
                if u is not None:
                    user_block = {
                        "id": u.id,
                        "name": getattr(u, "name", None),
                        "email": getattr(u, "email", None),
                    }
                else:
                    user_block = {"id": uid, "name": None, "email": None}
            except Exception:
                user_block = {"id": uid, "name": None, "email": None}

        return {
            "trace_id": trace_id,
            "timestamp": trace.get("timestamp"),
            "user": user_block,
            "model": model,
            "input_preview": input_preview,
            "output_preview": output_preview,
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_cost_usd": round(total_cost, 6),
            "latency_ms": round(total_latency_ms, 1),
            "observations": observations,
            "langfuse_url": f"{self.host}/trace/{trace_id}",
        }


# Singleton instance
_langfuse_adapter: Optional[LangfusePromptAdapter] = None


def get_langfuse_adapter() -> Optional[LangfusePromptAdapter]:
    """
    Get or create Langfuse adapter (returns None if not configured).

    Returns:
        LangfusePromptAdapter instance if configured, None otherwise
    """
    global _langfuse_adapter
    if _langfuse_adapter is None:
        try:
            # Check if Langfuse is configured
            from open_webui.env import LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST, LANGFUSE_ENABLED

            if LANGFUSE_ENABLED and LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY and LANGFUSE_HOST:
                _langfuse_adapter = LangfusePromptAdapter(
                    public_key=LANGFUSE_PUBLIC_KEY,
                    secret_key=LANGFUSE_SECRET_KEY,
                    host=LANGFUSE_HOST
                )
                log.info("[LANGFUSE] Adapter singleton created")
            else:
                log.warning("[LANGFUSE] Not configured or disabled")
        except Exception as e:
            log.error(f"[LANGFUSE] Failed to initialize adapter: {e}", exc_info=True)

    return _langfuse_adapter
