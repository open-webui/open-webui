import os
import requests
import logging

LAGO_API_URL = os.environ.get("LAGO_API_URL")
LAGO_API_KEY = os.environ.get("LAGO_API_KEY")

logger = logging.getLogger(__name__)

def upsert_customer(user_external_id, user_data):
    """
    Upserts a customer in Lago.
    # https://getlago.com/docs/api-reference/customers/create
    """
    if not LAGO_API_KEY:
        logger.error("LAGO_API_KEY environment variable not set.")
        raise ValueError("Lago API key is not configured.")

    api_endpoint = f"{LAGO_API_URL}/customers"
    headers = {
        "Authorization": f"Bearer {LAGO_API_KEY}",
        "Content-Type": "application/json",
    }

    # Construct the payload, mapping user_data to Lago's expected fields.
    # Ensure required fields like email, name, currency are present in user_data
    # Adjust the mapping based on the actual structure of your user_data
    payload = {
        "customer": {
            "external_id": str(user_external_id),
            "name": user_data.get("name", str(user_external_id)),
            "email": user_data.get("email"),
            "pinet_id_token": user_data.get("pinet_id_token_normal"),
            "moneta_id_token": user_data.get("moneta_id_token_normal"),
            "currency": user_data.get("currency", "USD"),  # Default currency if not provided
            "timezone": user_data.get("timezone", "UTC"),
            "country": user_data.get("region", "US"),
        }
    }

    # Remove keys with None values as Lago might not accept them
    payload["customer"] = {k: v for k, v in payload["customer"].items() if v is not None}
    import pdb; pdb.set_trace()

    try:
        response = requests.post(api_endpoint, headers=headers, json=payload, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        logger.info(f"Successfully upserted customer {user_external_id} to Lago.")
        return response.json().get("customer")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Lago API to upsert customer {user_external_id}: {e}")
        if e.response is not None:
            try:
                error_details = e.response.json()
                logger.error(f"Lago API Error details: {error_details}")
                raise Exception(f"Lago API error: {error_details}") from e
            except ValueError: # If response is not JSON
                logger.error(f"Lago API Error response text: {e.response.text}")
                raise Exception(f"Lago API error: {e.response.status_code} - {e.response.text}") from e
        else:
             raise Exception(f"Lago API request failed: {e}") from e

    except Exception as e:
        logger.error(f"An unexpected error occurred during Lago customer upsert for {user_external_id}: {e}")
        raise e