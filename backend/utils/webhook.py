import requests


def post_webhook(url: str, json: dict) -> bool:
    try:
        r = requests.post(url, json=json)
        r.raise_for_status()
        return True
    except Exception as e:
        print(e)
        return False
