'use client';

import { useAuthStore } from '@/lib/store';
import { Select } from '@/components/ui';
import { formatPhone } from '@/lib/utils';

const sportOptions = [
  { value: 'surf', label: 'Surf' },
  { value: 'tennis', label: 'Tennis' },
];

interface HeaderProps {
  title?: string;
}

export function Header({ title }: HeaderProps) {
  const { user, sport, setSport } = useAuthStore();

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
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
  );
}
