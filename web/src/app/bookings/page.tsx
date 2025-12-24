'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Ticket, Plus, X, RefreshCw, Copy, Check, Clock, Waves, GraduationCap, MoreVertical } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Button, Badge } from '@/components/ui';
import { useBookings } from '@/hooks';
import { formatDate } from '@/lib/utils';
import { BookingActionModal } from '@/components/BookingActionModal';
import { useQueryClient } from '@tanstack/react-query';

interface Booking {
  voucher_code: string;
  access_code: string;
  member_name: string;
  member_id: number;
  date: string;
  interval: string;
  level?: string;
  wave_side?: string;
  status: string;
}

// Wave images by level - fixed per level for quick visual identification
// Beginner: sunrise/sunset calm waves
// Intermediate: turquoise/green water
// Advanced: strong blue ocean waves
const getWaveBackground = (level?: string) => {
  if (!level) return '/wave-levels/advanced-1.jpg';
  if (level.startsWith('Iniciante')) {
    return '/wave-levels/beginner-1.jpg';
  } else if (level.startsWith('Intermediario')) {
    return '/wave-levels/intermediate-1.jpg';
  } else {
    return '/wave-levels/advanced-1.jpg';
  }
};

export default function BookingsPage() {
  const { data, isLoading, error, refetch } = useBookings();
  const queryClient = useQueryClient();
  const [copiedVoucher, setCopiedVoucher] = useState<string | null>(null);
  const [selectedBooking, setSelectedBooking] = useState<Booking | null>(null);
  const [showActionModal, setShowActionModal] = useState(false);

  const handleOpenActionModal = (booking: Booking) => {
    setSelectedBooking(booking);
    setShowActionModal(true);
  };

  const handleActionSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['bookings'] });
    queryClient.invalidateQueries({ queryKey: ['members'] });
  };

  const copyToClipboard = (text: string, voucher: string) => {
    navigator.clipboard.writeText(text);
    setCopiedVoucher(voucher);
    setTimeout(() => setCopiedVoucher(null), 2000);
  };

  // Format level for display (full name)
  const formatLevel = (level?: string) => {
    if (!level) return null;
    // Keep full name, just clean up formatting
    return level.replace('Iniciante', 'Iniciante ').replace('Intermediario', 'Intermediário ').replace('Avançado', 'Avançado ').replace('Avancado', 'Avançado ').trim();
  };

  // Format wave side for display (full name)
  const formatWaveSide = (waveSide?: string) => {
    if (!waveSide) return null;
    return waveSide.replace('Lado_', '').replace('esquerdo', 'Esquerdo').replace('direito', 'Direito');
  };

  return (
    <MainLayout title="Agendamentos">
      {/* Header Actions */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Badge variant="default">{data?.total ?? 0} agendamentos</Badge>
          <Badge variant="info">{data?.sport}</Badge>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" /> Atualizar
          </Button>
          <Link href="/bookings/new">
            <Button variant="primary">
              <Plus className="h-4 w-4 mr-2" /> Novo Agendamento
            </Button>
          </Link>
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
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse h-32 bg-gray-100 rounded-xl" />
          ))}
        </div>
      ) : data?.bookings.length === 0 ? (
        <div className="text-center py-12">
          <Ticket className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 mb-4">Nenhum agendamento ativo</p>
          <Link href="/bookings/new">
            <Button variant="primary">
              <Plus className="h-4 w-4 mr-2" /> Criar Agendamento
            </Button>
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {data?.bookings.map((booking) => {
            const daysUntil = Math.ceil((new Date(booking.date).getTime() - new Date().setHours(0,0,0,0)) / (1000 * 60 * 60 * 24));
            const daysLabel = daysUntil === 0 ? 'Hoje' : daysUntil === 1 ? 'Amanhã' : `Em ${daysUntil} dias`;

            return (
              <div
                key={booking.voucher_code}
                onClick={() => handleOpenActionModal(booking)}
                className="relative rounded-2xl overflow-hidden shadow-lg group cursor-pointer transition-all duration-300 hover:shadow-xl hover:-translate-y-1"
              >
                {/* Background Image */}
                <div
                  className="absolute inset-0 bg-cover bg-center transition-transform duration-500 group-hover:scale-110"
                  style={{ backgroundImage: `url(${getWaveBackground(booking.level)})` }}
                />
                {/* Gradient Overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-black/30" />

                {/* Content */}
                <div className="relative p-5 min-h-[220px] flex flex-col justify-between">
                  {/* Top Row */}
                  <div className="flex items-start justify-between">
                    {/* Days Badge */}
                    <span className="px-3 py-1.5 bg-white/95 backdrop-blur-sm rounded-full text-xs font-bold text-gray-800 shadow-sm">
                      {daysLabel}
                    </span>

                    {/* Cancel indicator */}
                    <div className="p-2 bg-white/20 backdrop-blur-sm rounded-full">
                      <X className="h-4 w-4 text-white" />
                    </div>
                  </div>

                  {/* Bottom Content */}
                  <div>
                    {/* Date & Time */}
                    <p className="text-white/80 text-sm mb-1">
                      {formatDate(booking.date)} · {booking.interval}
                    </p>

                    {/* Member Name */}
                    <h3 className="text-white font-bold text-xl mb-3 uppercase tracking-wide">
                      {booking.member_name}
                    </h3>

                    {/* Tags */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      {booking.level && (
                        <span className="px-2.5 py-1 bg-white/20 backdrop-blur-sm rounded-full text-xs font-medium text-white flex items-center gap-1">
                          <GraduationCap className="h-3 w-3" />
                          {formatLevel(booking.level)}
                        </span>
                      )}
                      {booking.wave_side && (
                        <span className="px-2.5 py-1 bg-white/20 backdrop-blur-sm rounded-full text-xs font-medium text-white flex items-center gap-1">
                          <Waves className="h-3 w-3" />
                          {formatWaveSide(booking.wave_side)}
                        </span>
                      )}
                    </div>

                    {/* Codes */}
                    <div className="flex items-center gap-3 pt-3 border-t border-white/20">
                      <div className="flex-1">
                        <p className="text-white/60 text-[10px] uppercase tracking-wider mb-0.5">Voucher</p>
                        <div className="flex items-center gap-1">
                          <code className="text-white text-xs font-mono font-medium">{booking.voucher_code}</code>
                          <button
                            onClick={(e) => { e.stopPropagation(); copyToClipboard(booking.voucher_code, booking.voucher_code); }}
                            className="p-1 hover:bg-white/20 rounded transition-colors"
                          >
                            {copiedVoucher === booking.voucher_code ? (
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
                          <code className="text-white text-xs font-mono font-medium">{booking.access_code}</code>
                          <button
                            onClick={(e) => { e.stopPropagation(); copyToClipboard(booking.access_code, booking.voucher_code + '-access'); }}
                            className="p-1 hover:bg-white/20 rounded transition-colors"
                          >
                            {copiedVoucher === booking.voucher_code + '-access' ? (
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
            );
          })}
        </div>
      )}

      {/* Action Modal */}
      <BookingActionModal
        isOpen={showActionModal}
        onClose={() => setShowActionModal(false)}
        booking={selectedBooking}
        onSuccess={handleActionSuccess}
      />
    </MainLayout>
  );
}
