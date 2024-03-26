import json

import requests
from config import VERSION


def post_webhook(url: str, message: str, event_data: dict) -> bool:
    try:
        payload = {}

        if "https://hooks.slack.com" in url:
            payload["text"] = message
        elif "https://discord.com/api/webhooks" in url:
            payload["content"] = message
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
                        "activitySubtitle": f"Open WebUI ({VERSION}) - {action}",
                        "activityImage": "https://openwebui.com/favicon.png",
                        "facts": facts,
                        "markdown": True,
                    }
                ],
            }
        else:
            payload = {**event_data}

        r = requests.post(url, json=payload)
        r.raise_for_status()
        return True
    except Exception as e:
        print(e)
        return False
