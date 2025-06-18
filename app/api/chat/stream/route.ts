// app/api/chat/stream/route.ts
import { Configuration, OpenAIApi } from 'openai-edge';
import { OpenAIStream, StreamingTextResponse } from 'ai';
import { createSupabaseRouteHandlerClient } from '@/lib/supabase/server'; // Assuming @ is mapped to src/
import { cookies } from 'next/headers';

// IMPORTANT: Set the runtime to edge
export const runtime = 'edge';

// Configure OpenAI API client
// Ensure your OPENAI_API_KEY is set in your environment variables
const config = new Configuration({
  apiKey: process.env.OPENAI_API_KEY,
});
const openai = new OpenAIApi(config);

export async function POST(req: Request) {
  try {
    const cookieStore = cookies();
    // Note: The createSupabaseRouteHandlerClient in this project's server.ts
    // was updated to NOT require cookieStore as an argument, as it calls cookies() internally.
    // If you have a version that requires cookieStore, you'd pass it:
    // const supabase = createSupabaseRouteHandlerClient({ cookies: () => cookieStore });
    // For this project's current server.ts, it should be:
    const supabase = createSupabaseRouteHandlerClient();


    const { data: { session } } = await supabase.auth.getSession();

    if (!session) {
      return new Response('Unauthorized', { status: 401 });
    }

    const { messages, model: modelId } = await req.json();

    // TODO: Potentially fetch model-specific settings (e.g., system prompt, parameters) from Supabase
    // using modelId and user session, and apply RLS.
    // For MVP, we'll use a default or pass everything from client.

    // Ask OpenAI for a streaming chat completion
    const response = await openai.createChatCompletion({
      model: modelId || 'gpt-3.5-turbo', // Default to gpt-3.5-turbo if no model provided
      stream: true,
      messages: messages,
      // TODO: Add other parameters like temperature, max_tokens etc. if needed
    });

    // Convert the response into a friendly text-stream
    const stream = OpenAIStream(response);

    // Respond with the stream
    return new StreamingTextResponse(stream);
  } catch (error: any) {
    console.error('Error in chat stream route:', error);
    // Ensure a Response object is returned in case of error
    const errorMessage = error.message || 'An unexpected error occurred';
    const errorStatus = error.status || 500;
    return new Response(JSON.stringify({ error: errorMessage }), { status: errorStatus });
  }
}
