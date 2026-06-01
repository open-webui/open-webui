import json, base64, urllib.request

# Get the file content
url = "https://api.github.com/repos/open-webui/open-webui/contents/backend/open_webui/routers/retrieval.py"
req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read())
    content = base64.b64decode(data['content']).decode()

# Find and replace the specific block
old_block = """        items = [
            {
                'id': str(uuid.uuid4()),
                'text': text,
                'vector': embeddings[idx],
                'metadata': metadatas[idx],
            }
            for idx, text in enumerate(texts)
        ]"""

new_block = """        # Filter out texts without valid embeddings (empty lists are rejected by chromadb)
        valid_items = []
        for idx, text in enumerate(texts):
            if idx < len(embeddings) and len(embeddings[idx]) > 0:
                valid_items.append({
                    'id': str(uuid.uuid4()),
                    'text': text,
                    'vector': embeddings[idx],
                    'metadata': metadatas[idx],
                })


        items = valid_items

        if not items:
            log.warning(f'No valid embeddings found, skipping vector DB insert for collection {collection_name}')
            return True"""

if old_block in content:
    content = content.replace(old_block, new_block)
    print("Found and replaced the block")
    # Save for use in push
    with open('/tmp/retrieval_fixed.py', 'w') as f:
        f.write(content)
    print("Saved to /tmp/retrieval_fixed.py")
else:
    print("ERROR: Could not find the block to replace")
    print("Searching for similar patterns...")
    import re
    pattern = r"'vector':\s*embeddings\[idx\]"
    matches = re.findall(pattern, content)
    print(f"Found {len(matches)} matches for pattern: {matches}")
