import tiktoken

def calculate_messages_token_usage(messages, model="gpt-4"):
    """
    Calculate the token usage for a list of OpenAI-style messages.
    
    Args:
        messages (list): A list of dictionaries with 'role' and 'content'.
        model (str): The OpenAI model to use for tokenization (e.g., "gpt-3.5-turbo" or "gpt-4").
        
    Returns:
        int: The total number of tokens used.
    """
    # Load the tokenizer for the specified model
    encoding = tiktoken.encoding_for_model(model)
    
    total_tokens = 0
    
    # OpenAI chat models use some extra tokens per message and per conversation
    tokens_per_message = 3  # Every message has 3 overhead tokens (role + formatting)
    tokens_per_conversation = 2  # Every conversation has 2 extra tokens at the start
    
    for message in messages:
        # Add tokens for 'role' and 'content'
        total_tokens += tokens_per_message
        total_tokens += len(encoding.encode(message["role"]))  # Tokens for role
        total_tokens += len(encoding.encode(message["content"]))  # Tokens for content
    
    # Add conversation-wide tokens
    total_tokens += tokens_per_conversation
    
    return total_tokens


def calculate_content_token_usage(text, model="gpt-4"):
    """
    Calculate the token usage for a plain text input.
    
    Args:
        text (str): The text input to calculate token usage for.
        model (str): The OpenAI model to use for tokenization (e.g., "gpt-3.5-turbo" or "gpt-4").
        
    Returns:
        int: The number of tokens used in the text.
    """
    # Load the tokenizer for the specified model
    encoding = tiktoken.encoding_for_model(model)
    
    # Encode the text to calculate tokens
    tokens = encoding.encode(text)
    
    # Return the number of tokens
    return len(tokens)
