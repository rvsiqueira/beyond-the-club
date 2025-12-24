'use client';

import { useState, useEffect } from 'react';
import { GraduationCap, Waves, Calendar, Clock, Play, Square, CheckCircle, Radio, XCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from '@/components/ui';
import { useMembers, useSessionOptions, useStartSessionSearch, useSessionSearchWebSocket } from '@/hooks';
import { getTodayDate, getDateDaysFromNow, formatLevel, formatWaveSide } from '@/lib/utils';
import type { Member } from '@/types';

// Wave levels with visual configuration
const LEVELS = [
  { value: 'Iniciante1', label: 'Iniciante 1', shortLabel: 'Ini 1', color: 'bg-emerald-500', image: '/wave-levels/beginner-1.jpg' },
  { value: 'Iniciante2', label: 'Iniciante 2', shortLabel: 'Ini 2', color: 'bg-emerald-600', image: '/wave-levels/beginner-1.jpg' },
  { value: 'Intermediario1', label: 'Intermediario 1', shortLabel: 'Int 1', color: 'bg-blue-500', image: '/wave-levels/intermediate-1.jpg' },
  { value: 'Intermediario2', label: 'Intermediario 2', shortLabel: 'Int 2', color: 'bg-blue-600', image: '/wave-levels/intermediate-1.jpg' },
  { value: 'Avançado1', label: 'Avancado 1', shortLabel: 'Ava 1', color: 'bg-purple-500', image: '/wave-levels/advanced-1.jpg' },
  { value: 'Avançado2', label: 'Avancado 2', shortLabel: 'Ava 2', color: 'bg-purple-600', image: '/wave-levels/advanced-1.jpg' },
];

const WAVE_SIDES = [
  { value: 'Lado_esquerdo', label: 'Esquerda', icon: '←' },
  { value: 'Lado_direito', label: 'Direita', icon: '→' },
];

const DURATIONS = [60, 120, 180];

export function SessionSearchForm() {
  const { data: membersData, isLoading: membersLoading } = useMembers();
  const { data: sessionOptions, isLoading: optionsLoading } = useSessionOptions();
  const startMutation = useStartSessionSearch();

  // Form state
  const [selectedMember, setSelectedMember] = useState<number | null>(null);
  const [selectedLevel, setSelectedLevel] = useState<string>('');
  const [selectedDate, setSelectedDate] = useState<string>(getTodayDate());
  const [selectedWaveSide, setSelectedWaveSide] = useState<string>('');
  const [selectedHour, setSelectedHour] = useState<string>('');
  const [duration, setDuration] = useState(120);

  // Monitor state
  const [monitorId, setMonitorId] = useState<string | null>(null);

  const { messages, isConnected, status, result, connect, disconnect, sendStop, reset } =
    useSessionSearchWebSocket(monitorId);

  // Available members (without booking)
  const availableMembers = membersData?.members.filter((m) => !m.has_booking) ?? [];

  // Get available hours for selected level
  const availableHours = selectedLevel && sessionOptions?.hours_by_level
    ? sessionOptions.hours_by_level[selectedLevel] || []
    : [];

  // Reset hour when level changes
  useEffect(() => {
    setSelectedHour('');
  }, [selectedLevel]);

  // Connect WebSocket when monitorId is set
  useEffect(() => {
    if (monitorId) {
      connect();
    }
    return () => disconnect();
  }, [monitorId, connect, disconnect]);

  const handleStart = async () => {
    if (!selectedMember || !selectedLevel || !selectedDate) return;

    // Validate hour is selected if available hours exist
    if (availableHours.length > 0 && !selectedHour) return;

    const request = {
      member_id: selectedMember,
      level: selectedLevel,
      target_date: selectedDate,
      target_hour: selectedHour || availableHours[0],
      wave_side: selectedWaveSide || undefined,
      auto_book: true,
      duration_minutes: duration,
    };

    try {
      const res = await startMutation.mutateAsync(request);
      setMonitorId(res.monitor_id);
    } catch (err) {
      console.error('Failed to start session search:', err);
    }
  };

  const handleStop = () => {
    sendStop();
  };

  const handleReset = () => {
    setMonitorId(null);
    reset();
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'running':
        return <Radio className="h-5 w-5 text-primary-600 animate-pulse" />;
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  const isFormValid = selectedMember && selectedLevel && selectedDate && (availableHours.length === 0 || selectedHour);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Configuration Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GraduationCap className="h-5 w-5" />
            Busca de Sessao Especifica
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Member Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Membro *
            </label>
            {membersLoading ? (
              <div className="animate-pulse h-10 bg-gray-100 rounded-lg" />
            ) : availableMembers.length === 0 ? (
              <p className="text-gray-500 text-sm">Nenhum membro disponivel</p>
            ) : (
              <select
                value={selectedMember || ''}
                onChange={(e) => setSelectedMember(Number(e.target.value) || null)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                disabled={status === 'running'}
              >
                <option value="">Selecione um membro</option>
                {availableMembers.map((member) => (
                  <option key={member.member_id} value={member.member_id}>
                    {member.social_name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Level Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
              <GraduationCap className="h-4 w-4" />
              Nivel da Onda *
            </label>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
              {LEVELS.map((level) => {
                const isSelected = selectedLevel === level.value;
                return (
                  <button
                    key={level.value}
                    onClick={() => setSelectedLevel(level.value)}
                    disabled={status === 'running'}
                    className={`relative h-16 rounded-xl overflow-hidden transition-all ${
                      isSelected ? 'ring-2 ring-primary-500 ring-offset-2' : 'hover:opacity-90'
                    } ${status === 'running' ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    <div
                      className="absolute inset-0 bg-cover bg-center"
                      style={{ backgroundImage: `url(${level.image})` }}
                    />
                    <div className={`absolute inset-0 ${isSelected ? 'bg-black/40' : 'bg-black/50'}`} />
                    <div className="relative h-full flex flex-col items-center justify-center">
                      <span className="text-white text-xs font-bold">{level.shortLabel}</span>
                      {isSelected && (
                        <div className="absolute top-1 right-1 w-4 h-4 bg-primary-500 rounded-full flex items-center justify-center">
                          <span className="text-white text-[10px]">✓</span>
                        </div>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Date Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Data *
            </label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              min={getTodayDate()}
              max={getDateDaysFromNow(30)}
              disabled={status === 'running'}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50"
            />
          </div>

          {/* Wave Side Selection (Optional) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
              <Waves className="h-4 w-4" />
              Lado da Onda (opcional)
            </label>
            <div className="flex gap-3">
              <button
                onClick={() => setSelectedWaveSide('')}
                disabled={status === 'running'}
                className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl border-2 transition-all ${
                  selectedWaveSide === ''
                    ? 'border-primary-500 bg-primary-50 text-primary-700'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                } ${status === 'running' ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <span className="font-medium">Ambos</span>
              </button>
              {WAVE_SIDES.map((side) => {
                const isSelected = selectedWaveSide === side.value;
                return (
                  <button
                    key={side.value}
                    onClick={() => setSelectedWaveSide(side.value)}
                    disabled={status === 'running'}
                    className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl border-2 transition-all ${
                      isSelected
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                    } ${status === 'running' ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    <span className="text-2xl">{side.icon}</span>
                    <span className="font-medium">{side.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Hour Selection (Optional, filtered by level) */}
          {selectedLevel && availableHours.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Horario (opcional)
              </label>
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => setSelectedHour('')}
                  disabled={status === 'running'}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    selectedHour === ''
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  } ${status === 'running' ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  Qualquer
                </button>
                {availableHours.map((hour) => (
                  <button
                    key={hour}
                    onClick={() => setSelectedHour(hour)}
                    disabled={status === 'running'}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      selectedHour === hour
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    } ${status === 'running' ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    {hour}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Duration */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Duracao da busca
            </label>
            <div className="flex gap-2">
              {DURATIONS.map((d) => (
                <button
                  key={d}
                  onClick={() => setDuration(d)}
                  disabled={status === 'running'}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    duration === d
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  } ${status === 'running' ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  {d}min
                </button>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="pt-4 border-t border-gray-200">
            {status === 'running' ? (
              <Button variant="danger" className="w-full" onClick={handleStop}>
                <Square className="h-4 w-4 mr-2" /> Parar Busca
              </Button>
            ) : status === 'completed' || status === 'error' ? (
              <Button variant="outline" className="w-full" onClick={handleReset}>
                Nova Busca
              </Button>
            ) : (
              <Button
                variant="primary"
                className="w-full"
                onClick={handleStart}
                disabled={!isFormValid}
                isLoading={startMutation.isPending}
              >
                <Play className="h-4 w-4 mr-2" /> Iniciar Busca
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Status & Logs */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {getStatusIcon()}
            Status da Busca
            {isConnected && (
              <Badge variant="success" className="ml-2">
                Conectado
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!monitorId ? (
            <div className="text-center py-12">
              <Radio className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">
                Configure e inicie a busca para ver os logs
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Monitor ID */}
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm text-gray-500">Monitor ID</span>
                <code className="text-sm font-mono">{monitorId}</code>
              </div>

              {/* Status */}
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm text-gray-500">Status</span>
                <Badge
                  variant={
                    status === 'running'
                      ? 'info'
                      : status === 'completed'
                      ? 'success'
                      : status === 'error'
                      ? 'danger'
                      : 'default'
                  }
                >
                  {status}
                </Badge>
              </div>

              {/* Result */}
              {result && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-sm font-medium text-green-800 mb-2">Sessao Encontrada!</p>
                  {result.voucher && (
                    <p className="text-xs text-green-700">Voucher: {String(result.voucher)}</p>
                  )}
                  {result.slot && (
                    <div className="text-xs text-green-700 mt-1">
                      <p>Data: {(result.slot as any).date} - {(result.slot as any).interval}</p>
                      <p>Nivel: {formatLevel((result.slot as any).level)}</p>
                      <p>Lado: {formatWaveSide((result.slot as any).wave_side)}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Logs */}
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Logs</p>
                <div className="bg-gray-900 rounded-lg p-4 h-64 overflow-y-auto font-mono text-sm">
                  {messages.length === 0 ? (
                    <p className="text-gray-500">Aguardando mensagens...</p>
                  ) : (
                    messages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`mb-1 ${
                          msg.type === 'error'
                            ? 'text-red-400'
                            : msg.type === 'completed'
                            ? 'text-green-400'
                            : msg.level === 'error'
                            ? 'text-red-400'
                            : msg.level === 'success'
                            ? 'text-green-400'
                            : msg.level === 'warning'
                            ? 'text-yellow-400'
                            : 'text-gray-300'
                        }`}
                      >
                        [{msg.type}] {msg.message || JSON.stringify(msg)}
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
