'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Users,
  Calendar,
  Ticket,
  Radio,
  Settings,
  LogOut,
  ChevronLeft,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUIStore } from '@/lib/store';
import { useAuth } from '@/hooks/useAuth';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Membros', href: '/members', icon: Users },
  { name: 'Disponibilidade', href: '/availability', icon: Calendar },
  { name: 'Agendamentos', href: '/bookings', icon: Ticket },
  { name: 'Monitor', href: '/monitor', icon: Radio },
];

// Beyond The Club brand colors for the divider
function BrandDivider() {
  return (
    <div className="flex h-1.5 w-full">
      <div className="flex-1 bg-[#1a2744]" />
      <div className="flex-1 bg-[#8b4d5c]" />
      <div className="flex-1 bg-[#d4876c]" />
      <div className="flex-1 bg-[#a8c4b8]" />
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const { logout } = useAuth();

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-50 flex flex-col bg-gray-900 transition-all duration-300',
        sidebarOpen ? 'w-64' : 'w-20'
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between px-4">
        <Link href="/dashboard" className="flex items-center gap-3">
          {sidebarOpen ? (
            <Image
              src="/logo.webp"
              alt="Beyond The Club"
              width={160}
              height={40}
              className="object-contain"
            />
          ) : (
            <Image
              src="/icon.png"
              alt="Beyond The Club"
              width={32}
              height={32}
              className="object-contain"
            />
          )}
        </Link>
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-800 hover:text-white"
        >
          <ChevronLeft
            className={cn(
              'h-5 w-5 transition-transform',
              !sidebarOpen && 'rotate-180'
            )}
          />
        </button>
      </div>
      {/* Brand Divider */}
      <BrandDivider />

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navigation.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              )}
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              {sidebarOpen && <span>{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-gray-800 space-y-1">
        <Link
          href="/settings"
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
        >
          <Settings className="h-5 w-5 flex-shrink-0" />
          {sidebarOpen && <span>Configuracoes</span>}
        </Link>
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
        >
          <LogOut className="h-5 w-5 flex-shrink-0" />
          {sidebarOpen && <span>Sair</span>}
        </button>
      </div>
    </aside>
  );
}
