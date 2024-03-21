import requests


def post_webhook(url: str, message: str, event_data: dict) -> bool:
    try:
        payload = {}

        if "https://hooks.slack.com" in url:
            payload["text"] = message
        elif "https://discord.com/api/webhooks" in url:
            payload["content"] = message
        else:
            payload = {**event_data}

        r = requests.post(url, json=payload)
        r.raise_for_status()
        return True
    except Exception as e:
        print(e)
        return False
