import React from 'react';

// Placeholder for Sidebar and Navbar components
const Sidebar = () => <div>Sidebar</div>;
const Navbar = () => <div>Navbar</div>;

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div>
      <Sidebar />
      <Navbar />
      <main>{children}</main>
    </div>
  );
}
