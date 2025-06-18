// src/app/(main)/usage/page.tsx
'use client'; // For client-side chart rendering

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

// Mock data for daily token usage
const mockDailyUsageData = [
  { date: '2024-07-01', tokens: 4500 },
  { date: '2024-07-02', tokens: 5200 },
  { date: '2024-07-03', tokens: 3800 },
  { date: '2024-07-04', tokens: 6100 },
  { date: '2024-07-05', tokens: 4900 },
  { date: '2024-07-06', tokens: 7500 },
  { date: '2024-07-07', tokens: 5300 },
];

// Define brand colors (example, ideally these are in tailwind.config.js)
const primaryColor = '#8D05D4'; // TechSci AI Hub Primary

export default function UsagePage() {
  return (
    <div className="p-4 md:p-6 space-y-6">
      <h1 className="text-3xl font-bold text-foreground">Usage Statistics</h1>

      <Card>
        <CardHeader>
          <CardTitle>Daily Token Usage</CardTitle>
          <CardDescription>
            Overview of your estimated token consumption per day.
            {/* TODO: Replace with actual data fetching and more accurate descriptions */}
          </CardDescription>
        </CardHeader>
        <CardContent className="h-[400px] w-full"> {/* Set a height for the chart container */}
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={mockDailyUsageData}
              margin={{
                top: 5,
                right: 30,
                left: 20,
                bottom: 5,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" />
              <YAxis stroke="hsl(var(--muted-foreground))" />
              <Tooltip
                contentStyle={{
                    backgroundColor: 'hsl(var(--background))',
                    borderColor: 'hsl(var(--border))',
                    borderRadius: '0.5rem',
                }}
              />
              <Legend wrapperStyle={{ color: 'hsl(var(--foreground))' }} />
              <Bar dataKey="tokens" fill={primaryColor} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* TODO: Add more charts or usage metrics as needed (e.g., model usage, feature usage) */}
      <p className="text-sm text-muted-foreground text-center">
        Usage data is illustrative. Actual data fetching and detailed breakdowns will be implemented.
      </p>
    </div>
  );
}
