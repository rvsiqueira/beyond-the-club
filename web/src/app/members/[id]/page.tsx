'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Trash2, Plus, GraduationCap, Waves, ArrowUp, ArrowDown, Check, Pencil, X, Copy } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle, Button } from '@/components/ui';
import { useMember, useMemberPreferences, useUpdatePreferences, useDeletePreferences, useBookings } from '@/hooks';
import { useAuthStore } from '@/lib/store';
import { formatDate } from '@/lib/utils';

// Wave images by level
const getWaveBackground = (level?: string) => {
  if (level?.startsWith('Iniciante')) {
    return '/wave-levels/beginner-1.jpg';
  } else if (level?.startsWith('Intermediario')) {
    return '/wave-levels/intermediate-1.jpg';
  } else {
    return '/wave-levels/advanced-1.jpg';
  }
};

// Format level for display
const formatLevel = (level?: string) => {
  if (!level) return '';
  return level.replace('Iniciante', 'Iniciante ').replace('Intermediario', 'Intermediário ').replace('Avançado', 'Avançado ').trim();
};

// Format wave side for display
const formatWaveSide = (waveSide?: string) => {
  if (!waveSide) return '';
  return waveSide.replace('Lado_', '').replace('esquerdo', 'Esquerdo').replace('direito', 'Direito');
};

// Wave levels with visual configuration
const LEVELS = [
  { value: 'Iniciante1', label: 'Iniciante 1', shortLabel: 'Ini 1', color: 'bg-emerald-500', image: '/wave-levels/beginner-1.jpg' },
  { value: 'Iniciante2', label: 'Iniciante 2', shortLabel: 'Ini 2', color: 'bg-emerald-600', image: '/wave-levels/beginner-1.jpg' },
  { value: 'Intermediario1', label: 'Intermediário 1', shortLabel: 'Int 1', color: 'bg-blue-500', image: '/wave-levels/intermediate-1.jpg' },
  { value: 'Intermediario2', label: 'Intermediário 2', shortLabel: 'Int 2', color: 'bg-blue-600', image: '/wave-levels/intermediate-1.jpg' },
  { value: 'Avançado1', label: 'Avançado 1', shortLabel: 'Ava 1', color: 'bg-purple-500', image: '/wave-levels/advanced-1.jpg' },
  { value: 'Avançado2', label: 'Avançado 2', shortLabel: 'Ava 2', color: 'bg-purple-600', image: '/wave-levels/advanced-1.jpg' },
];

const WAVE_SIDES = [
  { value: 'Lado_esquerdo', label: 'Esquerda', icon: '←' },
  { value: 'Lado_direito', label: 'Direita', icon: '→' },
];

interface PreferenceSession {
  level: string;
  wave_side: string;
  priority: number;
}

export default function MemberDetailPage() {
  const params = useParams();
  const router = useRouter();
  const memberId = parseInt(params.id as string);
  const sport = useAuthStore((state) => state.sport);

  const { data: member, isLoading: memberLoading } = useMember(memberId);
  const { data: preferences, isLoading: prefsLoading } = useMemberPreferences(memberId);
  const { data: bookingsData } = useBookings();
  const updateMutation = useUpdatePreferences(memberId);
  const deleteMutation = useDeletePreferences(memberId);

  // Find the member's next booking
  const memberBooking = bookingsData?.bookings.find(b => b.member_id === memberId);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const copyToClipboard = (text: string, codeId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(codeId);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  // Calculate days until booking
  const getDaysLabel = (date: string) => {
    const daysUntil = Math.ceil((new Date(date).getTime() - new Date().setHours(0,0,0,0)) / (1000 * 60 * 60 * 24));
    return daysUntil === 0 ? 'Hoje' : daysUntil === 1 ? 'Amanhã' : `Em ${daysUntil} dias`;
  };

  const [sessions, setSessions] = useState<PreferenceSession[]>([]);
  const [expandedSession, setExpandedSession] = useState<number | null>(null);
  const [savedSessionCount, setSavedSessionCount] = useState<number>(0); // Track how many sessions are saved
  const [originalSessions, setOriginalSessions] = useState<PreferenceSession[]>([]); // Track original state to detect changes
  const skipNextRefresh = useRef(false); // Flag to skip useEffect refresh after local changes

  // Initialize form with existing preferences
  useEffect(() => {
    if (!preferences) return;

    // Skip refresh if we just saved locally and are waiting for API to sync
    if (skipNextRefresh.current) {
      skipNextRefresh.current = false;
      return;
    }

    // API returns { member_id, sport, preferences: { sessions } }
    type ApiPrefsResponse = {
      preferences?: {
        sessions?: Array<{
          level?: string;
          wave_side?: string;
          attributes?: { level?: string; wave_side?: string };
        }>;
      };
      sessions?: Array<{
        level?: string;
        wave_side?: string;
        attributes?: { level?: string; wave_side?: string };
      }>;
    };
    const apiResponse = preferences as unknown as ApiPrefsResponse;
    const prefsData = apiResponse.preferences || apiResponse;
    const sessionsData = prefsData?.sessions || [];

    const loadedSessions = sessionsData.map((s, idx: number) => ({
      level: s.level || s.attributes?.level || LEVELS[0].value,
      wave_side: s.wave_side || s.attributes?.wave_side || WAVE_SIDES[0].value,
      priority: idx + 1,
    }));
    setSessions(loadedSessions);
    setOriginalSessions(JSON.parse(JSON.stringify(loadedSessions))); // Deep copy for comparison
    setSavedSessionCount(loadedSessions.length); // All loaded sessions are saved
    // Keep all cards closed when loading existing preferences
    setExpandedSession(null);
  }, [preferences]);

  // Save all current sessions - defined first so it can be used by other functions
  const saveAllSessions = useCallback(async (sessionsToSave: PreferenceSession[]) => {
    if (sessionsToSave.length === 0) return;

    try {
      await updateMutation.mutateAsync({
        sessions: sessionsToSave.map((s: PreferenceSession) => ({
          level: s.level,
          wave_side: s.wave_side,
        })),
      });
      setSavedSessionCount(sessionsToSave.length);
      setOriginalSessions(JSON.parse(JSON.stringify(sessionsToSave))); // Update original after save
    } catch (error) {
      console.error('Failed to save preferences:', error);
    }
  }, [updateMutation]);

  const addSession = async () => {
    // Save existing sessions before adding new one
    if (sessions.length > 0) {
      skipNextRefresh.current = true; // Don't reset state after save
      await saveAllSessions(sessions);
    }

    const newSession: PreferenceSession = {
      level: LEVELS[0].value,
      wave_side: WAVE_SIDES[0].value,
      priority: sessions.length + 1,
    };
    setSessions([...sessions, newSession]);
    setExpandedSession(sessions.length);
  };

  const moveSession = useCallback(async (index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= sessions.length) return;

    const newSessions = [...sessions];
    const temp = newSessions[index];
    newSessions[index] = newSessions[newIndex];
    newSessions[newIndex] = temp;

    // Update priorities
    const updatedSessions = newSessions.map((s, i) => ({ ...s, priority: i + 1 }));
    setSessions(updatedSessions);

    // Update expanded session to follow the moved item
    if (expandedSession === index) {
      setExpandedSession(newIndex);
    } else if (expandedSession === newIndex) {
      setExpandedSession(index);
    }

    // Auto-save after reordering
    skipNextRefresh.current = true;
    await saveAllSessions(updatedSessions);
  }, [sessions, expandedSession, saveAllSessions]);

  const updateSession = (index: number, field: keyof PreferenceSession, value: string | number) => {
    const updated = [...sessions];
    updated[index] = { ...updated[index], [field]: value };
    setSessions(updated);
  };

  // Add session to saved (mark as saved)
  const handleAddSession = async () => {
    skipNextRefresh.current = true;
    await saveAllSessions(sessions);
  };

  // Remove a session and save
  const handleRemoveSession = async (index: number) => {
    const newSessions = sessions.filter((_: PreferenceSession, i: number) => i !== index).map((s: PreferenceSession, i: number) => ({ ...s, priority: i + 1 }));
    setSessions(newSessions);

    // Keep all cards closed after removing
    setExpandedSession(null);

    // Always update the backend when removing
    if (newSessions.length === 0) {
      await deleteMutation.mutateAsync();
      setSavedSessionCount(0);
    } else {
      await saveAllSessions(newSessions);
    }
  };

  const isLoading = memberLoading || prefsLoading;

  const getLevelConfig = (level: string) => LEVELS.find(l => l.value === level) || LEVELS[0];
  const getWaveSideConfig = (side: string) => WAVE_SIDES.find(w => w.value === side) || WAVE_SIDES[0];

  return (
    <MainLayout title="Detalhes do Membro">
      {/* Back Button */}
      <Button
        variant="ghost"
        onClick={() => router.back()}
        className="mb-4"
      >
        <ArrowLeft className="h-4 w-4 mr-2" /> Voltar
      </Button>

      {isLoading ? (
        <div className="animate-pulse space-y-6">
          <div className="h-32 bg-gray-100 rounded-xl" />
          <div className="h-64 bg-gray-100 rounded-xl" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Member Info Card with Background */}
          <div className="relative rounded-2xl overflow-hidden shadow-lg">
            <div
              className="absolute inset-0 bg-cover bg-center"
              style={{ backgroundImage: 'url(/surf-backgrounds/surf-1.jpg)' }}
            />
            <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/60 to-black/40" />

            <div className="relative p-6">
              <div className="flex items-center gap-4">
                <div className="w-20 h-20 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center">
                  <span className="text-white font-bold text-2xl">
                    {member?.social_name[0]}
                  </span>
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-white">
                    {member?.social_name}
                  </h2>
                  <p className="text-white/70">{member?.name}</p>
                  <div className="flex gap-2 mt-2">
                    {member?.is_titular && (
                      <span className="px-2.5 py-1 bg-blue-500/40 backdrop-blur-sm rounded-full text-xs font-semibold text-white">
                        Titular
                      </span>
                    )}
                    {member?.has_booking && (
                      <span className="px-2.5 py-1 bg-green-500/40 backdrop-blur-sm rounded-full text-xs font-semibold text-white">
                        Agendado
                      </span>
                    )}
                    <span className="px-2.5 py-1 bg-white/20 backdrop-blur-sm rounded-full text-xs font-semibold text-white">
                      {member?.usage}/{member?.limit} usos
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Next Booking Card */}
          {memberBooking && (
            <div className="relative rounded-2xl overflow-hidden shadow-lg">
              {/* Background Image */}
              <div
                className="absolute inset-0 bg-cover bg-center"
                style={{ backgroundImage: `url(${getWaveBackground(memberBooking.level)})` }}
              />
              {/* Gradient Overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-black/30" />

              {/* Content */}
              <div className="relative p-5 min-h-[180px] flex flex-col justify-between">
                {/* Top Row */}
                <div className="flex items-start justify-between">
                  {/* Days Badge */}
                  <span className="px-3 py-1.5 bg-white/95 backdrop-blur-sm rounded-full text-xs font-bold text-gray-800 shadow-sm">
                    {getDaysLabel(memberBooking.date)}
                  </span>

                  {/* X icon */}
                  <div className="p-2 bg-white/20 backdrop-blur-sm rounded-full">
                    <X className="h-4 w-4 text-white" />
                  </div>
                </div>

                {/* Bottom Content */}
                <div>
                  {/* Date & Time */}
                  <p className="text-white/80 text-sm mb-1">
                    {formatDate(memberBooking.date)} · {memberBooking.interval}
                  </p>

                  {/* Member Name */}
                  <h3 className="text-white text-2xl font-bold mb-2">
                    {memberBooking.member_name}
                  </h3>

                  {/* Tags */}
                  <div className="flex flex-wrap gap-2 mb-3">
                    {memberBooking.level && (
                      <span className="px-2.5 py-1 bg-white/20 backdrop-blur-sm rounded-full text-xs font-semibold text-white flex items-center gap-1">
                        <GraduationCap className="h-3 w-3" />
                        {formatLevel(memberBooking.level)}
                      </span>
                    )}
                    {memberBooking.wave_side && (
                      <span className="px-2.5 py-1 bg-white/20 backdrop-blur-sm rounded-full text-xs font-semibold text-white flex items-center gap-1">
                        <Waves className="h-3 w-3" />
                        {formatWaveSide(memberBooking.wave_side)}
                      </span>
                    )}
                  </div>

                  {/* Codes */}
                  <div className="flex items-center gap-3 pt-3 border-t border-white/20">
                    <div className="flex-1">
                      <p className="text-white/60 text-[10px] uppercase tracking-wider mb-0.5">Voucher</p>
                      <div className="flex items-center gap-1">
                        <code className="text-white text-xs font-mono font-medium">{memberBooking.voucher_code}</code>
                        <button
                          onClick={() => copyToClipboard(memberBooking.voucher_code, 'voucher')}
                          className="p-1 hover:bg-white/20 rounded transition-colors"
                        >
                          {copiedCode === 'voucher' ? (
                            <Check className="h-3 w-3 text-green-400" />
                          ) : (
                            <Copy className="h-3 w-3 text-white/60" />
                          )}
                        </button>
                      </div>
                    </div>
                    <div className="flex-1">
                      <p className="text-white/60 text-[10px] uppercase tracking-wider mb-0.5">Acesso</p>
                      <div className="flex items-center gap-1">
                        <code className="text-white text-xs font-mono font-medium">{memberBooking.access_code}</code>
                        <button
                          onClick={() => copyToClipboard(memberBooking.access_code, 'access')}
                          className="p-1 hover:bg-white/20 rounded transition-colors"
                        >
                          {copiedCode === 'access' ? (
                            <Check className="h-3 w-3 text-green-400" />
                          ) : (
                            <Copy className="h-3 w-3 text-white/60" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Preferences */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <GraduationCap className="h-5 w-5" />
                Preferências ({sport})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Sessions List */}
              {sessions.length === 0 ? (
                <div className="text-center py-8">
                  <GraduationCap className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500 mb-4">Nenhuma preferência configurada</p>
                  <Button variant="primary" onClick={addSession}>
                    <Plus className="h-4 w-4 mr-1" /> Adicionar Preferência
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  {sessions.map((session, index) => {
                    const levelConfig = getLevelConfig(session.level);
                    const waveSideConfig = getWaveSideConfig(session.wave_side);
                    const isExpanded = expandedSession === index;

                    return (
                      <div
                        key={index}
                        className="border border-gray-200 rounded-xl overflow-hidden"
                      >
                        {/* Session Header - Always visible */}
                        <div
                          className="flex items-center gap-3 p-4 hover:bg-gray-50 transition-colors"
                        >
                          {/* Reorder Buttons */}
                          <div className="flex flex-col gap-0.5 flex-shrink-0">
                            <button
                              onClick={(e) => { e.stopPropagation(); moveSession(index, 'up'); }}
                              disabled={index === 0}
                              className={`p-1 rounded transition-colors ${index === 0 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:bg-gray-200 hover:text-gray-700'}`}
                              title="Mover para cima"
                            >
                              <ArrowUp className="h-4 w-4" />
                            </button>
                            <button
                              onClick={(e) => { e.stopPropagation(); moveSession(index, 'down'); }}
                              disabled={index === sessions.length - 1}
                              className={`p-1 rounded transition-colors ${index === sessions.length - 1 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:bg-gray-200 hover:text-gray-700'}`}
                              title="Mover para baixo"
                            >
                              <ArrowDown className="h-4 w-4" />
                            </button>
                          </div>

                          {/* Priority Badge */}
                          <div
                            onClick={() => setExpandedSession(isExpanded ? null : index)}
                            className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0 cursor-pointer"
                          >
                            <span className="text-sm font-bold text-gray-600">#{session.priority}</span>
                          </div>

                          {/* Content area */}
                          <div className="flex-1 flex items-center gap-3">
                            {/* Level Preview */}
                            <div className="relative h-12 w-20 rounded-lg overflow-hidden flex-shrink-0">
                              <div
                                className="absolute inset-0 bg-cover bg-center"
                                style={{ backgroundImage: `url(${levelConfig.image})` }}
                              />
                              <div className="absolute inset-0 bg-black/30" />
                              <div className="relative h-full flex items-center justify-center">
                                <span className="text-white text-xs font-bold">{levelConfig.shortLabel}</span>
                              </div>
                            </div>

                            {/* Wave Side */}
                            <div className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 rounded-full">
                              <Waves className="h-3.5 w-3.5 text-gray-600" />
                              <span className="text-sm font-medium text-gray-700">{waveSideConfig.label}</span>
                            </div>
                          </div>

                          {/* Action Icons */}
                          <div className="flex items-center gap-1 flex-shrink-0">
                            <button
                              onClick={(e) => { e.stopPropagation(); setExpandedSession(isExpanded ? null : index); }}
                              className="p-2 rounded-lg text-gray-500 hover:bg-blue-50 hover:text-blue-600 transition-colors"
                              title="Editar"
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                            <button
                              onClick={(e) => { e.stopPropagation(); handleRemoveSession(index); }}
                              className="p-2 rounded-lg text-gray-500 hover:bg-red-50 hover:text-red-600 transition-colors"
                              title="Excluir"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </div>

                        {/* Expanded Content */}
                        {isExpanded && (
                          <div className="border-t border-gray-200 p-4 bg-gray-50 space-y-6">
                            {/* Level Selection */}
                            <div>
                              <label className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
                                <GraduationCap className="h-4 w-4" />
                                Nível da Onda
                              </label>
                              <div className="grid grid-cols-3 md:grid-cols-6 gap-2 mt-2">
                                {LEVELS.map((level) => {
                                  const isSelected = session.level === level.value;
                                  return (
                                    <button
                                      key={level.value}
                                      onClick={() => updateSession(index, 'level', level.value)}
                                      className={`relative h-20 rounded-xl overflow-hidden transition-all ${
                                        isSelected ? 'ring-2 ring-primary-500 ring-offset-2' : 'hover:opacity-90'
                                      }`}
                                    >
                                      <div
                                        className="absolute inset-0 bg-cover bg-center"
                                        style={{ backgroundImage: `url(${level.image})` }}
                                      />
                                      <div className={`absolute inset-0 ${isSelected ? 'bg-black/40' : 'bg-black/50'}`} />
                                      <div className="relative h-full flex flex-col items-center justify-center">
                                        <span className="text-white text-xs font-bold">{level.label}</span>
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

                            {/* Wave Side Selection */}
                            <div>
                              <label className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
                                <Waves className="h-4 w-4" />
                                Lado da Onda
                              </label>
                              <div className="flex gap-3 mt-2">
                                {WAVE_SIDES.map((side) => {
                                  const isSelected = session.wave_side === side.value;
                                  return (
                                    <button
                                      key={side.value}
                                      onClick={() => updateSession(index, 'wave_side', side.value)}
                                      className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl border-2 transition-all ${
                                        isSelected
                                          ? 'border-primary-500 bg-primary-50 text-primary-700'
                                          : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                                      }`}
                                    >
                                      <span className="text-2xl">{side.icon}</span>
                                      <span className="font-medium">{side.label}</span>
                                    </button>
                                  );
                                })}
                              </div>
                            </div>

                            {/* Save/Cancel Buttons */}
                            <div className="pt-4 border-t border-gray-200 flex gap-2">
                              <Button
                                variant="primary"
                                size="sm"
                                onClick={() => { handleAddSession(); setExpandedSession(null); }}
                                isLoading={updateMutation.isPending}
                              >
                                <Check className="h-4 w-4 mr-1" /> Salvar
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  // Restore original values if it's a saved session
                                  if (index < savedSessionCount && originalSessions[index]) {
                                    const updated = [...sessions];
                                    updated[index] = { ...originalSessions[index] };
                                    setSessions(updated);
                                  } else {
                                    // Remove unsaved new session
                                    const newSessions = sessions.filter((_: PreferenceSession, i: number) => i !== index);
                                    setSessions(newSessions);
                                  }
                                  setExpandedSession(null);
                                }}
                              >
                                <X className="h-4 w-4 mr-1" /> Cancelar
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {/* Add Another Session */}
                  <Button
                    variant="outline"
                    onClick={addSession}
                    className="w-full"
                  >
                    <Plus className="h-4 w-4 mr-1" /> Adicionar Outra Preferência
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </MainLayout>
  );
}
