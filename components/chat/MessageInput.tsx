// components/chat/MessageInput.tsx
'use client';

import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface MessageInputProps {
  input: string;
  handleInputChange: (e: React.ChangeEvent<HTMLInputElement> | React.ChangeEvent<HTMLTextAreaElement>) => void;
  handleSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  isLoading: boolean;
  // TODO: Add props for file handling, voice input toggles etc. later
}

// Define brand colors (example, ideally these are in tailwind.config.js)
const primaryColor = '#8D05D4'; // TechSci AI Hub Primary

export default function MessageInput({ input, handleInputChange, handleSubmit, isLoading }: MessageInputProps) {
  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2 p-4 border-t border-border bg-card">
      <Input
        value={input}
        placeholder="Ask TechSci AI Hub..."
        onChange={handleInputChange}
        disabled={isLoading}
        className="flex-grow rounded-full px-4 py-2 focus:ring-2 focus:ring-primary/50"
      />
      <Button type="submit" disabled={isLoading} style={{ backgroundColor: primaryColor }} className="text-white rounded-full px-6 py-2 hover:opacity-90">
        Send
      </Button>
    </form>
  );
}
