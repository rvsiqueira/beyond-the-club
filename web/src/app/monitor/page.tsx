'use client';

import { useState, useEffect, useCallback } from 'react';
import { Radio, Play, Square, CheckCircle, XCircle, Clock, Users, Search, Calendar, X, PartyPopper } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from '@/components/ui';
import { useMembers, useRefreshMembers, useStartMonitor, useMonitorWebSocket } from '@/hooks';
import { SessionSearchForm } from '@/components/SessionSearchForm';
import type { Member } from '@/types';

type TabType = 'preferences' | 'specific';

interface BookingResult {
  memberId: number;
  memberName: string;
  date: string;
  time: string;
  level: string;
  waveSide: string;
  accessCode: string;
}

export default function MonitorPage() {
  const [activeTab, setActiveTab] = useState<TabType>('preferences');

  return (
    <MainLayout title="Monitor">
      {/* Tab Navigation */}
      <div className="mb-6">
        <div className="flex gap-2 p-1 bg-gray-100 rounded-lg w-fit">
          <button
            onClick={() => setActiveTab('preferences')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'preferences'
                ? 'bg-white text-primary-700 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Users className="h-4 w-4" />
            Auto Monitor
          </button>
          <button
            onClick={() => setActiveTab('specific')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'specific'
                ? 'bg-white text-primary-700 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Search className="h-4 w-4" />
            Busca Especifica
          </button>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'preferences' ? (
        <PreferencesMonitor />
      ) : (
        <SessionSearchForm />
      )}
    </MainLayout>
  );
}

function PreferencesMonitor() {
  const { data: membersData, isLoading: membersLoading } = useMembers();
  const refreshMembersMutation = useRefreshMembers();
  const startMutation = useStartMonitor();

  const [selectedMembers, setSelectedMembers] = useState<number[]>([]);
  const [duration, setDuration] = useState(120);
  const [monitorId, setMonitorId] = useState<string | null>(null);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [bookingResults, setBookingResults] = useState<BookingResult[]>([]);

  const { messages, isConnected, status, connect, disconnect, sendStop, clearMessages } =
    useMonitorWebSocket(monitorId);

  // Available members (without booking, with preferences)
  const availableMembers =
    membersData?.members.filter((m) => !m.has_booking && m.has_preferences) ?? [];

  const toggleMember = (id: number) => {
    if (selectedMembers.includes(id)) {
      setSelectedMembers(selectedMembers.filter((m) => m !== id));
    } else {
      setSelectedMembers([...selectedMembers, id]);
    }
  };

  const selectAll = () => {
    setSelectedMembers(availableMembers.map((m) => m.member_id));
  };

  const handleStart = async () => {
    if (selectedMembers.length === 0) return;

    const result = await startMutation.mutateAsync({
      member_ids: selectedMembers,
      duration_minutes: duration,
    });

    setMonitorId(result.monitor_id);
  };

  // Connect WebSocket when monitorId is set
  useEffect(() => {
    if (monitorId) {
      connect();
    }
    return () => disconnect();
  }, [monitorId, connect, disconnect]);

  // Detect completed bookings and show success modal
  useEffect(() => {
    const completedMsg = messages.find(
      (msg) => msg.type === 'completed' && msg.results
    );

    if (completedMsg && completedMsg.results) {
      const results: BookingResult[] = [];

      // Parse results from the completed message
      Object.entries(completedMsg.results).forEach(([memberId, result]: [string, any]) => {
        if (result.success && result.slot) {
          const member = membersData?.members.find(
            (m) => m.member_id === parseInt(memberId)
          );
          results.push({
            memberId: parseInt(memberId),
            memberName: member?.social_name || `Membro ${memberId}`,
            date: result.slot.date || '',
            time: result.slot.interval || '',
            level: result.slot.level || '',
            waveSide: result.slot.wave_side || '',
            accessCode: result.access_code || '',
          });
        }
      });

      if (results.length > 0) {
        setBookingResults(results);
        setShowSuccessModal(true);
      }
    }
  }, [messages, membersData]);

  // Reset and close modal
  const handleCloseSuccessModal = useCallback(() => {
    setShowSuccessModal(false);
    setBookingResults([]);
    setMonitorId(null);
    setSelectedMembers([]);
    clearMessages();
    // Refresh members list from API to update booking status
    refreshMembersMutation.mutate();
  }, [clearMessages, refreshMembersMutation]);

  const handleStop = () => {
    sendStop();
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

  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Configuracao
            </CardTitle>
          </CardHeader>
          <CardContent>
            {/* Duration */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Duracao (minutos)
              </label>
              <div className="flex gap-2">
                {[30, 60, 120, 180].map((d) => (
                  <button
                    key={d}
                    onClick={() => setDuration(d)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      duration === d
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {d}min
                  </button>
                ))}
              </div>
            </div>

            {/* Member Selection */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <label className="block text-sm font-medium text-gray-700">
                  Membros ({selectedMembers.length} selecionados)
                </label>
                <Button variant="ghost" size="sm" onClick={selectAll}>
                  Selecionar todos
                </Button>
              </div>

              {membersLoading ? (
                <div className="animate-pulse space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-12 bg-gray-100 rounded-lg" />
                  ))}
                </div>
              ) : availableMembers.length === 0 ? (
                <p className="text-gray-500 text-center py-4">
                  Nenhum membro disponivel (sem agendamento e com preferencias)
                </p>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {availableMembers.map((member) => (
                    <button
                      key={member.member_id}
                      onClick={() => toggleMember(member.member_id)}
                      className={`w-full flex items-center justify-between p-3 rounded-lg border transition-colors ${
                        selectedMembers.includes(member.member_id)
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                            selectedMembers.includes(member.member_id)
                              ? 'border-primary-500 bg-primary-500'
                              : 'border-gray-300'
                          }`}
                        >
                          {selectedMembers.includes(member.member_id) && (
                            <CheckCircle className="h-4 w-4 text-white" />
                          )}
                        </div>
                        <span className="font-medium">{member.social_name}</span>
                      </div>
                      <Badge variant="success">Prefs</Badge>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="mt-6 flex gap-3">
              {status === 'running' ? (
                <Button
                  variant="danger"
                  className="flex-1"
                  onClick={handleStop}
                >
                  <Square className="h-4 w-4 mr-2" /> Parar
                </Button>
              ) : (
                <Button
                  variant="primary"
                  className="flex-1"
                  onClick={handleStart}
                  disabled={selectedMembers.length === 0}
                  isLoading={startMutation.isPending}
                >
                  <Play className="h-4 w-4 mr-2" /> Iniciar Monitor
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
              Status do Monitor
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
                  Configure e inicie o monitor para ver os logs
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

      {/* Success Modal */}
      {showSuccessModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-green-500 to-emerald-600 p-6 text-white text-center">
              <PartyPopper className="h-16 w-16 mx-auto mb-4" />
              <h2 className="text-2xl font-bold">Reserva Confirmada!</h2>
              <p className="text-green-100 mt-1">
                {bookingResults.length === 1
                  ? 'Sua sessao foi agendada com sucesso'
                  : `${bookingResults.length} sessoes foram agendadas com sucesso`}
              </p>
            </div>

            {/* Content */}
            <div className="p-6 max-h-80 overflow-y-auto">
              {bookingResults.map((result, idx) => (
                <div
                  key={idx}
                  className={`${idx > 0 ? 'mt-4 pt-4 border-t border-gray-100' : ''}`}
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">{result.memberName}</p>
                      <p className="text-sm text-gray-500">
                        {result.level} - {result.waveSide}
                      </p>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                    <div className="flex items-center gap-2 text-gray-700">
                      <Calendar className="h-4 w-4 text-gray-400" />
                      <span>{result.date} as {result.time}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-500">Codigo de Acesso:</span>
                      <code className="bg-green-100 text-green-800 px-3 py-1 rounded-lg font-mono font-bold">
                        {result.accessCode}
                      </code>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="p-4 bg-gray-50 border-t border-gray-100">
              <Button
                variant="primary"
                className="w-full"
                onClick={handleCloseSuccessModal}
              >
                Fechar
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
