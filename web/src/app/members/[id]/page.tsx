'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Save, Trash2, Plus } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle, Button, Input, Select, Badge } from '@/components/ui';
import { useMember, useMemberPreferences, useUpdatePreferences, useDeletePreferences } from '@/hooks';
import { useAuthStore } from '@/lib/store';
import type { SessionPreference } from '@/types';

const LEVELS = [
  { value: 'Iniciante1', label: 'Iniciante 1' },
  { value: 'Iniciante2', label: 'Iniciante 2' },
  { value: 'Intermediario1', label: 'Intermediario 1' },
  { value: 'Intermediario2', label: 'Intermediario 2' },
  { value: 'Avançado1', label: 'Avancado 1' },
  { value: 'Avançado2', label: 'Avancado 2' },
];

const WAVE_SIDES = [
  { value: 'Lado_esquerdo', label: 'Lado Esquerdo' },
  { value: 'Lado_direito', label: 'Lado Direito' },
];

const HOURS = [
  { value: '08:00', label: '08:00' },
  { value: '09:00', label: '09:00' },
  { value: '10:00', label: '10:00' },
  { value: '11:00', label: '11:00' },
  { value: '12:00', label: '12:00' },
  { value: '13:00', label: '13:00' },
  { value: '14:00', label: '14:00' },
  { value: '15:00', label: '15:00' },
  { value: '16:00', label: '16:00' },
  { value: '17:00', label: '17:00' },
];

export default function MemberDetailPage() {
  const params = useParams();
  const router = useRouter();
  const memberId = parseInt(params.id as string);
  const sport = useAuthStore((state) => state.sport);

  const { data: member, isLoading: memberLoading } = useMember(memberId);
  const { data: preferences, isLoading: prefsLoading } = useMemberPreferences(memberId);
  const updateMutation = useUpdatePreferences(memberId);
  const deleteMutation = useDeletePreferences(memberId);

  const [sessions, setSessions] = useState<SessionPreference[]>([]);
  const [targetHours, setTargetHours] = useState<string[]>([]);
  const [targetDates, setTargetDates] = useState<string>('');
  const [initialized, setInitialized] = useState(false);

  // Initialize form with existing preferences
  if (preferences && !initialized) {
    setSessions(preferences.sessions || []);
    setTargetHours(preferences.target_hours || []);
    setTargetDates(preferences.target_dates?.join(', ') || '');
    setInitialized(true);
  }

  const addSession = () => {
    setSessions([
      ...sessions,
      { level: LEVELS[0].value, wave_side: WAVE_SIDES[0].value, priority: sessions.length + 1 },
    ]);
  };

  const removeSession = (index: number) => {
    setSessions(sessions.filter((_, i) => i !== index));
  };

  const updateSession = (index: number, field: keyof SessionPreference, value: string | number) => {
    const updated = [...sessions];
    updated[index] = { ...updated[index], [field]: value };
    setSessions(updated);
  };

  const toggleHour = (hour: string) => {
    if (targetHours.includes(hour)) {
      setTargetHours(targetHours.filter((h) => h !== hour));
    } else {
      setTargetHours([...targetHours, hour]);
    }
  };

  const handleSave = async () => {
    const dates = targetDates
      .split(',')
      .map((d) => d.trim())
      .filter((d) => d);

    await updateMutation.mutateAsync({
      member_id: memberId,
      sport,
      sessions,
      target_hours: targetHours,
      target_dates: dates,
    });
  };

  const handleDelete = async () => {
    if (confirm('Tem certeza que deseja remover as preferencias?')) {
      await deleteMutation.mutateAsync();
      setSessions([]);
      setTargetHours([]);
      setTargetDates('');
    }
  };

  const isLoading = memberLoading || prefsLoading;

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
          {/* Member Info */}
          <Card>
            <CardContent className="py-6">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center">
                  <span className="text-primary-600 font-bold text-xl">
                    {member?.social_name[0]}
                  </span>
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    {member?.social_name}
                  </h2>
                  <p className="text-gray-500">{member?.name}</p>
                  <div className="flex gap-2 mt-2">
                    {member?.is_titular && <Badge variant="info">Titular</Badge>}
                    {member?.has_booking && <Badge variant="success">Agendado</Badge>}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Preferences Form */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Preferencias ({sport})</CardTitle>
              <div className="flex gap-2">
                {preferences && (
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={handleDelete}
                    isLoading={deleteMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4 mr-1" /> Remover
                  </Button>
                )}
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleSave}
                  isLoading={updateMutation.isPending}
                >
                  <Save className="h-4 w-4 mr-1" /> Salvar
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Sessions */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h4 className="font-medium text-gray-900">Sessoes</h4>
                  <Button variant="outline" size="sm" onClick={addSession}>
                    <Plus className="h-4 w-4 mr-1" /> Adicionar
                  </Button>
                </div>

                {sessions.length === 0 ? (
                  <p className="text-gray-500 text-center py-4">
                    Nenhuma sessao configurada
                  </p>
                ) : (
                  <div className="space-y-4">
                    {sessions.map((session, index) => (
                      <div
                        key={index}
                        className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg"
                      >
                        <span className="text-sm font-medium text-gray-500 w-8">
                          #{session.priority}
                        </span>
                        <Select
                          value={session.level}
                          onChange={(e) => updateSession(index, 'level', e.target.value)}
                          options={LEVELS}
                          className="flex-1"
                        />
                        <Select
                          value={session.wave_side}
                          onChange={(e) => updateSession(index, 'wave_side', e.target.value)}
                          options={WAVE_SIDES}
                          className="flex-1"
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeSession(index)}
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Target Hours */}
              <div>
                <h4 className="font-medium text-gray-900 mb-4">Horarios Preferidos</h4>
                <div className="flex flex-wrap gap-2">
                  {HOURS.map((hour) => (
                    <button
                      key={hour.value}
                      onClick={() => toggleHour(hour.value)}
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        targetHours.includes(hour.value)
                          ? 'bg-primary-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {hour.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Target Dates */}
              <div>
                <Input
                  label="Datas Alvo (separadas por virgula)"
                  placeholder="2025-01-15, 2025-01-16"
                  value={targetDates}
                  onChange={(e) => setTargetDates(e.target.value)}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Formato: YYYY-MM-DD
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </MainLayout>
  );
}
