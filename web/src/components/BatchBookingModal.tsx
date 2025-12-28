'use client';

import { useState, useEffect } from 'react';
import { Users, Check, AlertTriangle, GraduationCap, Waves, Clock, Calendar } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui';
import { useMembers, useCreateBooking } from '@/hooks';
import { formatDate } from '@/lib/utils';
import type { AvailableSlot } from '@/types';
import { useQueryClient } from '@tanstack/react-query';

interface BatchBookingModalProps {
  isOpen: boolean;
  onClose: () => void;
  slot: AvailableSlot | null;
  onSuccess: () => void;
}

// Wave images by level - fixed per level for quick visual identification
const getSlotBackground = (slot: AvailableSlot) => {
  if (slot.level.startsWith('Iniciante')) {
    return '/wave-levels/beginner-1.jpg';
  } else if (slot.level.startsWith('Intermediario')) {
    return '/wave-levels/intermediate-1.jpg';
  } else {
    return '/wave-levels/advanced-1.jpg';
  }
};

const formatLevel = (level?: string) => {
  if (!level) return null;
  return level.replace('Iniciante', 'Iniciante ').replace('Intermediario', 'Intermediário ').replace('Avançado', 'Avançado ').replace('Avancado', 'Avançado ').trim();
};

const formatWaveSide = (waveSide?: string) => {
  if (!waveSide) return null;
  return waveSide.replace('Lado_', '').replace('esquerdo', 'Esquerda').replace('direito', 'Direita');
};

export function BatchBookingModal({
  isOpen,
  onClose,
  slot,
  onSuccess,
}: BatchBookingModalProps) {
  const [selectedMemberIds, setSelectedMemberIds] = useState<number[]>([]);
  const [isBooking, setIsBooking] = useState(false);
  const [bookingResults, setBookingResults] = useState<{ memberId: number; success: boolean; error?: string }[]>([]);
  const queryClient = useQueryClient();
  const { data: membersData, refetch: refetchMembers } = useMembers();
  const createBookingMutation = useCreateBooking();

  // Refetch members when modal opens to ensure fresh data
  useEffect(() => {
    if (isOpen) {
      queryClient.invalidateQueries({ queryKey: ['members'] });
      refetchMembers();
    }
  }, [isOpen, queryClient, refetchMembers]);

  const handleClose = () => {
    setSelectedMemberIds([]);
    setBookingResults([]);
    setIsBooking(false);
    onClose();
  };

  const toggleMember = (memberId: number) => {
    if (selectedMemberIds.includes(memberId)) {
      setSelectedMemberIds(selectedMemberIds.filter(id => id !== memberId));
    } else {
      setSelectedMemberIds([...selectedMemberIds, memberId]);
    }
  };

  const handleBookAll = async () => {
    if (!slot || selectedMemberIds.length === 0) return;

    setIsBooking(true);
    setBookingResults([]);
    const results: { memberId: number; success: boolean; error?: string }[] = [];

    for (const memberId of selectedMemberIds) {
      try {
        await createBookingMutation.mutateAsync({
          member_id: memberId,
          date: slot.date,
          interval: slot.interval,
          level: slot.level,
          wave_side: slot.wave_side,
          package_id: slot.package_id,
          product_id: slot.product_id,
        });
        results.push({ memberId, success: true });
      } catch (error: unknown) {
        const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
        results.push({ memberId, success: false, error: errorMessage });
      }
    }

    setBookingResults(results);
    setIsBooking(false);

    const successCount = results.filter(r => r.success).length;
    if (successCount > 0) {
      onSuccess();
    }
  };

  // Filter members that can receive a booking:
  // - Don't have active bookings (has_booking = false)
  const availableMembers = membersData?.members.filter(
    (m) => !m.has_booking
  ) ?? [];

  const selectedCount = selectedMemberIds.length;
  const availableVacancies = slot?.available ?? 0;
  const isOverLimit = selectedCount > availableVacancies;

  if (!slot) return null;

  const hasResults = bookingResults.length > 0;
  const successCount = bookingResults.filter(r => r.success).length;
  const failCount = bookingResults.filter(r => !r.success).length;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={hasResults ? 'Resultado do Agendamento' : 'Agendar Sessão'}
    >
      <div className="space-y-6">
        {/* Slot Card with Image */}
        <div className="relative h-32 rounded-xl overflow-hidden">
          {/* Background Image */}
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{ backgroundImage: `url(${getSlotBackground(slot)})` }}
          />
          {/* Gradient Overlay */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-black/20" />

          {/* Content */}
          <div className="relative h-full p-4 flex flex-col justify-between">
            {/* Top - Availability Badge */}
            <div className="flex justify-between items-start">
              <span className="px-3 py-1.5 bg-white/95 backdrop-blur-sm rounded-full text-xs font-bold text-gray-800 shadow-sm flex items-center gap-1">
                <Users className="h-3 w-3" />
                {slot.available} vagas
              </span>
            </div>

            {/* Bottom - Slot Info */}
            <div>
              <div className="flex items-center gap-2 text-white/80 text-sm mb-1">
                <Calendar className="h-3.5 w-3.5" />
                {formatDate(slot.date)}
                <span className="mx-1">·</span>
                <Clock className="h-3.5 w-3.5" />
                {slot.interval}
              </div>
              <div className="flex gap-2">
                {slot.level && (
                  <span className="px-2.5 py-1 bg-white/20 backdrop-blur-sm rounded-full text-xs font-medium text-white flex items-center gap-1">
                    <GraduationCap className="h-3 w-3" />
                    {formatLevel(slot.level)}
                  </span>
                )}
                {slot.wave_side && (
                  <span className="px-2.5 py-1 bg-white/20 backdrop-blur-sm rounded-full text-xs font-medium text-white flex items-center gap-1">
                    <Waves className="h-3 w-3" />
                    {formatWaveSide(slot.wave_side)}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Results View */}
        {hasResults ? (
          <div className="space-y-4">
            {/* Summary */}
            <div className={`p-4 rounded-lg ${failCount > 0 ? 'bg-yellow-50' : 'bg-green-50'}`}>
              <p className={`font-medium ${failCount > 0 ? 'text-yellow-800' : 'text-green-800'}`}>
                {successCount > 0 && `${successCount} agendamento${successCount > 1 ? 's' : ''} realizado${successCount > 1 ? 's' : ''} com sucesso!`}
                {failCount > 0 && successCount > 0 && ' '}
                {failCount > 0 && `${failCount} falha${failCount > 1 ? 's' : ''}.`}
              </p>
            </div>

            {/* Individual Results */}
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {bookingResults.map((result) => {
                const member = membersData?.members.find(m => m.member_id === result.memberId);
                return (
                  <div
                    key={result.memberId}
                    className={`p-3 rounded-lg flex items-center justify-between ${
                      result.success ? 'bg-green-50' : 'bg-red-50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                        result.success ? 'bg-green-100' : 'bg-red-100'
                      }`}>
                        {result.success ? (
                          <Check className="h-4 w-4 text-green-600" />
                        ) : (
                          <AlertTriangle className="h-4 w-4 text-red-600" />
                        )}
                      </div>
                      <span className="font-medium text-gray-900">
                        {member?.social_name || `Membro ${result.memberId}`}
                      </span>
                    </div>
                    {result.error && (
                      <span className="text-xs text-red-600">{result.error}</span>
                    )}
                  </div>
                );
              })}
            </div>

            <Button variant="primary" className="w-full" onClick={handleClose}>
              Fechar
            </Button>
          </div>
        ) : (
          <>
            {/* Member Selection */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <p className="text-gray-600 text-sm">
                  Selecione os membros para agendar:
                </p>
                <span className={`text-xs font-medium px-2 py-1 rounded ${
                  isOverLimit
                    ? 'bg-red-100 text-red-700'
                    : selectedCount > 0
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-600'
                }`}>
                  {selectedCount}/{availableVacancies} selecionados
                </span>
              </div>

              {availableMembers.length === 0 ? (
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-yellow-700 text-sm">
                    Nenhum membro disponível para agendamento. Todos os membros já possuem agendamentos ativos ou atingiram o limite de uso.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-2 max-h-64 overflow-y-auto">
                  {availableMembers.map((member) => {
                    const isSelected = selectedMemberIds.includes(member.member_id);
                    return (
                      <button
                        key={member.member_id}
                        onClick={() => toggleMember(member.member_id)}
                        className={`p-3 rounded-xl border-2 text-left transition-all ${
                          isSelected
                            ? 'border-primary-500 bg-primary-50'
                            : 'border-gray-200 hover:border-gray-300 bg-white'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                            isSelected
                              ? 'bg-primary-500 text-white'
                              : 'bg-gray-100 text-gray-600'
                          }`}>
                            {isSelected ? (
                              <Check className="h-4 w-4" />
                            ) : (
                              member.social_name[0]
                            )}
                          </div>
                          <div className="min-w-0">
                            <div className="font-medium text-gray-900 text-sm truncate">
                              {member.social_name}
                            </div>
                            <div className="text-xs text-gray-500">
                              {member.has_booking ? 'Agendado' : 'Disponível'}
                            </div>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Warning if over limit */}
            {isOverLimit && (
              <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0" />
                <p className="text-red-700 text-sm">
                  Você selecionou mais membros do que vagas disponíveis. Reduza a seleção para {availableVacancies} ou menos.
                </p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3">
              <Button
                variant="outline"
                className="flex-1"
                onClick={handleClose}
              >
                Cancelar
              </Button>
              <Button
                variant="primary"
                className="flex-1"
                onClick={handleBookAll}
                disabled={selectedCount === 0 || isOverLimit || isBooking}
                isLoading={isBooking}
              >
                {isBooking ? 'Agendando...' : `Agendar ${selectedCount > 0 ? `(${selectedCount})` : ''}`}
              </Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
