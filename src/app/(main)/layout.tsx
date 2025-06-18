// src/app/(main)/layout.tsx
import Sidebar from '@/components/layout/Sidebar'; // Assuming @ is mapped to src/
// TODO: Create and import Navbar component for top navigation if needed

export default function MainAppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen bg-background text-foreground">
      <Sidebar />
      <main className="flex-1 ml-64 overflow-y-auto">
        {/* TODO: Add a Navbar here if design requires it */}
        {/* <Navbar /> */}
        <div className="p-0">{/* Page content will be rendered here, remove padding if pages handle it */}
          {children}
        </div>
      </main>
    </div>
  );
}
