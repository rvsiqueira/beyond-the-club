'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { Users, Calendar, Ticket, Radio, ArrowRight, RefreshCw, Clock, Waves } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from '@/components/ui';
import { useMembers, useBookings, useAvailability, useScanAvailability, useBeyondTokenStatus, useAuth } from '@/hooks';
import { isBeyondAuthError } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { SMSVerificationModal } from '@/components/SMSVerificationModal';
import { useQueryClient } from '@tanstack/react-query';

const REFRESH_COOLDOWN_SECONDS = 60;

export default function DashboardPage() {
  const { user } = useAuth();
  const { data: membersData, isLoading: membersLoading, error: membersError } = useMembers();
  const { data: bookingsData, isLoading: bookingsLoading, error: bookingsError } = useBookings();
  const { data: availabilityData, isLoading: availabilityLoading, error: availabilityError } = useAvailability();
  const { data: beyondStatus, isLoading: beyondStatusLoading } = useBeyondTokenStatus();
  const scanMutation = useScanAvailability();
  const queryClient = useQueryClient();

  const [showSMSModal, setShowSMSModal] = useState(false);
  const [refreshCooldown, setRefreshCooldown] = useState(0);
  const [lastRefreshTime, setLastRefreshTime] = useState<number | null>(null);

  // Cooldown timer for refresh button
  useEffect(() => {
    if (refreshCooldown > 0) {
      const timer = setTimeout(() => {
        setRefreshCooldown(refreshCooldown - 1);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [refreshCooldown]);

  // Calculate initial cooldown based on cache_updated_at
  useEffect(() => {
    if (availabilityData?.cache_updated_at && !lastRefreshTime) {
      const cacheTime = new Date(availabilityData.cache_updated_at).getTime();
      const now = Date.now();
      const secondsSinceUpdate = Math.floor((now - cacheTime) / 1000);

      // Only set cooldown if update was recent (within cooldown period)
      // and the calculated time is reasonable (not negative or too large)
      if (secondsSinceUpdate >= 0 && secondsSinceUpdate < REFRESH_COOLDOWN_SECONDS) {
        setRefreshCooldown(REFRESH_COOLDOWN_SECONDS - secondsSinceUpdate);
      }
      // If secondsSinceUpdate is negative or too large, don't set cooldown (allow refresh)
    }
  }, [availabilityData?.cache_updated_at, lastRefreshTime]);

  const handleRefresh = useCallback(() => {
    if (refreshCooldown > 0 || scanMutation.isPending) return;

    scanMutation.mutate(undefined, {
      onSuccess: () => {
        setLastRefreshTime(Date.now());
        setRefreshCooldown(REFRESH_COOLDOWN_SECONDS);
      }
    });
  }, [refreshCooldown, scanMutation]);

  const isRefreshDisabled = refreshCooldown > 0 || scanMutation.isPending;

  // Auto-show SMS modal if Beyond token is invalid OR any query returns Beyond auth error
  useEffect(() => {
    const hasBeyondError =
      isBeyondAuthError(membersError) ||
      isBeyondAuthError(bookingsError) ||
      isBeyondAuthError(availabilityError);

    if (hasBeyondError || (!beyondStatusLoading && beyondStatus && !beyondStatus.valid)) {
      setShowSMSModal(true);
    }
  }, [beyondStatus, beyondStatusLoading, membersError, bookingsError, availabilityError]);

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

  // Format level for display (full name)
  const formatLevel = (level?: string) => {
    if (!level) return null;
    return level.replace('Iniciante', 'Iniciante ').replace('Intermediario', 'Intermediário ').replace('Avançado', 'Avançado ').replace('Avancado', 'Avançado ').trim();
  };

  // Format wave side for display (full name)
  const formatWaveSide = (waveSide?: string) => {
    if (!waveSide) return null;
    return waveSide.replace('Lado_', '').replace('esquerdo', 'Esquerdo').replace('direito', 'Direito');
  };

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
                      <p className="text-sm text-gray-500 flex items-center gap-1">
                        {formatDate(booking.date)} - <Clock className="h-3.5 w-3.5" /> {booking.interval}
                      </p>
                      <div className="flex gap-2 mt-1">
                        {booking.level && (
                          <Badge variant="info" className="text-xs">
                            {formatLevel(booking.level)}
                          </Badge>
                        )}
                        {booking.wave_side && (
                          <Badge variant="default" className="text-xs flex items-center gap-1">
                            <Waves className="h-3 w-3" />
                            {formatWaveSide(booking.wave_side)}
                          </Badge>
                        )}
                      </div>
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
              onClick={handleRefresh}
              isLoading={scanMutation.isPending}
              disabled={isRefreshDisabled}
            >
              <RefreshCw className={`mr-1 h-4 w-4 ${scanMutation.isPending ? 'animate-spin' : ''}`} />
              {refreshCooldown > 0 ? `Aguarde ${refreshCooldown}s` : 'Atualizar'}
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

      {/* SMS Verification Modal */}
      {user && (
        <SMSVerificationModal
          isOpen={showSMSModal}
          onClose={() => setShowSMSModal(false)}
          onSuccess={() => {
            // Refresh all queries that depend on Beyond API
            queryClient.invalidateQueries({ queryKey: ['beyond-token-status'] });
            queryClient.invalidateQueries({ queryKey: ['members'] });
            queryClient.invalidateQueries({ queryKey: ['bookings'] });
            queryClient.invalidateQueries({ queryKey: ['availability'] });
          }}
          phone={user.phone}
        />
      )}
    </MainLayout>
  );
}
