import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string): string {
  // Parse date string as local time (not UTC) to avoid timezone shift
  // Input format: "YYYY-MM-DD"
  const [year, month, day] = date.split('-').map(Number);
  const localDate = new Date(year, month - 1, day); // month is 0-indexed

  const dayMonth = localDate.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
  });
  const weekday = localDate.toLocaleDateString('pt-BR', {
    weekday: 'long',
  });

  return `${dayMonth} (${weekday})`;
}

export function formatDateBR(date: string): string {
  // Convert YYYY-MM-DD to dd/mm/yyyy
  if (!date) return '';
  const [year, month, day] = date.split('-');
  return `${day}/${month}/${year}`;
}

export function formatPhone(phone: string): string {
  const cleaned = phone.replace(/\D/g, '');
  if (cleaned.length === 11) {
    return `(${cleaned.slice(0, 2)}) ${cleaned.slice(2, 7)}-${cleaned.slice(7)}`;
  }
  return phone;
}

export function getTodayDate(): string {
  const today = new Date();
  return today.toISOString().split('T')[0];
}

export function getDateDaysFromNow(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().split('T')[0];
}

export function formatLevel(level?: string): string {
  if (!level) return '';
  return level
    .replace('Iniciante', 'Iniciante ')
    .replace('Intermediario', 'Intermediário ')
    .replace('Avançado', 'Avançado ')
    .trim();
}

export function formatWaveSide(waveSide?: string): string {
  if (!waveSide) return '';
  return waveSide
    .replace('Lado_', '')
    .replace('esquerdo', 'Esquerdo')
    .replace('direito', 'Direito');
}
