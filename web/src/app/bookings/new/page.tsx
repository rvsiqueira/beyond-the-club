'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, ArrowRight, Check, Calendar, User, Clock } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge, Select } from '@/components/ui';
import { useMembers, useAvailability, useCreateBooking } from '@/hooks';
import { formatDate } from '@/lib/utils';
import type { Member, AvailableSlot } from '@/types';

type Step = 'member' | 'slot' | 'confirm';

export default function NewBookingPage() {
  const router = useRouter();
  const { data: membersData, isLoading: membersLoading } = useMembers();
  const { data: availabilityData, isLoading: availabilityLoading } = useAvailability();
  const createMutation = useCreateBooking();

  const [step, setStep] = useState<Step>('member');
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<AvailableSlot | null>(null);
  const [dateFilter, setDateFilter] = useState('');
  const [levelFilter, setLevelFilter] = useState('');

  // Available members (without booking)
  const availableMembers = membersData?.members.filter((m) => !m.has_booking) ?? [];

  // Filter slots
  const filteredSlots = useMemo(() => {
    if (!availabilityData?.slots) return [];
    return availabilityData.slots.filter((slot) => {
      if (slot.available <= 0) return false;
      if (dateFilter && slot.date !== dateFilter) return false;
      if (levelFilter && slot.level !== levelFilter) return false;
      return true;
    });
  }, [availabilityData, dateFilter, levelFilter]);

  // Unique dates and levels
  const dates = useMemo(() => {
    if (!availabilityData?.slots) return [];
    const uniqueDates = [...new Set(availabilityData.slots.filter(s => s.available > 0).map((s) => s.date))];
    return uniqueDates.sort();
  }, [availabilityData]);

  const levels = useMemo(() => {
    if (!availabilityData?.slots) return [];
    return [...new Set(availabilityData.slots.map((s) => s.level))];
  }, [availabilityData]);

  const handleSubmit = async () => {
    if (!selectedMember || !selectedSlot) return;

    await createMutation.mutateAsync({
      member_id: selectedMember.member_id,
      date: selectedSlot.date,
      interval: selectedSlot.interval,
      level: selectedSlot.level,
      wave_side: selectedSlot.wave_side,
      package_id: selectedSlot.package_id,
      product_id: selectedSlot.product_id,
    });

    router.push('/bookings');
  };

  const steps = [
    { id: 'member', label: 'Membro', icon: User },
    { id: 'slot', label: 'Horario', icon: Calendar },
    { id: 'confirm', label: 'Confirmar', icon: Check },
  ];

  const currentStepIndex = steps.findIndex((s) => s.id === step);

  return (
    <MainLayout title="Novo Agendamento">
      {/* Back Button */}
      <Button variant="ghost" onClick={() => router.back()} className="mb-4">
        <ArrowLeft className="h-4 w-4 mr-2" /> Voltar
      </Button>

      {/* Steps */}
      <div className="flex items-center justify-center mb-8">
        {steps.map((s, idx) => (
          <div key={s.id} className="flex items-center">
            <div
              className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
                step === s.id
                  ? 'bg-primary-600 text-white'
                  : idx < currentStepIndex
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-500'
              }`}
            >
              <s.icon className="h-5 w-5" />
              <span className="font-medium">{s.label}</span>
            </div>
            {idx < steps.length - 1 && (
              <div className="w-12 h-px bg-gray-300 mx-2" />
            )}
          </div>
        ))}
      </div>

      {/* Step 1: Select Member */}
      {step === 'member' && (
        <Card>
          <CardHeader>
            <CardTitle>Selecione o Membro</CardTitle>
          </CardHeader>
          <CardContent>
            {membersLoading ? (
              <div className="animate-pulse space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-gray-100 rounded-lg" />
                ))}
              </div>
            ) : availableMembers.length === 0 ? (
              <p className="text-center text-gray-500 py-8">
                Todos os membros ja possuem agendamento
              </p>
            ) : (
              <div className="space-y-3">
                {availableMembers.map((member) => (
                  <button
                    key={member.member_id}
                    onClick={() => {
                      setSelectedMember(member);
                      setStep('slot');
                    }}
                    className={`w-full flex items-center justify-between p-4 rounded-lg border transition-colors ${
                      selectedMember?.member_id === member.member_id
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                        <span className="text-primary-600 font-medium">
                          {member.social_name[0]}
                        </span>
                      </div>
                      <div className="text-left">
                        <p className="font-medium text-gray-900">
                          {member.social_name}
                        </p>
                        <p className="text-sm text-gray-500">{member.name}</p>
                      </div>
                    </div>
                    {member.has_preferences && (
                      <Badge variant="success">Preferencias</Badge>
                    )}
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Step 2: Select Slot */}
      {step === 'slot' && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Selecione o Horario</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => setStep('member')}>
              <ArrowLeft className="h-4 w-4 mr-1" /> Voltar
            </Button>
          </CardHeader>
          <CardContent>
            {/* Filters */}
            <div className="flex gap-4 mb-6">
              <Select
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
                options={[
                  { value: '', label: 'Todas as datas' },
                  ...dates.map((d) => ({ value: d, label: formatDate(d) })),
                ]}
                className="w-48"
              />
              <Select
                value={levelFilter}
                onChange={(e) => setLevelFilter(e.target.value)}
                options={[
                  { value: '', label: 'Todos os niveis' },
                  ...levels.map((l) => ({ value: l, label: l })),
                ]}
                className="w-48"
              />
            </div>

            {availabilityLoading ? (
              <div className="animate-pulse space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-20 bg-gray-100 rounded-lg" />
                ))}
              </div>
            ) : filteredSlots.length === 0 ? (
              <p className="text-center text-gray-500 py-8">
                Nenhum slot disponivel
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredSlots.slice(0, 20).map((slot, idx) => (
                  <button
                    key={`${slot.date}-${slot.interval}-${slot.level}-${idx}`}
                    onClick={() => {
                      setSelectedSlot(slot);
                      setStep('confirm');
                    }}
                    className={`p-4 rounded-lg border text-left transition-colors ${
                      selectedSlot === slot
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-gray-400" />
                        <span className="font-medium">{formatDate(slot.date)}</span>
                      </div>
                      <Badge variant="success">
                        {slot.available} vagas
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 mb-2">
                      <Clock className="h-4 w-4 text-gray-400" />
                      <span className="text-lg font-semibold">{slot.interval}</span>
                    </div>
                    <div className="flex gap-2">
                      <Badge variant="info">{slot.level}</Badge>
                      <Badge variant="default">
                        {slot.wave_side.replace('Lado_', '')}
                      </Badge>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Step 3: Confirm */}
      {step === 'confirm' && selectedMember && selectedSlot && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Confirmar Agendamento</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => setStep('slot')}>
              <ArrowLeft className="h-4 w-4 mr-1" /> Voltar
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* Member Info */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500 mb-1">Membro</p>
                <p className="font-semibold text-lg">{selectedMember.social_name}</p>
                <p className="text-gray-500">{selectedMember.name}</p>
              </div>

              {/* Slot Info */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500 mb-1">Sessao</p>
                <div className="flex items-center gap-4">
                  <div>
                    <p className="font-semibold text-lg">
                      {formatDate(selectedSlot.date)}
                    </p>
                    <p className="text-gray-500">{selectedSlot.interval}</p>
                  </div>
                  <div className="flex gap-2">
                    <Badge variant="info">{selectedSlot.level}</Badge>
                    <Badge variant="default">
                      {selectedSlot.wave_side.replace('Lado_', '')}
                    </Badge>
                  </div>
                </div>
              </div>

              {/* Error */}
              {createMutation.error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-600">
                    {createMutation.error instanceof Error
                      ? createMutation.error.message
                      : 'Erro ao criar agendamento'}
                  </p>
                </div>
              )}

              {/* Submit */}
              <Button
                variant="primary"
                size="lg"
                className="w-full"
                onClick={handleSubmit}
                isLoading={createMutation.isPending}
              >
                <Check className="h-5 w-5 mr-2" /> Confirmar Agendamento
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </MainLayout>
  );
}
