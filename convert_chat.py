import json
import os

def convert_to_txt(chat_data):
    chat = chat_data.get('chat', chat_data)
    history = chat.get('history', {})
    msgs_dict = history.get('messages', {})
    
    if not msgs_dict:
        return ""

    # Sort messages by timestamp to ensure chronological order
    # If timestamp is missing, use 0
    messages = list(msgs_dict.values())
    messages.sort(key=lambda x: x.get('timestamp', 0))
    
    chat_text = ""
    count = 0
    for message in messages:
        role = str(message.get('role', 'UNKNOWN')).upper()
        content = message.get('content', '')
        if content: # Only export messages with content
            chat_text += f"### {role}\n{content}\n\n"
            count += 1
    
    print(f"Processed {count} messages for chat: {chat.get('title', 'Untitled')}")
    return chat_text.strip()

input_path = r"C:\Users\Ulrich\Downloads\chat-export-1768230300470.json"
output_path = r"C:\Users\Ulrich\Downloads\chat-export-1768230300470.txt"

try:
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, list):
        results = []
        for chat_obj in data:
            results.append(convert_to_txt(chat_obj))
        final_text = "\n\n" + "="*50 + "\n\n".join(results)
    else:
        final_text = convert_to_txt(data)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_text)
    
    print(f"\nFinal export successful: {output_path}")

except Exception as e:
    print(f"Error: {e}")
