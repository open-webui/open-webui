// components/layout/Sidebar.tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
// TODO: Import actual icons from a library like lucide-react
// import { MessageSquare, Clock, Settings, BarChart3 } from 'lucide-react';
// import { Button } from '@/components/ui/button'; // If using buttons for nav items

// Define brand colors (example, ideally these are in tailwind.config.js)
const primaryColor = '#8D05D4'; // TechSci AI Hub Primary
const secondaryColor = '#2D3081'; // TechSci AI Hub Secondary

const navItems = [
  { href: '/chat', label: 'Chat', icon: '💬' /* Replace with actual icon component */ },
  { href: '/history', label: 'History', icon: '📜' /* Replace with actual icon component */ },
  { href: '/usage', label: 'Usage', icon: '📊' /* Replace with actual icon component */ },
  { href: '/settings', label: 'Settings', icon: '⚙️' /* Replace with actual icon component */ },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 h-screen p-4 md:p-6 space-y-4 border-r border-border bg-card text-card-foreground fixed top-0 left-0">
      <div className="flex items-center justify-center mb-8">
        {/* TODO: Replace with TechSci AI Hub Logo */}
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-xl"
          style={{ backgroundColor: primaryColor }}
        >
          TS
        </div>
        <h1 className="ml-3 text-2xl font-bold" style={{ color: primaryColor }}>TechSci AI Hub</h1>
      </div>
      <nav className="space-y-2">
        {navItems.map((item) => (
          <Link
            key={item.label}
            href={item.href}
            className={`flex items-center space-x-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors
                                ${pathname === item.href || (item.href !== '/chat' && pathname.startsWith(item.href))
                                  ? 'text-white'
                                  : 'text-muted-foreground hover:text-foreground'}
                                ${pathname === item.href ? 'bg-primary' : 'hover:bg-muted'}`}
            style={pathname === item.href ? { backgroundColor: primaryColor } : {}}
          >
            {/* <item.icon className="w-5 h-5" /> */}
            <span className="text-2xl mr-2">{item.icon}</span> {/* Placeholder for icon components */}
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
      {/* Optional: Add user profile section or other elements at the bottom */}
    </aside>
  );
}
