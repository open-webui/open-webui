#!/usr/bin/env python3
"""
JIRA Search Examples using Open WebUI API
This script demonstrates how to search for JIRA issues without manual confirmation steps.
"""

from py_client import (
    chat_completion_streaming, 
    create_new_chat,
    update_chat
)

def search_jira_streaming(query, chat_id=None):
    """Search JIRA issues with streaming response and auto-confirmation"""
    # Create new chat if no chat_id provided
    if not chat_id:
        new_chat = create_new_chat("JIRA Search Streaming")
        chat_id = new_chat["id"]
    
    # Initial message to the agent
    messages = [
        {"role": "user", "content": query}
    ]
    
    print("🔍 Sending initial query...")
    
    # Get streaming response for initial query
    response_content = ""
    for chunk in chat_completion_streaming("uat-cgce-qa-agent-gpt-5", messages):
        if "choices" in chunk and chunk["choices"]:
            delta = chunk["choices"][0].get("delta", {})
            if "content" in delta:
                content = delta["content"]
                response_content += content
                print(content, end="", flush=True)
    
    print("\n")
    
    # Check if confirmation is needed
    if "yes to proceed" in response_content.lower() or "please answer with 'yes'" in response_content.lower():
        print("🤖 Agent requesting confirmation - automatically responding 'yes'...")
        
        # Add the assistant's response and user's "yes" to messages
        messages.append({"role": "assistant", "content": response_content})
        messages.append({"role": "user", "content": "Yes, go ahead."})
        
        # Update chat with conversation
        update_chat(chat_id, messages=messages)
        
        print("📊 Getting JIRA search results...")
        
        # Get final streaming response
        final_response = ""
        for chunk in chat_completion_streaming("uat-cgce-qa-agent-gpt-5", messages):
            if "choices" in chunk and chunk["choices"]:
                delta = chunk["choices"][0].get("delta", {})
                if "content" in delta:
                    content = delta["content"]
                    final_response += content
                    print(content, end="", flush=True)
        
        print("\n")
        
        return {
            "chat_id": chat_id,
            "full_response": final_response,
            "conversation": messages
        }
    else:
        # Direct response
        return {
            "chat_id": chat_id,
            "full_response": response_content,
            "conversation": messages
        }


def example_streaming_search():
    """Example : Streaming JIRA search with real-time output"""
    print("\n🌊 Example : Streaming JIRA Search")
    print("-" * 40)
    
    query = "Search for high priority JIRA issues in Krackan project that are affecting production"
    result = search_jira_streaming(query)
    
    print(f"\n✅ Completed streaming search. Chat ID: {result['chat_id']}")
    return result['chat_id']


def main():
    """Run all examples"""
    print("🚀 Starting JIRA Search Examples with automatically responding yes")
    print("=" * 50)
    
    try:
        # Run all examples
        chat_id_1 = example_streaming_search()
        
        print("\n🎉 All examples completed successfully!")
        
        # Example of how to continue a conversation
        print("\n💬 You can continue any conversation by using the chat_id with update_chat()")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")

if __name__ == "__main__":
    main()