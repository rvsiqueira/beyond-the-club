'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Ticket, Plus, X, RefreshCw, Copy, Check } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from '@/components/ui';
import { useBookings, useCancelBooking } from '@/hooks';
import { formatDate } from '@/lib/utils';

export default function BookingsPage() {
  const { data, isLoading, error, refetch } = useBookings();
  const cancelMutation = useCancelBooking();
  const [copiedVoucher, setCopiedVoucher] = useState<string | null>(null);

  const handleCancel = async (voucherCode: string) => {
    if (confirm('Tem certeza que deseja cancelar este agendamento?')) {
      await cancelMutation.mutateAsync(voucherCode);
    }
  };

  const copyToClipboard = (text: string, voucher: string) => {
    navigator.clipboard.writeText(text);
    setCopiedVoucher(voucher);
    setTimeout(() => setCopiedVoucher(null), 2000);
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
        <div className="space-y-4">
          {data?.bookings.map((booking) => (
            <Card key={booking.voucher_code}>
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center">
                      <Ticket className="h-6 w-6 text-primary-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        {booking.member_name}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {formatDate(booking.date)} - {booking.interval}
                      </p>
                      <div className="flex gap-2 mt-1">
                        {booking.level && (
                          <Badge variant="info">{booking.level}</Badge>
                        )}
                        {booking.wave_side && (
                          <Badge variant="default">
                            {booking.wave_side.replace('Lado_', '')}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    {/* Voucher & Access Code */}
                    <div className="text-right">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-500">Voucher:</span>
                        <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono">
                          {booking.voucher_code}
                        </code>
                        <button
                          onClick={() =>
                            copyToClipboard(booking.voucher_code, booking.voucher_code)
                          }
                          className="p-1 hover:bg-gray-100 rounded"
                        >
                          {copiedVoucher === booking.voucher_code ? (
                            <Check className="h-4 w-4 text-green-500" />
                          ) : (
                            <Copy className="h-4 w-4 text-gray-400" />
                          )}
                        </button>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-sm text-gray-500">Acesso:</span>
                        <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono">
                          {booking.access_code}
                        </code>
                        <button
                          onClick={() =>
                            copyToClipboard(
                              booking.access_code,
                              booking.voucher_code + '-access'
                            )
                          }
                          className="p-1 hover:bg-gray-100 rounded"
                        >
                          {copiedVoucher === booking.voucher_code + '-access' ? (
                            <Check className="h-4 w-4 text-green-500" />
                          ) : (
                            <Copy className="h-4 w-4 text-gray-400" />
                          )}
                        </button>
                      </div>
                    </div>

                    {/* Status & Actions */}
                    <div className="flex items-center gap-3">
                      <Badge variant="success">{booking.status}</Badge>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleCancel(booking.voucher_code)}
                        isLoading={cancelMutation.isPending}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </MainLayout>
  );
}
