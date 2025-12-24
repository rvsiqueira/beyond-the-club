'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Users, Radio, ArrowRight, RefreshCw, Clock, Waves, GraduationCap } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from '@/components/ui';
import { useMembers, useBookings, useAvailability, useScanAvailability, useBeyondTokenStatus, useAuth } from '@/hooks';
import { isBeyondAuthError } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { SMSVerificationModal } from '@/components/SMSVerificationModal';
import { useQueryClient } from '@tanstack/react-query';

const REFRESH_COOLDOWN_SECONDS = 60;

const LEVEL_COLORS: Record<string, string> = {
  'Iniciante1': 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200',
  'Iniciante2': 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200',
  'Intermediario1': 'bg-blue-100 text-blue-700 hover:bg-blue-200',
  'Intermediario2': 'bg-blue-100 text-blue-700 hover:bg-blue-200',
  'Avançado1': 'bg-purple-100 text-purple-700 hover:bg-purple-200',
  'Avançado2': 'bg-purple-100 text-purple-700 hover:bg-purple-200',
};

const LEVEL_LABELS: Record<string, string> = {
  'Iniciante1': 'Iniciante 1',
  'Iniciante2': 'Iniciante 2',
  'Intermediario1': 'Intermediário 1',
  'Intermediario2': 'Intermediário 2',
  'Avançado1': 'Avançado 1',
  'Avançado2': 'Avançado 2',
};

const LEVEL_ORDER = [
  'Iniciante1',
  'Iniciante2',
  'Intermediario1',
  'Intermediario2',
  'Avançado1',
  'Avançado2',
];

// Wave images by level - fixed per level for quick visual identification
const getWaveBackground = (level: string) => {
  if (level.startsWith('Iniciante')) {
    return '/wave-levels/beginner-1.jpg';
  } else if (level.startsWith('Intermediario')) {
    return '/wave-levels/intermediate-1.jpg';
  } else {
    return '/wave-levels/advanced-1.jpg';
  }
};

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { data: membersData, isLoading: membersLoading, error: membersError } = useMembers();
  const { data: bookingsData, isLoading: bookingsLoading, error: bookingsError } = useBookings();
  const { data: availabilityData, isLoading: availabilityLoading, error: availabilityError } = useAvailability();
  const { data: beyondStatus, isLoading: beyondStatusLoading } = useBeyondTokenStatus();
  const scanMutation = useScanAvailability();
  const queryClient = useQueryClient();

  const [showSMSModal, setShowSMSModal] = useState(false);
  const [refreshCooldown, setRefreshCooldown] = useState(0);
  const [lastRefreshTime, setLastRefreshTime] = useState<number | null>(null);

  // Cooldown timer for refresh button
  useEffect(() => {
    if (refreshCooldown > 0) {
      const timer = setTimeout(() => {
        setRefreshCooldown(refreshCooldown - 1);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [refreshCooldown]);

  // Calculate initial cooldown based on cache_updated_at
  useEffect(() => {
    if (availabilityData?.cache_updated_at && !lastRefreshTime) {
      const cacheTime = new Date(availabilityData.cache_updated_at).getTime();
      const now = Date.now();
      const secondsSinceUpdate = Math.floor((now - cacheTime) / 1000);

      // Only set cooldown if update was recent (within cooldown period)
      // and the calculated time is reasonable (not negative or too large)
      if (secondsSinceUpdate >= 0 && secondsSinceUpdate < REFRESH_COOLDOWN_SECONDS) {
        setRefreshCooldown(REFRESH_COOLDOWN_SECONDS - secondsSinceUpdate);
      }
      // If secondsSinceUpdate is negative or too large, don't set cooldown (allow refresh)
    }
  }, [availabilityData?.cache_updated_at, lastRefreshTime]);

  const handleRefresh = useCallback(() => {
    if (refreshCooldown > 0 || scanMutation.isPending) return;

    scanMutation.mutate(undefined, {
      onSuccess: () => {
        setLastRefreshTime(Date.now());
        setRefreshCooldown(REFRESH_COOLDOWN_SECONDS);
      }
    });
  }, [refreshCooldown, scanMutation]);

  const isRefreshDisabled = refreshCooldown > 0 || scanMutation.isPending;

  // Auto-show SMS modal if Beyond token is invalid OR any query returns Beyond auth error
  useEffect(() => {
    const hasBeyondError =
      isBeyondAuthError(membersError) ||
      isBeyondAuthError(bookingsError) ||
      isBeyondAuthError(availabilityError);

    if (hasBeyondError || (!beyondStatusLoading && beyondStatus && !beyondStatus.valid)) {
      setShowSMSModal(true);
    }
  }, [beyondStatus, beyondStatusLoading, membersError, bookingsError, availabilityError]);

  const membersWithoutBooking = membersData?.members.filter(m => !m.has_booking) ?? [];
  const membersWithPrefs = membersData?.members.filter(m => m.has_preferences) ?? [];

  // Get the next 6 available sessions (sorted by date and time)
  const nextSessions = useMemo(() => {
    if (!availabilityData?.slots) return [];

    // Filter only available slots and sort by date + interval
    return availabilityData.slots
      .filter(s => s.available > 0)
      .sort((a, b) => {
        const dateCompare = a.date.localeCompare(b.date);
        if (dateCompare !== 0) return dateCompare;
        return a.interval.localeCompare(b.interval);
      })
      .slice(0, 6)
      .map(slot => {
        const [year, month, day] = slot.date.split('-').map(Number);
        const dateObj = new Date(year, month - 1, day);
        const weekday = dateObj.toLocaleDateString('pt-BR', { weekday: 'long' });

        const dayMonth = dateObj.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });

        return {
          ...slot,
          weekday: weekday.charAt(0).toUpperCase() + weekday.slice(1),
          dayMonth,
          formattedDate: formatDate(slot.date)
        };
      });
  }, [availabilityData]);

  // Group availability by date and level for the next 3 dates
  const availabilityByDate = useMemo(() => {
    if (!availabilityData?.slots) return [];

    // Get unique dates sorted
    const dates = [...new Set(availabilityData.slots.map(s => s.date))].sort();
    const next3Dates = dates.slice(0, 3);

    return next3Dates.map(date => {
      const slotsForDate = availabilityData.slots.filter(s => s.date === date && s.available > 0);

      // Group by level
      const byLevel: Record<string, number> = {};
      slotsForDate.forEach(slot => {
        if (slot.level) {
          byLevel[slot.level] = (byLevel[slot.level] || 0) + 1;
        }
      });

      // Parse date for display
      const [year, month, day] = date.split('-').map(Number);
      const dateObj = new Date(year, month - 1, day);
      const weekday = dateObj.toLocaleDateString('pt-BR', { weekday: 'short' }).replace('.', '');
      const dayMonth = dateObj.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });

      return {
        date,
        dayMonth,
        weekday: weekday.charAt(0).toUpperCase() + weekday.slice(1),
        day,
        totalAvailable: slotsForDate.length,
        byLevel
      };
    });
  }, [availabilityData]);

  const handleLevelClick = (date: string, level: string) => {
    router.push(`/availability?date=${date}&level=${level}`);
  };

  const handleSlotClick = (slot: { date: string; interval: string; level: string; wave_side: string }) => {
    const params = new URLSearchParams({
      date: slot.date,
      interval: slot.interval,
      level: slot.level,
      wave_side: slot.wave_side,
      open_modal: 'true'
    });
    router.push(`/availability?${params.toString()}`);
  };

  // Format level for display (full name)
  const formatLevel = (level?: string) => {
    if (!level) return null;
    return level.replace('Iniciante', 'Iniciante ').replace('Intermediario', 'Intermediário ').replace('Avançado', 'Avançado ').replace('Avancado', 'Avançado ').trim();
  };

  // Format wave side for display (full name)
  const formatWaveSide = (waveSide?: string) => {
    if (!waveSide) return null;
    return waveSide.replace('Lado_', '').replace('esquerdo', 'Esquerdo').replace('direito', 'Direito');
  };

  return (
    <MainLayout title="Dashboard">
      {/* Next 6 Available Sessions */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">Próximas Sessões Disponíveis</h2>
          <Link href="/availability">
            <Button variant="ghost" size="sm">
              Ver todas <ArrowRight className="ml-1 h-4 w-4" />
            </Button>
          </Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {availabilityLoading ? (
            <>
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="animate-pulse h-[140px] bg-gray-200 rounded-2xl" />
              ))}
            </>
          ) : nextSessions.length === 0 ? (
            <div className="col-span-6 flex items-center justify-center bg-gray-50 rounded-2xl py-12">
              <p className="text-gray-500 text-sm">Nenhuma sessão disponível</p>
            </div>
          ) : (
            nextSessions.map((slot, idx) => (
              <div
                key={`${slot.date}-${slot.interval}-${slot.level}-${idx}`}
                onClick={() => handleSlotClick(slot)}
                className="relative rounded-2xl overflow-hidden shadow-lg group transition-all duration-300 cursor-pointer hover:shadow-xl hover:-translate-y-1"
              >
                {/* Background Image */}
                <div
                  className="absolute inset-0 bg-cover bg-center transition-transform duration-500 group-hover:scale-110"
                  style={{ backgroundImage: `url(${getWaveBackground(slot.level)})` }}
                />
                {/* Gradient Overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/40 to-black/20" />

                {/* Content */}
                <div className="relative p-3 min-h-[140px] flex flex-col justify-between">
                  {/* Top Row - Time and Vacancy */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-1.5">
                      <div className="p-1.5 bg-white/20 backdrop-blur-sm rounded-lg">
                        <Clock className="h-3 w-3 text-white" />
                      </div>
                      <span className="text-xl font-bold text-white drop-shadow-lg">{slot.interval}</span>
                    </div>
                    <span className="px-2 py-1 rounded-full text-[10px] font-bold bg-white/95 text-gray-800">
                      <Users className="h-2.5 w-2.5 inline mr-0.5" />
                      {slot.available}/{slot.max_quantity}
                    </span>
                  </div>

                  {/* Bottom Content */}
                  <div>
                    <p className="text-white/90 text-sm font-semibold mb-0.5">{slot.dayMonth}</p>
                    <p className="text-white/60 text-xs mb-1">{slot.weekday}</p>
                    <div className="flex flex-wrap gap-1">
                      <span className="px-2 py-1 bg-white/20 backdrop-blur-sm rounded-full text-[10px] font-semibold text-white flex items-center gap-1">
                        <GraduationCap className="h-2.5 w-2.5" />
                        {LEVEL_LABELS[slot.level] || slot.level}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Green pulse indicator */}
                <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-green-400 animate-pulse shadow-lg shadow-green-400/50" />
              </div>
            ))
          )}
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Bookings */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Próximos Agendamentos</CardTitle>
            <Link href="/bookings">
              <Button variant="ghost" size="sm">
                Ver todos <ArrowRight className="ml-1 h-4 w-4" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {bookingsLoading ? (
              <div className="animate-pulse space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-32 bg-gray-100 rounded-xl" />
                ))}
              </div>
            ) : bookingsData?.bookings.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                Nenhum agendamento ativo
              </p>
            ) : (
              <div className="space-y-4">
                {bookingsData?.bookings.slice(0, 5).map((booking) => {
                  const daysUntil = Math.ceil((new Date(booking.date).getTime() - new Date().setHours(0,0,0,0)) / (1000 * 60 * 60 * 24));
                  const daysLabel = daysUntil === 0 ? 'Hoje' : daysUntil === 1 ? 'Amanhã' : `Em ${daysUntil} dias`;

                  return (
                    <div
                      key={booking.voucher_code}
                      className="relative h-32 rounded-xl overflow-hidden group cursor-pointer"
                    >
                      {/* Background Image */}
                      <div
                        className="absolute inset-0 bg-cover bg-center transition-transform duration-300 group-hover:scale-105"
                        style={{ backgroundImage: `url(${getWaveBackground(booking.level || 'Avançado1')})` }}
                      />
                      {/* Gradient Overlay */}
                      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-black/20" />

                      {/* Days Badge */}
                      <div className="absolute top-3 left-3">
                        <span className="px-3 py-1 bg-white/90 backdrop-blur-sm rounded-full text-xs font-semibold text-gray-800">
                          {daysLabel}
                        </span>
                      </div>

                      {/* Content */}
                      <div className="absolute bottom-0 left-0 right-0 p-4">
                        <p className="text-white/80 text-sm">
                          {formatDate(booking.date)} · {booking.interval}
                        </p>
                        <p className="text-white font-bold text-lg">
                          {booking.member_name}
                        </p>
                        <div className="flex gap-2 mt-1">
                          {booking.level && (
                            <span className="text-white/90 text-xs flex items-center gap-1">
                              <GraduationCap className="h-3 w-3" />
                              {formatLevel(booking.level)}
                            </span>
                          )}
                          {booking.wave_side && (
                            <span className="text-white/90 text-xs flex items-center gap-1">
                              <Waves className="h-3 w-3" />
                              {formatWaveSide(booking.wave_side)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Members Ready to Book */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Membros sem Agendamento</CardTitle>
            <Link href="/monitor">
              <Button variant="primary" size="sm">
                <Radio className="mr-1 h-4 w-4" /> Auto Monitor
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {membersLoading ? (
              <div className="animate-pulse space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 bg-gray-100 rounded-lg" />
                ))}
              </div>
            ) : membersWithoutBooking.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                Todos os membros estao agendados!
              </p>
            ) : (
              <div className="space-y-3">
                {membersWithoutBooking.slice(0, 5).map((member) => (
                  <div
                    key={member.member_id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                        <span className="text-primary-600 font-medium text-sm">
                          {member.social_name[0]}
                        </span>
                      </div>
                      <span className="font-medium text-gray-900">
                        {member.social_name}
                      </span>
                    </div>
                    {member.has_preferences ? (
                      <Badge variant="success">Preferencias</Badge>
                    ) : (
                      <Badge variant="warning">Sem prefs</Badge>
                    )}
                  </div>
                ))}
                {membersWithoutBooking.length > 5 && (
                  <p className="text-sm text-gray-500 text-center pt-2">
                    +{membersWithoutBooking.length - 5} membros
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Availability by Date */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Próximas Disponibilidades</CardTitle>
              {availabilityData?.cache_updated_at && (
                <p className="text-sm text-gray-500 mt-1">
                  Atualizado às {new Date(availabilityData.cache_updated_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                </p>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              isLoading={scanMutation.isPending}
              disabled={isRefreshDisabled}
            >
              <RefreshCw className={`mr-1 h-4 w-4 ${scanMutation.isPending ? 'animate-spin' : ''}`} />
              {refreshCooldown > 0 ? `${refreshCooldown}s` : 'Atualizar'}
            </Button>
          </CardHeader>
          <CardContent>
            {availabilityLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="animate-pulse h-48 bg-gray-100 rounded-lg" />
                ))}
              </div>
            ) : availabilityByDate.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                Nenhuma disponibilidade encontrada
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {availabilityByDate.map((dateInfo) => (
                  <div
                    key={dateInfo.date}
                    className="bg-gray-50 rounded-xl p-4 border border-gray-100"
                  >
                    {/* Date Header */}
                    <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-200">
                      <div className="flex items-center gap-3">
                        <div className="bg-primary-600 text-white rounded-lg px-3 py-2 text-center min-w-[60px]">
                          <p className="text-xs font-medium uppercase">{dateInfo.weekday}</p>
                          <p className="text-2xl font-bold">{dateInfo.day}</p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-500">{dateInfo.dayMonth}</p>
                          <p className="text-lg font-semibold text-gray-800">
                            {dateInfo.totalAvailable} sessões
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Levels Summary */}
                    <div className="space-y-2">
                      {Object.entries(dateInfo.byLevel)
                        .sort(([a], [b]) => LEVEL_ORDER.indexOf(a) - LEVEL_ORDER.indexOf(b))
                        .map(([level, count]) => (
                          <button
                            key={level}
                            onClick={() => handleLevelClick(dateInfo.date, level)}
                            className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors cursor-pointer ${LEVEL_COLORS[level] || 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                          >
                            <span className="font-medium text-sm">
                              {LEVEL_LABELS[level] || level}
                            </span>
                            <span className="font-bold">
                              {count}
                            </span>
                          </button>
                        ))}
                      {Object.keys(dateInfo.byLevel).length === 0 && (
                        <p className="text-sm text-gray-400 text-center py-2">
                          Sem sessões disponíveis
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* SMS Verification Modal */}
      {user && (
        <SMSVerificationModal
          isOpen={showSMSModal}
          onClose={() => setShowSMSModal(false)}
          onSuccess={() => {
            // Refresh all queries that depend on Beyond API
            queryClient.invalidateQueries({ queryKey: ['beyond-token-status'] });
            queryClient.invalidateQueries({ queryKey: ['members'] });
            queryClient.invalidateQueries({ queryKey: ['bookings'] });
            queryClient.invalidateQueries({ queryKey: ['availability'] });
          }}
          phone={user.phone}
        />
      )}
    </MainLayout>
  );
}
