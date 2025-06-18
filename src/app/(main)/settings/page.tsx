// src/app/(main)/settings/page.tsx
'use client'; // For client-side interactions like state for form inputs if any

// import { useState } from 'react'; // If managing form state locally
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
// TODO: Import Select, SelectTrigger, SelectContent, SelectItem for theme selection

// Define brand colors (example, ideally these are in tailwind.config.js)
const primaryColor = '#8D05D4'; // TechSci AI Hub Primary

export default function SettingsPage() {
  // const [userName, setUserName] = useState(''); // Example state for profile
  // const [theme, setTheme] = useState('system'); // Example state for theme
  // const [apiKey, setApiKey] = useState(''); // Example state for API key

  return (
    <div className="p-4 md:p-6 space-y-6">
      <h1 className="text-3xl font-bold text-foreground">Settings</h1>

      <Tabs defaultValue="profile" className="w-full">
        <TabsList className="grid w-full grid-cols-3 md:max-w-md mb-6">
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="theme">Theme</TabsTrigger>
          <TabsTrigger value="apiKeys">API Keys</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle>Profile</CardTitle>
              <CardDescription>Manage your personal information.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input id="name" placeholder="Your Name (e.g., Alex Doe)" />
                {/* TODO: Fetch and display actual user name from Supabase Auth user_metadata */}
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" placeholder="your@email.com" disabled />
                {/* TODO: Fetch and display actual user email from Supabase Auth */}
              </div>
              <Button style={{ backgroundColor: primaryColor }} className="text-white hover:opacity-90">
                Save Profile
              </Button>
               {/* TODO: Implement save profile logic (update user_metadata) */}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="theme">
          <Card>
            <CardHeader>
              <CardTitle>Theme</CardTitle>
              <CardDescription>Customize the appearance of TechSci AI Hub.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="theme-select">Select Theme</Label>
                {/* TODO: Replace with ShadCN Select component */}
                <select id="theme-select" className="w-full p-2 border rounded-md border-border bg-input">
                  <option value="system">System</option>
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                </select>
              </div>
              <p className="text-sm text-muted-foreground">
                Current theme is set to: [System]. {/* TODO: Reflect actual theme state */}
              </p>
               {/* TODO: Implement theme switching logic (e.g., using next-themes) */}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="apiKeys">
          <Card>
            <CardHeader>
              <CardTitle>API Keys</CardTitle>
              <CardDescription>
                Manage your API keys for external services (e.g., OpenAI).
                <br />
                <strong className="text-destructive">API keys are sensitive. Handle with care.</strong>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="openai-api-key">OpenAI API Key</Label>
                <Input id="openai-api-key" type="password" placeholder="sk-..." />
                {/* TODO: Implement secure storage and retrieval for API keys.
                           Consider Supabase Vault or other secure server-side solutions.
                           Displaying only partial keys or indicators of presence.
                */}
              </div>
              <Button style={{ backgroundColor: primaryColor }} className="text-white hover:opacity-90">
                Save API Key
              </Button>
              <p className="text-xs text-muted-foreground">
                Keys are stored securely and only used for server-to-server communication.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
