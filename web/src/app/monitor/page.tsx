'use client';

import { useState, useEffect } from 'react';
import { Radio, Play, Square, CheckCircle, XCircle, Clock, Users, Search } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from '@/components/ui';
import { useMembers, useStartMonitor, useMonitorWebSocket } from '@/hooks';
import { SessionSearchForm } from '@/components/SessionSearchForm';
import type { Member } from '@/types';

type TabType = 'preferences' | 'specific';

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
  const startMutation = useStartMonitor();

  const [selectedMembers, setSelectedMembers] = useState<number[]>([]);
  const [duration, setDuration] = useState(120);
  const [monitorId, setMonitorId] = useState<string | null>(null);

  const { messages, isConnected, status, connect, disconnect, sendStop } =
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
  );
}
