import requests
from typing import Optional
import logging


class DecryptionError(Exception):
    pass


def decrypt_file_via_azure(
    file_name: str, file_bytes: bytes, endpoint: str, api_key: str, timeout: int = 30
) -> bytes:
    """
    Decrypts a file using the Azure function.

    Args:
        file_bytes: The encrypted file content as bytes.
        endpoint: The Azure function endpoint URL.
        api_key: The access key for authentication.
        timeout: Timeout in seconds for the request.

    Returns:
        Decrypted file content as bytes.

    Raises:
        DecryptionError: If decryption fails or the response is invalid.
    """
    headers = {
        "x-functions-key": api_key,
    }
    files = {
        "file": (file_name, file_bytes),
    }
    try:
        response = requests.post(
            endpoint,
            headers=headers,
            files=files,
            timeout=timeout,
        )
        # If the response is an error, capture the error message (plain text or JSON)
        if response.status_code >= 400:
            content_type = response.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                try:
                    error = response.json()
                except Exception as e:
                    logging.error(
                        f"Invalid JSON error response from Azure function: {e}"
                    )
                    raise DecryptionError(
                        "Invalid error response format from Azure function"
                    )
                raise DecryptionError(error.get("detail") or str(error))
            else:
                # Assume plain text error
                error_text = response.text.strip()
                logging.error(
                    f"Azure function returned error (plain text): {error_text}"
                )
                raise DecryptionError(error_text or "Unknown error from Azure function")
        if not response.content or len(response.content) == 0:
            logging.error("Decryption succeeded but returned empty content")
            raise DecryptionError("Decryption succeeded but returned empty content")
        # Optional: check for file corruption (e.g., by magic bytes or format validation)
        # This is a placeholder for actual validation logic
        # if not is_valid_file(response.content):
        #     logging.error("Decrypted file appears corrupted or invalid format")
        #     raise DecryptionError("Decrypted file appears corrupted or invalid format")
        return response.content
    except requests.Timeout:
        logging.error("Decryption request timed out")
        raise DecryptionError("Decryption request timed out (network timeout)")
    except requests.RequestException as e:
        logging.error(f"Decryption request failed: {e}")
        raise DecryptionError(
            f"Decryption request failed (network or authentication error): {e}"
        )
    except DecryptionError as e:
        # Already logged above
        raise
    except Exception as e:
        logging.error(f"Unexpected error during decryption: {e}")
        raise DecryptionError(f"Unexpected error during decryption: {e}")
