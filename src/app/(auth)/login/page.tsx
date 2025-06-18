// TODO: Implement full UI and logic for Magic Link and OAuth (e.g., Google/GitHub) login
'use client'; // Required for Supabase client-side auth helpers & form interactions

import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';
import { useState } from 'react';
import { useRouter } from 'next/navigation'; // Use next/navigation for App Router

export default function LoginPage() {
  const supabase = createClientComponentClient();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');

  const handleMagicLinkSignIn = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMessage('');
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/api/auth/callback`, // Or your main app page after callback
      },
    });
    if (error) {
      setMessage(`Error: ${error.message}`);
    } else {
      setMessage('Check your email for the magic link!');
    }
  };

  const handleOAuthSignIn = async (provider: 'google' | 'github') => {
    setMessage('');
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/api/auth/callback`,
      },
    });
    if (error) {
      setMessage(`Error: ${error.message}`);
    }
  };

  return (
    <div>
      <h1>Login to TechSci AI Hub</h1>
      <form onSubmit={handleMagicLinkSignIn}>
        <label htmlFor="email">Email:</label>
        <input
          type="email"
          id="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <button type="submit">Sign in with Magic Link</button>
      </form>
      <hr />
      <button onClick={() => handleOAuthSignIn('google')}>Sign in with Google</button>
      <button onClick={() => handleOAuthSignIn('github')}>Sign in with GitHub</button>
      {message && <p>{message}</p>}
      {/* TODO: Add proper styling with ShadCN UI components and Tailwind CSS */}
    </div>
  );
}
