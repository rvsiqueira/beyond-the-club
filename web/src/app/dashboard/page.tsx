'use client';

import Link from 'next/link';
import { Users, Calendar, Ticket, Radio, ArrowRight, RefreshCw } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from '@/components/ui';
import { useMembers, useBookings, useAvailability, useScanAvailability } from '@/hooks';
import { formatDate } from '@/lib/utils';

export default function DashboardPage() {
  const { data: membersData, isLoading: membersLoading } = useMembers();
  const { data: bookingsData, isLoading: bookingsLoading } = useBookings();
  const { data: availabilityData, isLoading: availabilityLoading } = useAvailability();
  const scanMutation = useScanAvailability();

  const stats = [
    {
      name: 'Membros',
      value: membersData?.total ?? '-',
      icon: Users,
      href: '/members',
      color: 'bg-blue-500',
    },
    {
      name: 'Agendamentos',
      value: bookingsData?.total ?? '-',
      icon: Ticket,
      href: '/bookings',
      color: 'bg-green-500',
    },
    {
      name: 'Slots Disponiveis',
      value: availabilityData?.total ?? '-',
      icon: Calendar,
      href: '/availability',
      color: 'bg-purple-500',
    },
  ];

  const membersWithoutBooking = membersData?.members.filter(m => !m.has_booking) ?? [];
  const membersWithPrefs = membersData?.members.filter(m => m.has_preferences) ?? [];

  return (
    <MainLayout title="Dashboard">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {stats.map((stat) => (
          <Link key={stat.name} href={stat.href}>
            <Card className="hover:shadow-md transition-shadow cursor-pointer">
              <CardContent className="flex items-center gap-4 py-6">
                <div className={`w-12 h-12 ${stat.color} rounded-lg flex items-center justify-center`}>
                  <stat.icon className="h-6 w-6 text-white" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">{stat.name}</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {stat.value}
                  </p>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Bookings */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Agendamentos Ativos</CardTitle>
            <Link href="/bookings">
              <Button variant="ghost" size="sm">
                Ver todos <ArrowRight className="ml-1 h-4 w-4" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {bookingsLoading ? (
              <div className="animate-pulse space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-gray-100 rounded-lg" />
                ))}
              </div>
            ) : bookingsData?.bookings.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                Nenhum agendamento ativo
              </p>
            ) : (
              <div className="space-y-4">
                {bookingsData?.bookings.slice(0, 5).map((booking) => (
                  <div
                    key={booking.voucher_code}
                    className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                  >
                    <div>
                      <p className="font-medium text-gray-900">
                        {booking.member_name}
                      </p>
                      <p className="text-sm text-gray-500">
                        {formatDate(booking.date)} - {booking.interval}
                      </p>
                    </div>
                    <div className="text-right">
                      <Badge variant="success">{booking.status}</Badge>
                      <p className="text-xs text-gray-400 mt-1">
                        {booking.voucher_code}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Members Ready to Book */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Membros sem Agendamento</CardTitle>
            <Link href="/monitor">
              <Button variant="primary" size="sm">
                <Radio className="mr-1 h-4 w-4" /> Auto Monitor
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {membersLoading ? (
              <div className="animate-pulse space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 bg-gray-100 rounded-lg" />
                ))}
              </div>
            ) : membersWithoutBooking.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                Todos os membros estao agendados!
              </p>
            ) : (
              <div className="space-y-3">
                {membersWithoutBooking.slice(0, 5).map((member) => (
                  <div
                    key={member.member_id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                        <span className="text-primary-600 font-medium text-sm">
                          {member.social_name[0]}
                        </span>
                      </div>
                      <span className="font-medium text-gray-900">
                        {member.social_name}
                      </span>
                    </div>
                    {member.has_preferences ? (
                      <Badge variant="success">Preferencias</Badge>
                    ) : (
                      <Badge variant="warning">Sem prefs</Badge>
                    )}
                  </div>
                ))}
                {membersWithoutBooking.length > 5 && (
                  <p className="text-sm text-gray-500 text-center pt-2">
                    +{membersWithoutBooking.length - 5} membros
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Availability Status */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Status da Disponibilidade</CardTitle>
              {availabilityData?.cache_updated_at && (
                <p className="text-sm text-gray-500 mt-1">
                  Atualizado: {new Date(availabilityData.cache_updated_at).toLocaleString('pt-BR')}
                </p>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => scanMutation.mutate()}
              isLoading={scanMutation.isPending}
            >
              <RefreshCw className="mr-1 h-4 w-4" /> Atualizar
            </Button>
          </CardHeader>
          <CardContent>
            {availabilityLoading ? (
              <div className="animate-pulse h-32 bg-gray-100 rounded-lg" />
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-3xl font-bold text-primary-600">
                    {availabilityData?.total ?? 0}
                  </p>
                  <p className="text-sm text-gray-500">Total de Slots</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-3xl font-bold text-green-600">
                    {availabilityData?.slots.filter(s => s.available > 0).length ?? 0}
                  </p>
                  <p className="text-sm text-gray-500">Disponiveis</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-3xl font-bold text-blue-600">
                    {membersWithPrefs.length}
                  </p>
                  <p className="text-sm text-gray-500">Com Preferencias</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-3xl font-bold text-purple-600">
                    {availabilityData?.cache_valid ? 'Sim' : 'Nao'}
                  </p>
                  <p className="text-sm text-gray-500">Cache Valido</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}
