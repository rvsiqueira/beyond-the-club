'use client';

import { useState, useMemo, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Calendar, RefreshCw, Clock, Waves, GraduationCap, ArrowLeft, ArrowRight, Users } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui';
import { useAvailability, useScanAvailability } from '@/hooks';
import { BatchBookingModal } from '@/components/BatchBookingModal';
import { useQueryClient } from '@tanstack/react-query';
import type { AvailableSlot } from '@/types';

const LEVELS = [
  { value: 'Iniciante1', label: 'Iniciante 1', shortLabel: 'Ini 1', color: 'bg-emerald-100 text-emerald-700 border-emerald-300' },
  { value: 'Iniciante2', label: 'Iniciante 2', shortLabel: 'Ini 2', color: 'bg-emerald-100 text-emerald-700 border-emerald-300' },
  { value: 'Intermediario1', label: 'Intermediário 1', shortLabel: 'Int 1', color: 'bg-blue-100 text-blue-700 border-blue-300' },
  { value: 'Intermediario2', label: 'Intermediário 2', shortLabel: 'Int 2', color: 'bg-blue-100 text-blue-700 border-blue-300' },
  { value: 'Avançado1', label: 'Avançado 1', shortLabel: 'Ava 1', color: 'bg-purple-100 text-purple-700 border-purple-300' },
  { value: 'Avançado2', label: 'Avançado 2', shortLabel: 'Ava 2', color: 'bg-purple-100 text-purple-700 border-purple-300' },
];

const WAVE_SIDES = [
  { value: 'Lado_esquerdo', label: 'Esquerda', icon: '←' },
  { value: 'Lado_direito', label: 'Direita', icon: '→' },
];

// Wave images by level - fixed per level for quick visual identification
// Beginner: sunrise/sunset calm waves
// Intermediate: turquoise/green water
// Advanced: strong blue ocean waves
const getWaveBackground = (level: string) => {
  if (level.startsWith('Iniciante')) {
    return '/wave-levels/beginner-1.jpg';
  } else if (level.startsWith('Intermediario')) {
    return '/wave-levels/intermediate-1.jpg';
  } else {
    return '/wave-levels/advanced-1.jpg';
  }
};

const REFRESH_COOLDOWN_SECONDS = 60;

function AvailabilityContent() {
  const { data, isLoading, error } = useAvailability();
  const scanMutation = useScanAvailability();
  const queryClient = useQueryClient();

  const searchParams = useSearchParams();
  const initialDate = searchParams.get('date');
  const initialLevel = searchParams.get('level');
  const initialInterval = searchParams.get('interval');
  const initialWaveSide = searchParams.get('wave_side');
  const shouldOpenModal = searchParams.get('open_modal') === 'true';

  const [levelFilter, setLevelFilter] = useState(initialLevel || '');
  const [waveSideFilter, setWaveSideFilter] = useState('');
  const [dateFilter, setDateFilter] = useState(initialDate || '');
  const [refreshCooldown, setRefreshCooldown] = useState(0);
  const [lastRefreshTime, setLastRefreshTime] = useState<number | null>(null);
  const [initialFiltersApplied, setInitialFiltersApplied] = useState(false);
  const [modalAutoOpened, setModalAutoOpened] = useState(false);

  // Batch booking modal state
  const [selectedSlot, setSelectedSlot] = useState<AvailableSlot | null>(null);
  const [showBookingModal, setShowBookingModal] = useState(false);

  const handleSlotClick = (slot: AvailableSlot) => {
    if (slot.available > 0) {
      setSelectedSlot(slot);
      setShowBookingModal(true);
    }
  };

  const handleBookingSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['availability'] });
    queryClient.invalidateQueries({ queryKey: ['members'] });
    queryClient.invalidateQueries({ queryKey: ['bookings'] });
  };

  // Auto-open modal if coming from dashboard with specific slot params
  useEffect(() => {
    if (shouldOpenModal && !modalAutoOpened && data?.slots && initialDate && initialInterval && initialLevel && initialWaveSide) {
      const matchingSlot = data.slots.find(
        (s: AvailableSlot) => s.date === initialDate &&
             s.interval === initialInterval &&
             s.level === initialLevel &&
             s.wave_side === initialWaveSide &&
             s.available > 0
      );
      if (matchingSlot) {
        setSelectedSlot(matchingSlot);
        setShowBookingModal(true);
        setModalAutoOpened(true);
      }
    }
  }, [shouldOpenModal, modalAutoOpened, data?.slots, initialDate, initialInterval, initialLevel, initialWaveSide]);

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
    if (data?.cache_updated_at && !lastRefreshTime) {
      const cacheTime = new Date(data.cache_updated_at).getTime();
      const now = Date.now();
      const secondsSinceUpdate = Math.floor((now - cacheTime) / 1000);

      if (secondsSinceUpdate >= 0 && secondsSinceUpdate < REFRESH_COOLDOWN_SECONDS) {
        setRefreshCooldown(REFRESH_COOLDOWN_SECONDS - secondsSinceUpdate);
      }
    }
  }, [data?.cache_updated_at, lastRefreshTime]);

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

  // Get unique dates
  const dates = useMemo(() => {
    if (!data?.slots) return [];
    const uniqueDates = [...new Set(data.slots.map((s) => s.date))];
    return uniqueDates.sort();
  }, [data]);

  // Auto-select date: use URL param if valid, otherwise first available date
  useEffect(() => {
    if (dates.length > 0 && !initialFiltersApplied) {
      // If URL has a valid date param, use it; otherwise use first available
      if (initialDate && dates.includes(initialDate)) {
        setDateFilter(initialDate);
      } else if (!dateFilter) {
        setDateFilter(dates[0]);
      }
      setInitialFiltersApplied(true);
    }
  }, [dates, dateFilter, initialDate, initialFiltersApplied]);

  // Filter slots
  const filteredSlots = useMemo(() => {
    if (!data?.slots) return [];
    return data.slots.filter((slot) => {
      if (levelFilter && slot.level !== levelFilter) return false;
      if (waveSideFilter && slot.wave_side !== waveSideFilter) return false;
      if (dateFilter && slot.date !== dateFilter) return false;
      return true;
    });
  }, [data, levelFilter, waveSideFilter, dateFilter]);

  // Group by interval for cleaner display
  const groupedByInterval = useMemo(() => {
    const groups: Record<string, typeof filteredSlots> = {};
    filteredSlots.forEach((slot) => {
      if (!groups[slot.interval]) groups[slot.interval] = [];
      groups[slot.interval].push(slot);
    });
    return groups;
  }, [filteredSlots]);

  // Get short day name
  const getShortDate = (dateStr: string) => {
    const [year, month, day] = dateStr.split('-').map(Number);
    const date = new Date(year, month - 1, day);
    const weekday = date.toLocaleDateString('pt-BR', { weekday: 'short' }).replace('.', '');
    return { day, weekday: weekday.charAt(0).toUpperCase() + weekday.slice(1) };
  };

  // Navigate dates
  const currentDateIndex = dates.indexOf(dateFilter);
  const canGoPrev = currentDateIndex > 0;
  const canGoNext = currentDateIndex < dates.length - 1;

  const goToPrevDate = () => {
    if (canGoPrev) setDateFilter(dates[currentDateIndex - 1]);
  };

  const goToNextDate = () => {
    if (canGoNext) setDateFilter(dates[currentDateIndex + 1]);
  };

  // Count slots per filter for badges
  const countByLevel = useMemo(() => {
    if (!data?.slots) return {};
    const counts: Record<string, number> = {};
    data.slots
      .filter(s => (!waveSideFilter || s.wave_side === waveSideFilter) && (!dateFilter || s.date === dateFilter))
      .forEach(s => {
        counts[s.level] = (counts[s.level] || 0) + (s.available > 0 ? 1 : 0);
      });
    return counts;
  }, [data, waveSideFilter, dateFilter]);

  const countByWaveSide = useMemo(() => {
    if (!data?.slots) return {};
    const counts: Record<string, number> = {};
    data.slots
      .filter(s => (!levelFilter || s.level === levelFilter) && (!dateFilter || s.date === dateFilter))
      .forEach(s => {
        counts[s.wave_side] = (counts[s.wave_side] || 0) + (s.available > 0 ? 1 : 0);
      });
    return counts;
  }, [data, levelFilter, dateFilter]);

  return (
    <MainLayout title="Disponibilidade">
      {/* Header with Refresh Button */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600">
            <span className="font-semibold text-gray-800">{filteredSlots.filter(s => s.available > 0).length}</span> sessões disponíveis
          </span>
          {data?.cache_updated_at && (
            <span className="text-xs text-gray-400">
              · Atualizado às {new Date(data.cache_updated_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          isLoading={scanMutation.isPending}
          disabled={isRefreshDisabled}
          className="whitespace-nowrap"
        >
          <RefreshCw className={`h-4 w-4 mr-1.5 ${scanMutation.isPending ? 'animate-spin' : ''}`} />
          {refreshCooldown > 0 ? `${refreshCooldown}s` : 'Atualizar'}
        </Button>
      </div>

      {/* Compact Filter Bar */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-6">
        <div className="flex flex-col lg:flex-row lg:items-center gap-4">
          {/* Date Navigation */}
          <div className="flex items-center gap-2">
            <button
              onClick={goToPrevDate}
              disabled={!canGoPrev}
              className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>

            <div className="flex gap-1 overflow-x-auto pb-1 scrollbar-hide">
              {dates.map((date) => {
                const { day, weekday } = getShortDate(date);
                const isSelected = date === dateFilter;
                return (
                  <button
                    key={date}
                    onClick={() => setDateFilter(date)}
                    className={`flex flex-col items-center px-3 py-2 rounded-lg min-w-[52px] transition-all ${
                      isSelected
                        ? 'bg-primary-600 text-white shadow-md'
                        : 'hover:bg-gray-100 text-gray-600'
                    }`}
                  >
                    <span className="text-[10px] font-medium uppercase">{weekday}</span>
                    <span className="text-lg font-bold">{day}</span>
                  </button>
                );
              })}
            </div>

            <button
              onClick={goToNextDate}
              disabled={!canGoNext}
              className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>

          {/* Divider */}
          <div className="hidden lg:block w-px h-10 bg-gray-200" />

          {/* Level Filter Chips */}
          <div className="flex items-center gap-2 flex-wrap">
            <GraduationCap className="h-4 w-4 text-gray-400" />
            <button
              onClick={() => setLevelFilter('')}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                !levelFilter
                  ? 'bg-gray-800 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Todos
            </button>
            {LEVELS.map((level) => {
              const count = countByLevel[level.value] || 0;
              const isSelected = levelFilter === level.value;
              const isDisabled = count === 0;
              return (
                <button
                  key={level.value}
                  onClick={() => !isDisabled && setLevelFilter(isSelected ? '' : level.value)}
                  disabled={isDisabled}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all flex items-center gap-1.5 relative ${
                    isDisabled
                      ? 'bg-gray-100 text-gray-300 border-gray-200 cursor-not-allowed line-through decoration-gray-400'
                      : isSelected
                        ? level.color + ' border-current'
                        : 'bg-white text-gray-500 border-gray-200 hover:border-gray-300'
                  }`}
                >
                  {level.shortLabel}
                  {count > 0 && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                      isSelected ? 'bg-white/30' : 'bg-green-100 text-green-700'
                    }`}>
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Divider */}
          <div className="hidden lg:block w-px h-10 bg-gray-200" />

          {/* Wave Side Filter */}
          <div className="flex items-center gap-2">
            <Waves className="h-4 w-4 text-gray-400" />
            <div className="flex rounded-lg border border-gray-200 overflow-hidden">
              <button
                onClick={() => setWaveSideFilter('')}
                className={`px-3 py-1.5 text-xs font-medium transition-all ${
                  !waveSideFilter
                    ? 'bg-gray-800 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                Ambos
              </button>
              {WAVE_SIDES.map((side) => {
                const count = countByWaveSide[side.value] || 0;
                const isSelected = waveSideFilter === side.value;
                const isDisabled = count === 0;
                return (
                  <button
                    key={side.value}
                    onClick={() => !isDisabled && setWaveSideFilter(isSelected ? '' : side.value)}
                    disabled={isDisabled}
                    className={`px-3 py-1.5 text-xs font-medium transition-all flex items-center gap-1 border-l border-gray-200 ${
                      isDisabled
                        ? 'bg-gray-100 text-gray-300 cursor-not-allowed line-through decoration-gray-400'
                        : isSelected
                          ? 'bg-blue-600 text-white'
                          : 'bg-white text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    <span>{side.icon}</span>
                    {side.label}
                    {count > 0 && !isSelected && (
                      <span className="text-[10px] px-1 py-0.5 rounded bg-green-100 text-green-700">
                        {count}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-6">
          <p className="text-red-600">{error.message}</p>
        </div>
      )}

      {/* Loading */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="animate-pulse h-[180px] bg-gray-200 rounded-2xl" />
          ))}
        </div>
      ) : (
        <>
          {/* Slots Grid by Interval */}
          {Object.keys(groupedByInterval).length === 0 ? (
            <div className="text-center py-16 bg-gray-50 rounded-xl">
              <Calendar className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Nenhum slot disponivel para esta combinacao</p>
              <button
                onClick={() => { setLevelFilter(''); setWaveSideFilter(''); }}
                className="mt-3 text-sm text-primary-600 hover:underline"
              >
                Limpar filtros
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {Object.entries(groupedByInterval)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([interval, slots]) => (
                  slots.map((slot, idx) => {
                    const levelConfig = LEVELS.find(l => l.value === slot.level);
                    const hasVacancy = slot.available > 0;
                    const waveImage = getWaveBackground(slot.level);

                    return (
                      <div
                        key={`${slot.date}-${slot.interval}-${slot.level}-${slot.wave_side}-${idx}`}
                        onClick={() => handleSlotClick(slot)}
                        className={`relative rounded-2xl overflow-hidden shadow-lg group transition-all duration-300 ${
                          hasVacancy
                            ? 'cursor-pointer hover:shadow-xl hover:-translate-y-1'
                            : 'opacity-50 cursor-not-allowed grayscale'
                        }`}
                      >
                        {/* Background Image */}
                        <div
                          className="absolute inset-0 bg-cover bg-center transition-transform duration-500 group-hover:scale-110"
                          style={{ backgroundImage: `url(${waveImage})` }}
                        />
                        {/* Gradient Overlay */}
                        <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/40 to-black/20" />

                        {/* Content */}
                        <div className="relative p-4 min-h-[180px] flex flex-col justify-between">
                          {/* Top Row - Time and Vacancy */}
                          <div className="flex items-start justify-between">
                            {/* Time Badge */}
                            <div className="flex items-center gap-2">
                              <div className="p-2 bg-white/20 backdrop-blur-sm rounded-lg">
                                <Clock className="h-4 w-4 text-white" />
                              </div>
                              <span className="text-2xl font-bold text-white drop-shadow-lg">{slot.interval}</span>
                            </div>

                            {/* Vacancy Badge */}
                            <span className={`px-3 py-1.5 rounded-full text-xs font-bold shadow-sm ${
                              hasVacancy
                                ? 'bg-white/95 text-gray-800'
                                : 'bg-gray-500/80 text-white'
                            }`}>
                              <Users className="h-3 w-3 inline mr-1" />
                              {slot.available}/{slot.max_quantity}
                            </span>
                          </div>

                          {/* Bottom Content */}
                          <div>
                            {/* Tags */}
                            <div className="flex flex-wrap gap-2 mb-3">
                              <span className="px-3 py-1.5 bg-white/20 backdrop-blur-sm rounded-full text-xs font-semibold text-white flex items-center gap-1.5">
                                <GraduationCap className="h-3.5 w-3.5" />
                                {levelConfig?.label || slot.level}
                              </span>
                              <span className="px-3 py-1.5 bg-white/20 backdrop-blur-sm rounded-full text-xs font-semibold text-white flex items-center gap-1.5">
                                <Waves className="h-3.5 w-3.5" />
                                {slot.wave_side === 'Lado_esquerdo' ? 'Esquerda' : 'Direita'}
                              </span>
                            </div>

                            {/* Click hint for available slots */}
                            {hasVacancy && (
                              <div className="flex items-center justify-center gap-2 pt-3 border-t border-white/20 text-white/70 text-xs">
                                <Users className="h-3 w-3" />
                                <span>Clique para agendar</span>
                              </div>
                            )}

                            {/* Sold out message */}
                            {!hasVacancy && (
                              <div className="flex items-center justify-center gap-2 pt-3 border-t border-white/20 text-white/50 text-xs">
                                <span>Esgotado</span>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Green pulse indicator for available slots */}
                        {hasVacancy && (
                          <div className="absolute top-3 right-3 w-2.5 h-2.5 rounded-full bg-green-400 animate-pulse shadow-lg shadow-green-400/50" />
                        )}
                      </div>
                    );
                  })
                ))}
            </div>
          )}
        </>
      )}

      {/* Batch Booking Modal */}
      <BatchBookingModal
        isOpen={showBookingModal}
        onClose={() => setShowBookingModal(false)}
        slot={selectedSlot}
        onSuccess={handleBookingSuccess}
      />
    </MainLayout>
  );
}

export default function AvailabilityPage() {
  return (
    <Suspense fallback={
      <MainLayout title="Disponibilidade">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="animate-pulse h-[180px] bg-gray-200 rounded-2xl" />
          ))}
        </div>
      </MainLayout>
    }>
      <AvailabilityContent />
    </Suspense>
  );
}
