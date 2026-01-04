'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, X, LayoutDashboard, Users, Calendar, Ticket, Radio, Settings, LogOut } from 'lucide-react';
import { useAuthStore, useUIStore } from '@/lib/store';
import { Select } from '@/components/ui';
import { formatPhone, cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';

const sportOptions = [
  { value: 'surf', label: 'Surf' },
  { value: 'tennis', label: 'Tennis' },
];

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

interface HeaderProps {
  title?: string;
}

export function Header({ title }: HeaderProps) {
  const pathname = usePathname();
  const { user, sport, setSport } = useAuthStore();
  const { mobileMenuOpen, toggleMobileMenu, setMobileMenuOpen } = useUIStore();
  const { logout } = useAuth();

  const handleNavClick = () => {
    setMobileMenuOpen(false);
  };

  return (
    <div className="bg-white lg:border-b lg:border-gray-200">
      {/* Mobile Header with hamburger and logo */}
      <div className="lg:hidden bg-gray-900">
        <div className="h-14 flex items-center justify-between px-4">
          {/* Hamburger menu button */}
          <button
            onClick={toggleMobileMenu}
            className="p-2 -ml-2 rounded-lg text-gray-400 hover:bg-gray-800 hover:text-white"
            aria-label={mobileMenuOpen ? 'Fechar menu' : 'Abrir menu'}
          >
            {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>

          {/* Centered logo */}
          <Link href="/dashboard" className="flex items-center">
            <Image
              src="/logo.webp"
              alt="Beyond The Club"
              width={140}
              height={35}
              className="object-contain"
            />
          </Link>

          {/* Spacer for centering */}
          <div className="w-10" />
        </div>
        {/* Brand Divider */}
        <BrandDivider />

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="bg-gray-900 border-t border-gray-800">
            {/* User info and Sport selector */}
            {user && (
              <div className="px-4 py-4 border-b border-gray-800">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                    <span className="text-primary-600 font-medium">
                      {user.name?.[0] || user.phone[0]}
                    </span>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">
                      {user.name || 'Usuario'}
                    </p>
                    <p className="text-xs text-gray-400">{formatPhone(user.phone)}</p>
                  </div>
                </div>
                <Select
                  value={sport}
                  onChange={(e) => setSport(e.target.value)}
                  options={sportOptions}
                  className="w-full bg-gray-800 border-gray-700 text-white"
                />
              </div>
            )}

            {/* Navigation */}
            <nav className="px-3 py-3 space-y-1">
              {navigation.map((item) => {
                const isActive = pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={handleNavClick}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-primary-600 text-white'
                        : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                    )}
                  >
                    <item.icon className="h-5 w-5 flex-shrink-0" />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </nav>

            {/* Footer */}
            <div className="px-3 py-3 border-t border-gray-800 space-y-1">
              <Link
                href="/settings"
                onClick={handleNavClick}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
              >
                <Settings className="h-5 w-5 flex-shrink-0" />
                <span>Configuracoes</span>
              </Link>
              <button
                onClick={() => {
                  handleNavClick();
                  logout();
                }}
                className="flex w-full items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
              >
                <LogOut className="h-5 w-5 flex-shrink-0" />
                <span>Sair</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Desktop Header */}
      <header className="h-16 hidden lg:flex items-center justify-between px-6">
        <div>
          {title && <h1 className="text-xl font-semibold text-gray-900">{title}</h1>}
        </div>

        <div className="flex items-center gap-4">
          <Select
            value={sport}
            onChange={(e) => setSport(e.target.value)}
            options={sportOptions}
            className="w-32"
          />

          {user && (
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                <span className="text-primary-600 font-medium text-sm">
                  {user.name?.[0] || user.phone[0]}
                </span>
              </div>
              <div className="hidden sm:block">
                <p className="text-sm font-medium text-gray-900">
                  {user.name || 'Usuario'}
                </p>
                <p className="text-xs text-gray-500">{formatPhone(user.phone)}</p>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Mobile page title */}
      {title && !mobileMenuOpen && (
        <div className="lg:hidden px-4 py-3 bg-gray-50">
          <h1 className="text-lg font-semibold text-gray-900">{title}</h1>
        </div>
      )}
    </div>
  );
}
