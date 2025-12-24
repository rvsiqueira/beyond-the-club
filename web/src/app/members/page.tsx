'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, User, CheckCircle, XCircle, Ticket } from 'lucide-react';
import { MainLayout } from '@/components/layout';
import { Input } from '@/components/ui';
import { useMembers } from '@/hooks';

// Random backgrounds for members - using surf backgrounds with different approach
const MEMBER_BACKGROUNDS = [
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

// Get a consistent background for a member based on member_id
const getMemberBackground = (memberId: number) => {
  return MEMBER_BACKGROUNDS[memberId % MEMBER_BACKGROUNDS.length];
};

export default function MembersPage() {
  const router = useRouter();
  const { data, isLoading, error } = useMembers();
  const [search, setSearch] = useState('');

  const filteredMembers = data?.members.filter(
    (m) =>
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.social_name.toLowerCase().includes(search.toLowerCase())
  ) ?? [];

  const handleMemberClick = (memberId: number) => {
    router.push(`/members/${memberId}`);
  };

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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="animate-pulse h-[180px] bg-gray-200 rounded-2xl" />
          ))}
        </div>
      ) : (
        <>
          {/* Members Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredMembers.map((member) => (
              <div
                key={member.member_id}
                onClick={() => handleMemberClick(member.member_id)}
                className="relative rounded-2xl overflow-hidden shadow-lg group transition-all duration-300 cursor-pointer hover:shadow-xl hover:-translate-y-1"
              >
                {/* Background Image */}
                <div
                  className="absolute inset-0 bg-cover bg-center transition-transform duration-500 group-hover:scale-110"
                  style={{ backgroundImage: `url(${getMemberBackground(member.member_id)})` }}
                />
                {/* Gradient Overlay - darker at bottom for text readability */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-black/30" />

                {/* Content */}
                <div className="relative p-4 min-h-[180px] flex flex-col justify-between">
                  {/* Top Row - Avatar and Usage */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center">
                        <span className="text-white font-bold text-lg">
                          {member.social_name[0]}
                        </span>
                      </div>
                      <div>
                        <h3 className="font-bold text-white text-lg drop-shadow-lg">
                          {member.social_name}
                        </h3>
                        <p className="text-white/70 text-xs">
                          ID: {member.member_id}
                        </p>
                      </div>
                    </div>

                    {/* Usage Badge */}
                    <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-white/95 text-gray-800 flex items-center gap-1">
                      <Ticket className="h-3 w-3" />
                      {member.usage}/{member.limit}
                    </span>
                  </div>

                  {/* Bottom Content */}
                  <div>
                    {/* Full Name */}
                    <p className="text-white/60 text-xs mb-2 truncate">
                      {member.name}
                    </p>

                    {/* Tags */}
                    <div className="flex flex-wrap gap-2">
                      {member.is_titular && (
                        <span className="px-2.5 py-1 bg-blue-500/40 backdrop-blur-sm rounded-full text-xs font-semibold text-white">
                          Titular
                        </span>
                      )}
                      {member.has_preferences ? (
                        <span className="px-2.5 py-1 bg-green-500/40 backdrop-blur-sm rounded-full text-xs font-semibold text-white flex items-center gap-1">
                          <CheckCircle className="h-3 w-3" />
                          Preferências
                        </span>
                      ) : (
                        <span className="px-2.5 py-1 bg-yellow-500/40 backdrop-blur-sm rounded-full text-xs font-semibold text-white flex items-center gap-1">
                          <XCircle className="h-3 w-3" />
                          Sem prefs
                        </span>
                      )}
                      {member.has_booking ? (
                        <span className="px-2.5 py-1 bg-green-500/40 backdrop-blur-sm rounded-full text-xs font-semibold text-white">
                          Agendado
                        </span>
                      ) : (
                        <span className="px-2.5 py-1 bg-white/20 backdrop-blur-sm rounded-full text-xs font-semibold text-white">
                          Disponível
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Status indicator for booked members */}
                {member.has_booking && (
                  <div className="absolute top-3 right-3 w-2.5 h-2.5 rounded-full bg-green-400 animate-pulse shadow-lg shadow-green-400/50" />
                )}
              </div>
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
