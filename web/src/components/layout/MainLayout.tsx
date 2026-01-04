'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { useUIStore } from '@/lib/store';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';

interface MainLayoutProps {
  children: React.ReactNode;
  title?: string;
}

export function MainLayout({ children, title }: MainLayoutProps) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const sidebarOpen = useUIStore((state) => state.sidebarOpen);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Sidebar />
      {/* Main content area */}
      <div
        className={cn(
          'transition-all duration-300',
          // Desktop: margin based on sidebar state
          'lg:ml-64',
          !sidebarOpen && 'lg:ml-20',
          // Mobile: no margin (sidebar is overlay)
          'ml-0'
        )}
      >
        <Header title={title} />
        <main className="p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
