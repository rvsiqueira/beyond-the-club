'use client';

import { useState, useEffect } from 'react';
import { Phone } from 'lucide-react';

interface PhoneInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

/**
 * Brazilian phone input with automatic formatting.
 *
 * Displays: (XX) XXXXX-XXXX
 * Stores: digits only (e.g., "11981491849")
 * The +55 country code is shown as a prefix but not stored.
 */
export function PhoneInput({
  value,
  onChange,
  placeholder = "(11) 98149-1849",
  className = ""
}: PhoneInputProps) {
  const [displayValue, setDisplayValue] = useState('');

  // Format: (XX) XXXXX-XXXX
  const formatPhone = (digits: string): string => {
    const cleaned = digits.replace(/\D/g, '').slice(0, 11);
    if (cleaned.length === 0) return '';
    if (cleaned.length <= 2) return `(${cleaned}`;
    if (cleaned.length <= 7) return `(${cleaned.slice(0, 2)}) ${cleaned.slice(2)}`;
    return `(${cleaned.slice(0, 2)}) ${cleaned.slice(2, 7)}-${cleaned.slice(7)}`;
  };

  // Parse formatted to digits only
  const parsePhone = (formatted: string): string => {
    return formatted.replace(/\D/g, '');
  };

  useEffect(() => {
    setDisplayValue(formatPhone(value));
  }, [value]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const digits = parsePhone(e.target.value);
    setDisplayValue(formatPhone(digits));
    onChange(digits);
  };

  return (
    <div className="relative">
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <span className="text-gray-400 text-sm font-medium">+55</span>
      </div>
      <input
        type="tel"
        value={displayValue}
        onChange={handleChange}
        placeholder={placeholder}
        className={`pl-12 pr-10 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 w-full ${className}`}
      />
      <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
        <Phone className="h-4 w-4 text-gray-400" />
      </div>
    </div>
  );
}
