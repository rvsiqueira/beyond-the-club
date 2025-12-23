'use client';

import { useState, useMemo } from 'react';
import { Calendar, RefreshCw, Filter, Clock } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle, Button, Select, Badge } from '@/components/ui';
import { useAvailability, useScanAvailability } from '@/hooks';
import { formatDate } from '@/lib/utils';

const LEVELS = [
  { value: '', label: 'Todos os niveis' },
  { value: 'Iniciante1', label: 'Iniciante 1' },
  { value: 'Iniciante2', label: 'Iniciante 2' },
  { value: 'Intermediario1', label: 'Intermediario 1' },
  { value: 'Intermediario2', label: 'Intermediario 2' },
  { value: 'Avançado1', label: 'Avancado 1' },
  { value: 'Avançado2', label: 'Avancado 2' },
];

const WAVE_SIDES = [
  { value: '', label: 'Todos os lados' },
  { value: 'Lado_esquerdo', label: 'Lado Esquerdo' },
  { value: 'Lado_direito', label: 'Lado Direito' },
];

export default function AvailabilityPage() {
  const { data, isLoading, error } = useAvailability();
  const scanMutation = useScanAvailability();

  const [levelFilter, setLevelFilter] = useState('');
  const [waveSideFilter, setWaveSideFilter] = useState('');
  const [dateFilter, setDateFilter] = useState('');

  // Get unique dates
  const dates = useMemo(() => {
    if (!data?.slots) return [];
    const uniqueDates = [...new Set(data.slots.map((s) => s.date))];
    return uniqueDates.sort();
  }, [data]);

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

  // Group by date
  const groupedSlots = useMemo(() => {
    const groups: Record<string, typeof filteredSlots> = {};
    filteredSlots.forEach((slot) => {
      if (!groups[slot.date]) groups[slot.date] = [];
      groups[slot.date].push(slot);
    });
    // Sort slots within each date by interval
    Object.keys(groups).forEach((date) => {
      groups[date].sort((a, b) => a.interval.localeCompare(b.interval));
    });
    return groups;
  }, [filteredSlots]);

  const dateOptions = [
    { value: '', label: 'Todas as datas' },
    ...dates.map((d) => ({ value: d, label: formatDate(d) })),
  ];

  return (
    <MainLayout title="Disponibilidade">
      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="py-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="h-5 w-5 text-gray-400" />
              <span className="text-sm font-medium text-gray-700">Filtros:</span>
            </div>
            <Select
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              options={LEVELS}
              className="w-48"
            />
            <Select
              value={waveSideFilter}
              onChange={(e) => setWaveSideFilter(e.target.value)}
              options={WAVE_SIDES}
              className="w-48"
            />
            <Select
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              options={dateOptions}
              className="w-48"
            />
            <div className="flex-1" />
            <Button
              variant="outline"
              onClick={() => scanMutation.mutate()}
              isLoading={scanMutation.isPending}
            >
              <RefreshCw className="h-4 w-4 mr-2" /> Atualizar
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Cache Status */}
      {data && (
        <div className="mb-4 flex items-center gap-4 text-sm text-gray-500">
          <span>
            {data.cache_valid ? (
              <Badge variant="success">Cache valido</Badge>
            ) : (
              <Badge variant="warning">Cache expirado</Badge>
            )}
          </span>
          {data.cache_updated_at && (
            <span>
              Atualizado: {new Date(data.cache_updated_at).toLocaleString('pt-BR')}
            </span>
          )}
          <span>{filteredSlots.length} slots encontrados</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-6">
          <p className="text-red-600">{error.message}</p>
        </div>
      )}

      {/* Loading */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse h-48 bg-gray-100 rounded-xl" />
          ))}
        </div>
      ) : (
        <>
          {/* Slots by Date */}
          {Object.keys(groupedSlots).length === 0 ? (
            <div className="text-center py-12">
              <Calendar className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Nenhum slot disponivel</p>
            </div>
          ) : (
            <div className="space-y-6">
              {Object.entries(groupedSlots)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([date, slots]) => (
                  <Card key={date}>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Calendar className="h-5 w-5" />
                        {formatDate(date)}
                        <Badge variant="default" className="ml-2">
                          {slots.length} slots
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {slots.map((slot, idx) => (
                          <div
                            key={`${slot.date}-${slot.interval}-${slot.level}-${slot.wave_side}-${idx}`}
                            className={`p-4 rounded-lg border ${
                              slot.available > 0
                                ? 'bg-green-50 border-green-200'
                                : 'bg-gray-50 border-gray-200'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <Clock className="h-4 w-4 text-gray-400" />
                                <span className="font-medium">{slot.interval}</span>
                              </div>
                              <Badge
                                variant={slot.available > 0 ? 'success' : 'danger'}
                              >
                                {slot.available}/{slot.max_quantity}
                              </Badge>
                            </div>
                            <div className="flex flex-wrap gap-1">
                              <Badge variant="info">{slot.level}</Badge>
                              <Badge variant="default">
                                {slot.wave_side.replace('Lado_', '')}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ))}
            </div>
          )}
        </>
      )}
    </MainLayout>
  );
}
