// __tests__/api/chatStream.test.ts
import { POST } from '@/app/api/chat/stream/route'; // Adjust path as necessary
import { NextRequest } from 'next/server';
import { createReadableStream } from '@/lib/test-utils'; // Placeholder for test utility

// Mock Supabase getSession
jest.mock('@/lib/supabase/server', () => ({
  createSupabaseRouteHandlerClient: jest.fn().mockReturnValue({
    auth: {
      getSession: jest.fn(),
    },
  }),
}));

// Mock OpenAI
const mockCreateChatCompletion = jest.fn();
jest.mock('openai-edge', () => ({
  Configuration: jest.fn(),
  OpenAIApi: jest.fn().mockImplementation(() => ({
    createChatCompletion: mockCreateChatCompletion,
  })),
}));

// Mock Vercel AI SDK stream
jest.mock('ai', () => ({
  OpenAIStream: jest.fn((res) => res), // Pass through the response for simplicity
  StreamingTextResponse: jest.fn((stream) => new Response(stream)),
}));


describe('/api/chat/stream POST', () => {
  beforeEach(() => {
    // Reset mocks before each test
    jest.clearAllMocks();
    // Mock process.env
    process.env.OPENAI_API_KEY = 'test-api-key';
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://localhost:54321';
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'test-anon-key';
  });

  it('should return 401 if user is not authenticated', async () => {
    const { createSupabaseRouteHandlerClient } = require('@/lib/supabase/server');
    (createSupabaseRouteHandlerClient().auth.getSession as jest.Mock).mockResolvedValueOnce({ data: { session: null }, error: null });

    const req = new NextRequest('http://localhost/api/chat/stream', {
      method: 'POST',
      body: JSON.stringify({ messages: [{ role: 'user', content: 'Hello' }], model: 'gpt-3.5-turbo' }),
    });

    const response = await POST(req);
    expect(response.status).toBe(401);
  });

  it('should return a streaming response if user is authenticated and OpenAI call is successful', async () => {
    const { createSupabaseRouteHandlerClient } = require('@/lib/supabase/server');
    (createSupabaseRouteHandlerClient().auth.getSession as jest.Mock).mockResolvedValueOnce({ data: { session: { user: {id: '123'} } }, error: null });

    const mockStreamData = ["Hello", " world", "!"];
    const stream = createReadableStream(mockStreamData);

    mockCreateChatCompletion.mockResolvedValueOnce(new Response(stream));

    const req = new NextRequest('http://localhost/api/chat/stream', {
      method: 'POST',
      body: JSON.stringify({ messages: [{ role: 'user', content: 'Hello' }], model: 'gpt-3.5-turbo' }),
    });

    const response = await POST(req);
    expect(response.status).toBe(200);
    // Further checks could involve reading the stream, but that's more complex for a smoke test
    // For now, just checking status 200 and that createChatCompletion was called is a good start.
    expect(mockCreateChatCompletion).toHaveBeenCalled();
  });

  it('should return 500 if OpenAI call fails', async () => {
    const { createSupabaseRouteHandlerClient } = require('@/lib/supabase/server');
    (createSupabaseRouteHandlerClient().auth.getSession as jest.Mock).mockResolvedValueOnce({ data: { session: { user: {id: '123'} } }, error: null });

    mockCreateChatCompletion.mockRejectedValueOnce(new Error('OpenAI API Error'));

    const req = new NextRequest('http://localhost/api/chat/stream', {
        method: 'POST',
        body: JSON.stringify({ messages: [{ role: 'user', content: 'Hello' }], model: 'gpt-3.5-turbo' })
    });

    const response = await POST(req);
    expect(response.status).toBe(500);
    const jsonResponse = await response.json();
    expect(jsonResponse.error).toContain('OpenAI API Error');
  });
});
