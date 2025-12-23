'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Search, User, Settings, CheckCircle, XCircle } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, Input, Badge, Button } from '@/components/ui';
import { useMembers } from '@/hooks';

export default function MembersPage() {
  const { data, isLoading, error } = useMembers();
  const [search, setSearch] = useState('');

  const filteredMembers = data?.members.filter(
    (m) =>
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.social_name.toLowerCase().includes(search.toLowerCase())
  ) ?? [];

  return (
    <MainLayout title="Membros">
      {/* Search */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <Input
            placeholder="Buscar membros..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="animate-pulse h-32 bg-gray-100 rounded-xl" />
          ))}
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-500">Total</p>
              <p className="text-2xl font-bold">{data?.total ?? 0}</p>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-500">Com Preferencias</p>
              <p className="text-2xl font-bold text-green-600">
                {data?.members.filter(m => m.has_preferences).length ?? 0}
              </p>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-500">Agendados</p>
              <p className="text-2xl font-bold text-blue-600">
                {data?.members.filter(m => m.has_booking).length ?? 0}
              </p>
            </div>
          </div>

          {/* Members Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredMembers.map((member) => (
              <Card key={member.member_id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center">
                        <User className="h-6 w-6 text-primary-600" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">
                          {member.social_name}
                        </h3>
                        <p className="text-sm text-gray-500">{member.name}</p>
                        <p className="text-xs text-gray-400">
                          ID: {member.member_id}
                        </p>
                      </div>
                    </div>
                    <Link href={`/members/${member.member_id}`}>
                      <Button variant="ghost" size="sm">
                        <Settings className="h-4 w-4" />
                      </Button>
                    </Link>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    {member.is_titular && (
                      <Badge variant="info">Titular</Badge>
                    )}
                    {member.has_preferences ? (
                      <Badge variant="success">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Preferencias
                      </Badge>
                    ) : (
                      <Badge variant="warning">
                        <XCircle className="h-3 w-3 mr-1" />
                        Sem prefs
                      </Badge>
                    )}
                    {member.has_booking ? (
                      <Badge variant="success">Agendado</Badge>
                    ) : (
                      <Badge variant="default">Disponivel</Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {filteredMembers.length === 0 && (
            <div className="text-center py-12">
              <User className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Nenhum membro encontrado</p>
            </div>
          )}
        </>
      )}
    </MainLayout>
  );
}
