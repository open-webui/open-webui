import requests  
import json  
  
# Configuration  
BASE_URL = "https://cepm.amd.com:3443"  # Replace with your Open WebUI instance  
API_KEY = "sk-52c....."    # Your API key  
  
# Headers for all requests  
headers = {  
    "Accept": "application/json",  
    "Content-Type": "application/json",  
    "Authorization": f"Bearer {API_KEY}"  
}

def get_api_key(jwt_token):  
    """Get user's API key using JWT token"""  
    response = requests.get(
        f"{BASE_URL}/api/v1/auths/api_key",
        headers={"Authorization": f"Bearer {jwt_token}"},
        verify=False
    )
    if response.status_code == 200:  
        return response.json()["api_key"]  
    else:  
        raise Exception(f"Failed to get API key: {response.text}")

def get_all_chats():
    """Get all chats for the authenticated user"""
    response = requests.get(f"{BASE_URL}/api/v1/chats/", headers=headers, verify=False)
    response.raise_for_status()  
    return response.json()  
  
def get_chat_by_id(chat_id):
    """Get specific chat by ID"""
    response = requests.get(f"{BASE_URL}/api/v1/chats/{chat_id}", headers=headers, verify=False)
    response.raise_for_status()  
    return response.json()  
  
def create_new_chat(title="New Chat", messages=None, folder_id=None):  
    """Create a new chat"""  
    if messages is None:  
        messages = []  
      
    data = {  
        "chat": {  
            "title": title,  
            "messages": messages  
        },  
        "folder_id": folder_id  
    }  
      
    response = requests.post(  
        f"{BASE_URL}/api/v1/chats/new",
        headers=headers,
        json=data,
        verify=False
    )
    response.raise_for_status()  
    return response.json()  
  
def update_chat(chat_id, title=None, messages=None):  
    """Update an existing chat"""  
    data = {"chat": {}}  
    if title:  
        data["chat"]["title"] = title  
    if messages:  
        data["chat"]["messages"] = messages  
      
    response = requests.post(  
        f"{BASE_URL}/api/v1/chats/{chat_id}",
        headers=headers,
        json=data,
        verify=False
    )
    response.raise_for_status()  
    return response.json()

def chat_completion(model, messages, stream=False):  
    """Send chat completion request"""  
    data = {  
        "model": model,  
        "messages": messages,  
        "stream": stream  
    }  
      
    response = requests.post(  
        f"{BASE_URL}/api/chat/completions",
        headers=headers,
        json=data,
        stream=stream,
        verify=False
    )
    response.raise_for_status()  
      
    if stream:  
        return response  # Return response object for streaming  
    else:  
        return response.json()  
  
def chat_completion_streaming(model, messages):  
    """Handle streaming chat completion"""  
    response = chat_completion(model, messages, stream=True)  
      
    for line in response.iter_lines():  
        if line:  
            line = line.decode('utf-8')  
            if line.startswith('data: '):  
                data = line[6:]  # Remove 'data: ' prefix  
                if data.strip() == '[DONE]':  
                    break  
                try:  
                    chunk = json.loads(data)  
                    yield chunk  
                except json.JSONDecodeError:  
                    continue

def main():  
    try:  
        # Get all chats  
        #chats = get_all_chats()  
        #print(f"Found {len(chats)} chats")  
          
        # Create a new chat  
        new_chat = create_new_chat("Python API Sample Code")  
        chat_id = new_chat["id"]  
        print(f"Created chat: {chat_id}")  
          
        # Send a chat completion  
        messages = [  
            {"role": "user", "content": "Hello! How are you?"}  
        ]  
          
        completion = chat_completion("uat-cgce-qa-agent-gpt-5", messages)  
        print("Response:", completion)  
          
        # Example with streaming  
        print("\nStreaming response:")  
        for chunk in chat_completion_streaming("uat-cgce-qa-agent-gpt-5", messages):  
            if "choices" in chunk and chunk["choices"]:  
                delta = chunk["choices"][0].get("delta", {})  
                if "content" in delta:  
                    print(delta["content"], end="", flush=True)  
        print()  
          
    except requests.exceptions.RequestException as e:  
        print(f"API request failed: {e}")  
    except Exception as e:  
        print(f"Error: {e}")  
  
if __name__ == "__main__":  
    main()
