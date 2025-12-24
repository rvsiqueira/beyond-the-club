/**
 * Utility functions for the Beyond The Club web app.
 */

/**
 * Format a date string (YYYY-MM-DD) for display.
 * Returns format: "Sex, 27 Dez"
 */
export function formatDate(dateStr: string): string {
  const date = new Date(dateStr + 'T12:00:00'); // Use noon to avoid timezone issues

  const weekdays = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab'];
  const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

  const weekday = weekdays[date.getDay()];
  const day = date.getDate();
  const month = months[date.getMonth()];

  return `${weekday}, ${day} ${month}`;
}

/**
 * Format a date string for form display (DD/MM/YYYY).
 */
export function formatDateShort(dateStr: string): string {
  const date = new Date(dateStr + 'T12:00:00');
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
}

/**
 * Get today's date in YYYY-MM-DD format.
 */
export function getTodayDate(): string {
  const today = new Date();
  return today.toISOString().split('T')[0];
}

/**
 * Get a date N days from now in YYYY-MM-DD format.
 */
export function getDateDaysFromNow(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().split('T')[0];
}

/**
 * Check if a date string is in the future.
 */
export function isFutureDate(dateStr: string): boolean {
  const date = new Date(dateStr + 'T00:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return date >= today;
}

/**
 * Combine class names, filtering out falsy values.
 */
export function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}

/**
 * Format level for display (e.g., "Iniciante1" -> "Iniciante 1").
 */
export function formatLevel(level?: string): string {
  if (!level) return '';
  return level
    .replace('Iniciante', 'Iniciante ')
    .replace('Intermediario', 'Intermediario ')
    .replace('Avançado', 'Avançado ')
    .trim();
}

/**
 * Format wave side for display (e.g., "Lado_esquerdo" -> "Esquerdo").
 */
export function formatWaveSide(waveSide?: string): string {
  if (!waveSide) return '';
  return waveSide
    .replace('Lado_', '')
    .replace('esquerdo', 'Esquerdo')
    .replace('direito', 'Direito');
}
