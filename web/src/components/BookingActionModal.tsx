'use client';

import { useState } from 'react';
import { AlertTriangle, X, RefreshCw, Users, GraduationCap, Waves } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui';
import { useMembers, useSwapBooking, useCancelBooking } from '@/hooks';
import { formatDate } from '@/lib/utils';

interface Booking {
  voucher_code: string;
  member_name: string;
  member_id: number;
  date: string;
  interval: string;
  level?: string;
  wave_side?: string;
}

const SURF_BACKGROUNDS = [
  '/surf-backgrounds/surf-1.jpg',
  '/surf-backgrounds/surf-2.jpg',
  '/surf-backgrounds/surf-3.jpg',
  '/surf-backgrounds/surf-4.jpg',
  '/surf-backgrounds/surf-5.jpg',
  '/surf-backgrounds/surf-6.jpg',
  '/surf-backgrounds/surf-7.jpg',
  '/surf-backgrounds/surf-8.jpg',
  '/surf-backgrounds/surf-9.jpg',
  '/surf-backgrounds/surf-10.jpg',
];

const getBookingBackground = (voucherCode: string) => {
  let hash = 0;
  for (let i = 0; i < voucherCode.length; i++) {
    hash = ((hash << 5) - hash) + voucherCode.charCodeAt(i);
    hash = hash & hash;
  }
  return SURF_BACKGROUNDS[Math.abs(hash) % SURF_BACKGROUNDS.length];
};

const formatLevel = (level?: string) => {
  if (!level) return null;
  return level.replace('Iniciante', 'Iniciante ').replace('Intermediario', 'Intermediário ').replace('Avançado', 'Avançado ').replace('Avancado', 'Avançado ').trim();
};

const formatWaveSide = (waveSide?: string) => {
  if (!waveSide) return null;
  return waveSide.replace('Lado_', '').replace('esquerdo', 'Esquerda').replace('direito', 'Direita');
};

interface BookingActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  booking: Booking | null;
  onSuccess: () => void;
}

type Action = 'choose' | 'cancel' | 'swap';

export function BookingActionModal({
  isOpen,
  onClose,
  booking,
  onSuccess,
}: BookingActionModalProps) {
  const [action, setAction] = useState<Action>('choose');
  const [selectedMemberId, setSelectedMemberId] = useState<number | null>(null);
  const { data: membersData } = useMembers();
  const swapMutation = useSwapBooking();
  const cancelMutation = useCancelBooking();

  const handleClose = () => {
    setAction('choose');
    setSelectedMemberId(null);
    onClose();
  };

  const handleCancel = async () => {
    if (!booking) return;
    try {
      await cancelMutation.mutateAsync(booking.voucher_code);
      onSuccess();
      handleClose();
    } catch (error) {
      // Error handling is done by mutation
    }
  };

  const handleSwap = async () => {
    if (!booking || !selectedMemberId) return;
    try {
      await swapMutation.mutateAsync({
        voucherCode: booking.voucher_code,
        newMemberId: selectedMemberId,
      });
      onSuccess();
      handleClose();
    } catch (error) {
      // Error handling is done by mutation
    }
  };

  // Filter members that can receive a booking:
  // - Not the current booking member
  // - Don't have active bookings (has_booking = false)
  const availableMembers = membersData?.members.filter(
    (m) => !m.has_booking && m.member_id !== booking?.member_id
  ) ?? [];

  if (!booking) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={action === 'choose' ? 'Gerenciar Agendamento' : action === 'cancel' ? 'Cancelar Agendamento' : 'Trocar Membro'}
    >
      <div className="space-y-6">
        {/* Booking Card with Image */}
        <div className="relative h-28 rounded-xl overflow-hidden">
          {/* Background Image */}
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{ backgroundImage: `url(${getBookingBackground(booking.voucher_code)})` }}
          />
          {/* Gradient Overlay */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-black/20" />

          {/* Content */}
          <div className="relative h-full p-4 flex flex-col justify-end">
            <p className="text-white/80 text-sm">
              {formatDate(booking.date)} · {booking.interval}
            </p>
            <h4 className="text-white font-bold text-lg uppercase">
              {booking.member_name}
            </h4>
            <div className="flex gap-2 mt-1">
              {booking.level && (
                <span className="px-2 py-0.5 bg-white/20 backdrop-blur-sm rounded-full text-xs font-medium text-white flex items-center gap-1">
                  <GraduationCap className="h-3 w-3" />
                  {formatLevel(booking.level)}
                </span>
              )}
              {booking.wave_side && (
                <span className="px-2 py-0.5 bg-white/20 backdrop-blur-sm rounded-full text-xs font-medium text-white flex items-center gap-1">
                  <Waves className="h-3 w-3" />
                  {formatWaveSide(booking.wave_side)}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Choose Action */}
        {action === 'choose' && (
          <div className="space-y-3">
            <p className="text-gray-600 text-center mb-4">
              O que deseja fazer com este agendamento?
            </p>
            <Button
              variant="outline"
              className="w-full justify-start gap-3 py-4"
              onClick={() => setAction('swap')}
            >
              <RefreshCw className="h-5 w-5 text-primary-600" />
              <div className="text-left">
                <div className="font-medium">Trocar Membro</div>
                <div className="text-sm text-gray-500">
                  Transferir este agendamento para outro membro
                </div>
              </div>
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start gap-3 py-4 border-red-200 hover:bg-red-50"
              onClick={() => setAction('cancel')}
            >
              <X className="h-5 w-5 text-red-600" />
              <div className="text-left">
                <div className="font-medium text-red-600">Cancelar Agendamento</div>
                <div className="text-sm text-gray-500">
                  Liberar a vaga para outros usuarios
                </div>
              </div>
            </Button>
          </div>
        )}

        {/* Cancel Confirmation */}
        {action === 'cancel' && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-4 bg-red-50 rounded-lg">
              <AlertTriangle className="h-6 w-6 text-red-600 flex-shrink-0" />
              <p className="text-red-700">
                Tem certeza que deseja cancelar este agendamento? Esta acao nao pode ser desfeita.
              </p>
            </div>
            <div className="flex gap-3">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setAction('choose')}
              >
                Voltar
              </Button>
              <Button
                variant="danger"
                className="flex-1"
                onClick={handleCancel}
                isLoading={cancelMutation.isPending}
              >
                Confirmar Cancelamento
              </Button>
            </div>
          </div>
        )}

        {/* Swap Member Selection */}
        {action === 'swap' && (
          <div className="space-y-4">
            <p className="text-gray-600">
              Selecione o membro que recebera este agendamento:
            </p>

            {availableMembers.length === 0 ? (
              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-yellow-700 text-sm">
                  Nenhum membro disponivel para troca. Todos os membros ja possuem agendamentos ativos.
                </p>
              </div>
            ) : (
              <div className="max-h-60 overflow-y-auto space-y-2">
                {availableMembers.map((member) => (
                  <button
                    key={member.member_id}
                    onClick={() => setSelectedMemberId(member.member_id)}
                    className={`w-full p-3 rounded-lg border-2 text-left transition-colors ${
                      selectedMemberId === member.member_id
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                        <Users className="h-5 w-5 text-primary-600" />
                      </div>
                      <div>
                        <div className="font-medium text-gray-900">
                          {member.social_name}
                        </div>
                        <div className="text-sm text-gray-500">
                          {member.has_booking ? 'Agendado' : 'Disponível'}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}

            <div className="flex gap-3">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => {
                  setAction('choose');
                  setSelectedMemberId(null);
                }}
              >
                Voltar
              </Button>
              <Button
                variant="primary"
                className="flex-1"
                onClick={handleSwap}
                disabled={!selectedMemberId}
                isLoading={swapMutation.isPending}
              >
                Confirmar Troca
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
