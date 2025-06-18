// src/app/(main)/chat/page.tsx
'use client';

import { useChat } from 'ai/react';
import { ScrollArea } from '@/components/ui/scroll-area'; // Assuming ShadCN setup
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'; // Assuming ShadCN setup
import { Card, CardHeader, CardTitle } from '@/components/ui/card'; // Assuming ShadCN setup
import MessageInput from '@/components/chat/MessageInput'; // Import the new component
import { useEffect, useRef } from 'react';

export default function ChatPage() {
  const { messages, input, handleInputChange, handleSubmit, isLoading, error } = useChat({
    api: '/api/chat/stream',
    // Optional: send initial messages, headers, body, etc.
    // initialMessages: [{ id: '0', role: 'system', content: 'You are a helpful assistant.' }],
    // onResponse: (response) => {},
    // onFinish: (message) => {},
    // onError: (error) => {},
  });

  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom effect
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Define brand colors (example, ideally these are in tailwind.config.js)
  const primaryColor = '#8D05D4'; // TechSci AI Hub Primary
  // const secondaryColor = '#2D3081'; // TechSci AI Hub Secondary - Not used in this component currently
  const userMessageBg = 'bg-slate-200 dark:bg-slate-700';
  const assistantMessageBg = 'bg-purple-100 dark:bg-purple-900 border-purple-300 dark:border-purple-700';


  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    handleSubmit(e, { /* options if needed */ });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] p-4 md:p-6 bg-background text-foreground">
      <Card className="flex flex-col flex-grow overflow-hidden border-border">
        <CardHeader className="p-4 border-b border-border">
          <CardTitle className="text-xl font-semibold" style={{ color: primaryColor }}>TechSci AI Hub Chat</CardTitle>
        </CardHeader>
        <ScrollArea className="flex-grow p-4" ref={scrollAreaRef}>
          {messages.length > 0
            ? messages.map(m => (
                <div key={m.id} className={`flex items-start gap-3 mb-4 p-3 rounded-lg shadow-sm ${m.role === 'user' ? userMessageBg : assistantMessageBg}`}>
                  <Avatar className="w-8 h-8">
                    <AvatarImage src={m.role === 'user' ? '/user-avatar.png' : '/assistant-avatar.png'} alt={m.role} />
                    <AvatarFallback>{m.role === 'user' ? 'U' : 'AI'}</AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <p className="font-semibold text-sm">{m.role === 'user' ? 'You' : 'TechSci AI Hub'}</p>
                    <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                  </div>
                </div>
              ))
            : <div className="flex items-center justify-center h-full"><p className="text-muted-foreground">No messages yet. Start by typing below!</p></div>}
          <div ref={messagesEndRef} />
          {isLoading && messages.length > 0 && messages[messages.length -1].role === 'user' && (
            <div className={`flex items-start gap-3 mb-4 p-3 rounded-lg shadow-sm ${assistantMessageBg}`}>
               <Avatar className="w-8 h-8">
                 <AvatarImage src="/assistant-avatar.png" alt="assistant" />
                 <AvatarFallback>AI</AvatarFallback>
               </Avatar>
               <p className="text-sm text-muted-foreground">Thinking...</p>
            </div>
          )}
        </ScrollArea>
        {error && <p className="p-4 text-sm text-red-500 border-t border-border">Error: {error.message}</p>}

        {/* Use the new MessageInput component */}
        <MessageInput
          input={input}
          handleInputChange={handleInputChange}
          handleSubmit={onSubmit}
          isLoading={isLoading}
        />
      </Card>
      <p className="text-xs text-center text-muted-foreground mt-2">
        Chat MVP for TechSci AI Hub. UI powered by ShadCN & TailwindCSS.
      </p>
    </div>
  );
}
