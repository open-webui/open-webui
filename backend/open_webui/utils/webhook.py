import json
import logging
import asyncio
import uuid
from typing import Optional, List

import aiohttp
from open_webui.config import WEBUI_FAVICON_URL
from open_webui.env import SRC_LOG_LEVELS, VERSION
from open_webui.internal.db import get_db
from open_webui.utils.webhook_events import WebhookEvent, is_valid_event

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["WEBHOOK"])


async def post_webhook(name: str, url: str, message: str, event_data: dict) -> bool:
    """Post webhook to a single URL - now async to match dev branch"""
    try:
        log.debug(f"post_webhook: {url}, {message}, {event_data}")
        payload = {}

        # Slack and Google Chat Webhooks
        if "https://hooks.slack.com" in url or "https://chat.googleapis.com" in url:
            payload["text"] = message
        # Discord Webhooks
        elif "https://discord.com/api/webhooks" in url:
            payload["content"] = (
                message
                if len(message) < 2000
                else f"{message[: 2000 - 20]}... (truncated)"
            )
        # Microsoft Teams Webhooks
        elif "webhook.office.com" in url:
            action = event_data.get("action", "undefined")
            facts = [
                {"name": name, "value": value}
                for name, value in json.loads(event_data.get("user", {})).items()
            ]
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "0076D7",
                "summary": message,
                "sections": [
                    {
                        "activityTitle": message,
                        "activitySubtitle": f"{name} ({VERSION}) - {action}",
                        "activityImage": WEBUI_FAVICON_URL,
                        "facts": facts,
                        "markdown": True,
                    }
                ],
            }
        # Default Payload
        else:
            payload = {**event_data}

        log.debug(f"payload: {payload}")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as r:
                r_text = await r.text()
                r.raise_for_status()
                log.debug(f"r.text: {r_text}")

        return True
    except Exception as e:
        log.exception(e)
        return False


def post_webhook_sync(name: str, url: str, message: str, event_data: dict) -> bool:
    """Synchronous wrapper for post_webhook - for legacy compatibility"""
    import asyncio

    try:
        # Run the async function in the current event loop if it exists
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, we can't use asyncio.run
            # Create a new task and return the result synchronously (not recommended but needed for compatibility)
            task = loop.create_task(post_webhook(name, url, message, event_data))
            # This is a hack - in practice the sync function should be avoided
            # We'll return True and let the background processing handle it
            return True
        except RuntimeError:
            # No event loop running, we can use asyncio.run
            return asyncio.run(post_webhook(name, url, message, event_data))
    except Exception as e:
        log.exception(f"Error in sync webhook wrapper: {e}")
        return False


async def store_webhook_event_async(
    url: str, name: str, message: str, event_data: dict
) -> str:
    """Store webhook event for later processing and return the event ID"""
    try:
        # Import here to avoid circular imports
        from open_webui.models.webhooks import WebhookEvents

        db = next(get_db())
        webhook_events = WebhookEvents(db)

        event_id = str(uuid.uuid4())

        # Create complete event payload
        payload = {}

        # Slack and Google Chat Webhooks
        if "https://hooks.slack.com" in url or "https://chat.googleapis.com" in url:
            payload["text"] = message
        # Discord Webhooks
        elif "https://discord.com/api/webhooks" in url:
            payload["content"] = (
                message
                if len(message) < 2000
                else f"{message[: 2000 - 20]}... (truncated)"
            )
        # Microsoft Teams Webhooks
        elif "webhook.office.com" in url:
            action = event_data.get("action", "undefined")
            facts = [
                {"name": name, "value": value}
                for name, value in json.loads(event_data.get("user", {})).items()
            ]
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "0076D7",
                "summary": message,
                "sections": [
                    {
                        "activityTitle": message,
                        "activitySubtitle": f"{name} ({VERSION}) - {action}",
                        "activityImage": WEBUI_FAVICON_URL,
                        "facts": facts,
                        "markdown": True,
                    }
                ],
            }
        # Default Payload
        else:
            payload = {**event_data}

        # Store the event
        result = webhook_events.store_webhook_event(event_id, payload, url)
        if result:
            log.debug(f"Stored webhook event {event_id} for later processing")
            return event_id
        else:
            log.error(f"Failed to store webhook event for URL: {url}")
            return ""
    except Exception as e:
        log.exception(f"Error storing webhook event: {e}")
        return ""


async def trigger_webhooks_async(
    event_type: str, message: str, event_data: dict, user_id: Optional[str] = None
) -> List[bool]:
    """
    Trigger webhooks for a specific event type asynchronously

    This function uses a fire-and-forget approach with store-and-forward for failed deliveries.
    Successful deliveries complete immediately, failed deliveries are stored for retry.

    Args:
        event_type: The webhook event type (from WebhookEvent enum)
        message: Human readable message for the event
        event_data: Data payload for the event
        user_id: Optional user ID for user-specific webhooks

    Returns:
        List of boolean results for each webhook attempted (True = immediate success or stored for retry)
    """
    if not is_valid_event(event_type):
        log.error(f"Invalid webhook event type: {event_type}")
        return []

    try:
        # Import here to avoid circular imports
        from open_webui.models.webhooks import WebhookConfigs

        db = next(get_db())
        webhook_configs = WebhookConfigs(db)

        # Get matching webhook configurations
        configs = webhook_configs.get_webhook_configs_for_event(event_type, user_id)

        if not configs:
            log.debug(f"No webhook configurations found for event: {event_type}")
            return []

        results = []

        # Add event type to event data
        enhanced_event_data = {
            **event_data,
            "event_type": event_type,
            "timestamp": event_data.get("timestamp", int(__import__("time").time())),
            "version": VERSION,
        }

        # Process all webhooks concurrently
        async def process_webhook(config):
            log.debug(f"Triggering webhook: {config.name} for event: {event_type}")

            # Try immediate delivery
            success = await post_webhook(
                name=config.name,
                url=config.url,
                message=message,
                event_data=enhanced_event_data,
            )

            if success:
                log.info(
                    f"Successfully triggered webhook '{config.name}' for event '{event_type}'"
                )
                return True
            else:
                # Store for retry on failure
                log.warning(
                    f"Immediate delivery failed for webhook '{config.name}', storing for retry"
                )
                event_id = await store_webhook_event_async(
                    url=config.url,
                    name=config.name,
                    message=message,
                    event_data=enhanced_event_data,
                )
                if event_id:
                    log.info(
                        f"Stored webhook '{config.name}' event {event_id} for retry"
                    )
                    return True  # Consider stored events as "successful" for the caller
                else:
                    log.error(f"Failed to store webhook '{config.name}' for retry")
                    return False

        # Execute all webhooks concurrently
        tasks = [process_webhook(config) for config in configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to False
        results = [result if isinstance(result, bool) else False for result in results]

        return results

    except Exception as e:
        log.exception(f"Error triggering webhooks for event {event_type}: {e}")
        return []


def trigger_webhooks(
    event_type: str, message: str, event_data: dict, user_id: Optional[str] = None
) -> List[bool]:
    """
    Trigger webhooks for a specific event type

    Args:
        event_type: The webhook event type (from WebhookEvent enum)
        message: Human readable message for the event
        event_data: Data payload for the event
        user_id: Optional user ID for user-specific webhooks

    Returns:
        List of boolean results for each webhook triggered
    """
    if not is_valid_event(event_type):
        log.error(f"Invalid webhook event type: {event_type}")
        return []

    try:
        # Import here to avoid circular imports
        from open_webui.models.webhooks import WebhookConfigs

        db = next(get_db())
        webhook_configs = WebhookConfigs(db)

        # Get matching webhook configurations
        configs = webhook_configs.get_webhook_configs_for_event(event_type, user_id)

        if not configs:
            log.debug(f"No webhook configurations found for event: {event_type}")
            return []

        results = []

        # Add event type to event data
        enhanced_event_data = {
            **event_data,
            "event_type": event_type,
            "timestamp": event_data.get("timestamp", int(__import__("time").time())),
            "version": VERSION,
        }

        for config in configs:
            log.debug(f"Triggering webhook: {config.name} for event: {event_type}")
            result = post_webhook_sync(
                name=config.name,
                url=config.url,
                message=message,
                event_data=enhanced_event_data,
            )
            results.append(result)

            if result:
                log.info(
                    f"Successfully triggered webhook '{config.name}' for event '{event_type}'"
                )
            else:
                log.error(
                    f"Failed to trigger webhook '{config.name}' for event '{event_type}'"
                )

        return results

    except Exception as e:
        log.exception(f"Error triggering webhooks for event {event_type}: {e}")
        return []


def is_webhook_migration_needed():
    """
    Lightweight check to see if webhook migration is needed
    Returns True if migration is needed, False if already completed
    """
    try:
        from open_webui.models.webhooks import WebhookConfigs
        
        db = next(get_db())
        webhook_configs = WebhookConfigs(db)
        
        # Check if any webhook configs exist - if so, migration is done
        existing_configs = webhook_configs.get_webhook_configs()
        return len(existing_configs) == 0
    except Exception as e:
        log.warning(f"Error checking webhook migration status: {e}")
        return True  # Assume migration is needed if we can't check


def migrate_legacy_webhooks():
    """
    Migrate existing webhook configurations to the new system
    This function should be called during application startup
    """
    try:
        # Early check to avoid heavy imports if migration already done
        if not is_webhook_migration_needed():
            log.info("Webhook migration already completed, skipping")
            return

        # Heavy imports only when migration is actually needed
        from open_webui.config import WEBHOOK_URL
        from open_webui.models.users import Users
        from open_webui.models.webhooks import WebhookConfigs
        import uuid

        db = next(get_db())
        webhook_configs = WebhookConfigs(db)
        users = Users(db)

        # Migrate global webhook URL if it exists
        if WEBHOOK_URL and WEBHOOK_URL.strip():
            webhook_id = str(uuid.uuid4())
            webhook_configs.insert_new_webhook_config(
                id=webhook_id,
                name="Legacy Global Webhook",
                url=WEBHOOK_URL,
                events=[
                    event.value for event in WebhookEvent
                ],  # All events for backward compatibility
                user_id=None,
                enabled=True,
            )
            log.info(f"Migrated global webhook URL to new system: {WEBHOOK_URL}")

        # Migrate user-specific webhook URLs
        all_users = users.get_users()
        for user in all_users:
            user_webhook_url = users.get_user_webhook_url_by_id(user.id)
            if user_webhook_url and user_webhook_url.strip():
                webhook_id = str(uuid.uuid4())
                webhook_configs.insert_new_webhook_config(
                    id=webhook_id,
                    name=f"Legacy Webhook - {user.name}",
                    url=user_webhook_url,
                    events=[
                        event.value for event in WebhookEvent
                    ],  # All events for backward compatibility
                    user_id=user.id,
                    enabled=True,
                )
                log.info(
                    f"Migrated user webhook URL for {user.name}: {user_webhook_url}"
                )

        log.info("Webhook migration completed successfully")

    except Exception as e:
        log.exception(f"Error during webhook migration: {e}")


async def process_webhook_retries():
    """
    Process webhook events that need to be retried
    This function should be called periodically by a background task
    """
    try:
        # Import here to avoid circular imports
        from open_webui.models.webhooks import WebhookEvents

        db = next(get_db())
        webhook_events = WebhookEvents(db)

        # Get events that are ready for retry
        events_to_retry = webhook_events.get_events_for_retry(max_tries=5)

        if not events_to_retry:
            log.debug("No webhook events ready for retry")
            return

        log.info(f"Processing {len(events_to_retry)} webhook events for retry")

        for event in events_to_retry:
            try:
                log.debug(
                    f"Retrying webhook event {event.id} (attempt {event.tries + 1})"
                )

                # Try to deliver the webhook
                async with aiohttp.ClientSession() as session:
                    async with session.post(event.url, json=event.event) as response:
                        response.raise_for_status()

                    # Success - remove the event from retry queue
                    webhook_events.delete_webhook_event(event.id)
                    log.info(
                        f"Successfully delivered webhook event {event.id} on retry"
                    )

            except Exception as e:
                log.warning(f"Retry failed for webhook event {event.id}: {e}")

                # Update the tries counter
                updated_event = webhook_events.update_webhook_event_tries(event.id)

                if updated_event and updated_event.tries >= 5:
                    # Max tries reached, remove from queue
                    webhook_events.delete_webhook_event(event.id)
                    log.error(
                        f"Max retries reached for webhook event {event.id}, removing from queue"
                    )
                else:
                    log.info(
                        f"Webhook event {event.id} will be retried again later (attempt {updated_event.tries if updated_event else 'unknown'})"
                    )

    except Exception as e:
        log.exception(f"Error processing webhook retries: {e}")


def cleanup_legacy_webhooks():
    """
    Clean up legacy webhook configurations after successful migration
    This should be called after confirming the new system is working
    """
    try:
        # This function would clean up the old webhook configurations
        # For now, we'll keep them for backward compatibility
        pass
    except Exception as e:
        log.exception(f"Error during webhook cleanup: {e}")


# Helper function for fire-and-forget webhook delivery with store-and-forward
def trigger_webhooks_fire_and_forget(
    event_type: str, message: str, event_data: dict, user_id: Optional[str] = None
):
    """
    Trigger webhooks using fire-and-forget with immediate store-and-forward for failures
    This approach stores failed webhook events immediately for later retry without blocking
    """
    if not is_valid_event(event_type):
        log.error(f"Invalid webhook event type: {event_type}")
        return []

    try:
        # Import here to avoid circular imports
        from open_webui.models.webhooks import WebhookConfigs, WebhookEvents

        db = next(get_db())
        webhook_configs = WebhookConfigs(db)
        webhook_events = WebhookEvents(db)

        # Get matching webhook configurations
        configs = webhook_configs.get_webhook_configs_for_event(event_type, user_id)

        if not configs:
            log.debug(f"No webhook configurations found for event: {event_type}")
            return []

        results = []

        # Add event type to event data
        enhanced_event_data = {
            **event_data,
            "event_type": event_type,
            "timestamp": event_data.get("timestamp", int(__import__("time").time())),
            "version": VERSION,
        }

        for config in configs:
            log.debug(f"Processing webhook: {config.name} for event: {event_type}")

            # Store event immediately for processing by background worker
            # This ensures delivery attempts even if initial attempt fails
            event_id = str(uuid.uuid4())

            # Create payload for this specific webhook
            payload = {}
            url = config.url

            # Slack and Google Chat Webhooks
            if "https://hooks.slack.com" in url or "https://chat.googleapis.com" in url:
                payload["text"] = message
            # Discord Webhooks
            elif "https://discord.com/api/webhooks" in url:
                payload["content"] = (
                    message
                    if len(message) < 2000
                    else f"{message[: 2000 - 20]}... (truncated)"
                )
            # Microsoft Teams Webhooks
            elif "webhook.office.com" in url:
                action = enhanced_event_data.get("action", "undefined")
                facts = [
                    {"name": config.name, "value": value}
                    for name, value in json.loads(
                        enhanced_event_data.get("user", "{}")
                    ).items()
                ]
                payload = {
                    "@type": "MessageCard",
                    "@context": "http://schema.org/extensions",
                    "themeColor": "0076D7",
                    "summary": message,
                    "sections": [
                        {
                            "activityTitle": message,
                            "activitySubtitle": f"{config.name} ({VERSION}) - {action}",
                            "activityImage": WEBUI_FAVICON_URL,
                            "facts": facts,
                            "markdown": True,
                        }
                    ],
                }
            # Default Payload
            else:
                payload = {**enhanced_event_data}

            # Store the event for background processing
            result = webhook_events.store_webhook_event(event_id, payload, url)
            if result:
                log.info(
                    f"Stored webhook '{config.name}' event {event_id} for background delivery"
                )
                results.append(True)
            else:
                log.error(
                    f"Failed to store webhook '{config.name}' event for background delivery"
                )
                results.append(False)

        return results

    except Exception as e:
        log.exception(f"Error storing webhooks for event {event_type}: {e}")
        return []
