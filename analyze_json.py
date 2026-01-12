import json

input_path = r"C:\Users\Ulrich\Downloads\chat-export-1768230300470.json"

try:
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    chat_obj = data[0] if isinstance(data, list) else data
    chat = chat_obj.get('chat', {})
    history = chat.get('history', {})
    messages = history.get('messages', {})
    current_id = history.get('currentId')
    
    print(f"Total messages in dictionary: {len(messages)}")
    print(f"Current ID: {current_id}")
    
    if current_id in messages:
        curr_msg = messages[current_id]
        print(f"Current message parentId: {curr_msg.get('parentId')}")
    else:
        print("CRITICAL: Current ID not found in messages dictionary!")

    # Check how many messages have a parentId
    has_parent = [m_id for m_id, m in messages.items() if m.get('parentId')]
    print(f"Messages with parentId: {len(has_parent)}")
    
    # Check for orphan messages (no parent and not the starting message)
    # Usually, only one message (the root) should have no parent.
    no_parent = [m_id for m_id, m in messages.items() if not m.get('parentId')]
    print(f"Messages with NO parentId: {len(no_parent)}")
    
    # Check if childrenIds are populated
    has_children = [m_id for m_id, m in messages.items() if m.get('childrenIds')]
    print(f"Messages with childrenIds: {len(has_children)}")

    # Let's look at a few messages
    sample_ids = list(messages.keys())[:5]
    for sid in sample_ids:
        m = messages[sid]
        print(f"ID: {sid[:8]}... | Parent: {str(m.get('parentId'))[:8]}... | Children: {len(m.get('childrenIds', []))}")

except Exception as e:
    print(f"Error: {e}")
