from pathlib import Path
import hashlib
import re
from datetime import timedelta
from typing import Optional


def get_gravatar_url(email):
    # Trim leading and trailing whitespace from
    # an email address and force all characters
    # to lower case
    address = str(email).strip().lower()

    # Create a SHA256 hash of the final string
    hash_object = hashlib.sha256(address.encode())
    hash_hex = hash_object.hexdigest()

    # Grab the actual image URL
    return f"https://www.gravatar.com/avatar/{hash_hex}?d=mp"


def calculate_sha256(file):
    sha256 = hashlib.sha256()
    # Read the file in chunks to efficiently handle large files
    for chunk in iter(lambda: file.read(8192), b""):
        sha256.update(chunk)
    return sha256.hexdigest()


def calculate_sha256_string(string):
    # Create a new SHA-256 hash object
    sha256_hash = hashlib.sha256()
    # Update the hash object with the bytes of the input string
    sha256_hash.update(string.encode("utf-8"))
    # Get the hexadecimal representation of the hash
    hashed_string = sha256_hash.hexdigest()
    return hashed_string


def validate_email_format(email: str) -> bool:
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False
    return True


def sanitize_filename(file_name):
    # Convert to lowercase
    lower_case_file_name = file_name.lower()

    # Remove special characters using regular expression
    sanitized_file_name = re.sub(r"[^\w\s]", "", lower_case_file_name)

    # Replace spaces with dashes
    final_file_name = re.sub(r"\s+", "-", sanitized_file_name)

    return final_file_name


def extract_folders_after_data_docs(path):
    # Convert the path to a Path object if it's not already
    path = Path(path)

    # Extract parts of the path
    parts = path.parts

    # Find the index of '/data/docs' in the path
    try:
        index_data_docs = parts.index("data") + 1
        index_docs = parts.index("docs", index_data_docs) + 1
    except ValueError:
        return []

    # Exclude the filename and accumulate folder names
    tags = []

    folders = parts[index_docs:-1]
    for idx, part in enumerate(folders):
        tags.append("/".join(folders[: idx + 1]))

    return tags


def parse_duration(duration: str) -> Optional[timedelta]:
    if duration == "-1" or duration == "0":
        return None

    # Regular expression to find number and unit pairs
    pattern = r"(-?\d+(\.\d+)?)(ms|s|m|h|d|w)"
    matches = re.findall(pattern, duration)

    if not matches:
        raise ValueError("Invalid duration string")

    total_duration = timedelta()

    for number, _, unit in matches:
        number = float(number)
        if unit == "ms":
            total_duration += timedelta(milliseconds=number)
        elif unit == "s":
            total_duration += timedelta(seconds=number)
        elif unit == "m":
            total_duration += timedelta(minutes=number)
        elif unit == "h":
            total_duration += timedelta(hours=number)
        elif unit == "d":
            total_duration += timedelta(days=number)
        elif unit == "w":
            total_duration += timedelta(weeks=number)

    return total_duration
