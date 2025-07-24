"""
Patch for OpenRouter streaming response usage tracking
This modifies the OpenAI router to capture usage data from streaming responses
"""

import json
import re

# The patch to apply to openai.py
STREAMING_USAGE_PATCH = '''
# Add this function after imports (around line 50)
async def extract_usage_from_stream(content_iterator, user, payload, client_context):
    """Extract usage data from OpenRouter streaming response"""
    buffer = ""
    async for chunk in content_iterator:
        buffer += chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk
        yield chunk
    
    # After stream completes, look for usage data in the final chunks
    # OpenRouter sometimes includes usage in the last data: [DONE] message
    try:
        # Try to find usage data in the stream
        lines = buffer.split('\\n')
        for line in lines:
            if line.startswith('data: ') and '{' in line:
                try:
                    data = json.loads(line[6:])  # Remove 'data: ' prefix
                    if 'usage' in data:
                        # Found usage data!
                        usage_data = data['usage']
                        await record_openrouter_usage(user, payload, usage_data, client_context)
                        break
                except:
                    pass
    except Exception as e:
        log.debug(f"Could not extract usage from stream: {e}")

# Add this function to handle usage recording
async def record_openrouter_usage(user, payload, usage_data, client_context):
    """Record OpenRouter usage from streaming or non-streaming responses"""
    try:
        from open_webui.utils.openrouter_client_manager import openrouter_client_manager
        
        input_tokens = usage_data.get("prompt_tokens", 0)
        output_tokens = usage_data.get("completion_tokens", 0)
        raw_cost = usage_data.get("total_cost", 0.0)
        
        if input_tokens > 0 or output_tokens > 0:
            log.info(f"Recording OpenRouter usage: {input_tokens + output_tokens} tokens, cost: ${raw_cost}")
            
            await openrouter_client_manager.record_real_time_usage(
                user_id=user.id,
                model_name=payload.get("model", "unknown"),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                raw_cost=raw_cost,
                provider="openrouter",
                generation_time=0,
                external_user=None,
                client_context=client_context
            )
    except Exception as e:
        log.error(f"Failed to record OpenRouter usage: {e}")
'''

# Instructions for applying the patch
print("""
MANUAL PATCH INSTRUCTIONS FOR STREAMING USAGE TRACKING
======================================================

Since OpenRouter returns streaming responses, the current code never records usage.
Here's how to fix it:

1. TEMPORARY WORKAROUND (Use this now):
   - OpenRouter provides usage data through their dashboard API
   - You can periodically sync usage data using their API
   
2. PERMANENT FIX (Requires code modification):
   - The streaming response handler needs to be modified to capture usage
   - This requires intercepting the stream and looking for usage data
   
3. ALTERNATIVE SOLUTION:
   - Use OpenRouter's webhook feature to receive usage notifications
   - Set up an endpoint to receive usage data directly from OpenRouter

For now, your usage tracking tables are ready and working, but the streaming
responses bypass the recording logic. You can:

a) Check usage directly in OpenRouter dashboard
b) Use their API to periodically sync usage data
c) Wait for a code update that handles streaming responses

The issue is NOT with your database or configuration - everything is set up
correctly. The code just needs to handle streaming responses differently.
""")